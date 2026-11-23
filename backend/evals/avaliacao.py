"""Avaliações reprodutíveis do Ergo Assist.

1. busca: acerto@1, acerto@3 e MRR por modo (texto, vetor, híbrido), em dois
   conjuntos — `dev` (escrito por quem fez o sistema, usado para ajustar) e
   `cegas` (escrito por um agente que só viu os títulos; nunca usado para
   ajustar = estimativa honesta). Mede também quantas perguntas fora do escopo
   o corte por distância recusaria.
2. recomendação: invariantes em perfis variados (toda cadeira indicada alcança
   a altura, aguenta o peso, cabe no orçamento) e cobertura do catálogo por
   estatura.
3. agente (precisa de OPENROUTER_APIKEY): escolha de ferramenta, números sem
   lastro, latência, tokens e, com --juiz, nota de fundamentação dada por LLM.
"""

import json
import statistics
import time
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from catalogo.models import Cadeira
from conhecimento.busca import buscar
from medidas.calculo import calcular
from medidas.recomendacao import Necessidades, avaliar, recomendar

PASTA = Path(__file__).parent
MODOS = ["texto", "vetor", "hibrido"]
CORTES = [0.45, 0.5, 0.55, 0.6, 0.65, 0.7]


def _carregar(nome: str) -> list[dict]:
    caminho = PASTA / nome
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else []


# --- 1. busca -----------------------------------------------------------------


def avaliar_busca(perguntas: list[dict]) -> dict:
    no_escopo = [p for p in perguntas if p["esperados"]]
    fora = [p for p in perguntas if not p["esperados"]]
    saida: dict = {"n": len(no_escopo), "fora_do_escopo": len(fora), "modos": {}, "erros_hibrido": []}
    for modo in MODOS:
        a1 = a3 = 0
        rr = []
        tempos = []
        for p in no_escopo:
            t0 = time.perf_counter()
            docs = [r.documento for r in buscar(p["pergunta"], k=5, modo=modo)]
            tempos.append((time.perf_counter() - t0) * 1000)
            pos = next((i for i, d in enumerate(docs) if d in p["esperados"]), None)
            a1 += pos == 0
            a3 += pos is not None and pos < 3
            rr.append(1 / (pos + 1) if pos is not None else 0)
            if modo == "hibrido" and (pos is None or pos > 0):
                saida["erros_hibrido"].append(
                    {"pergunta": p["pergunta"], "esperados": p["esperados"], "veio": docs[:3]}
                )
        n = max(len(no_escopo), 1)
        saida["modos"][modo] = {
            "acerto@1": round(a1 / n, 3),
            "acerto@3": round(a3 / n, 3),
            "mrr": round(sum(rr) / n, 3),
            "ms_mediana": round(statistics.median(tempos), 1) if tempos else 0,
        }
    # Corte de escopo: quantas fora do escopo seriam recusadas x quantas boas perdidas.
    cortes = {}
    for corte in CORTES:
        recusadas = sum(1 for p in fora if not buscar(p["pergunta"], k=3, dist_max=corte))
        perdidas = sum(1 for p in no_escopo if not buscar(p["pergunta"], k=3, dist_max=corte))
        cortes[str(corte)] = {"fora_recusadas": recusadas, "boas_perdidas": perdidas}
    saida["corte_escopo"] = cortes
    return saida


# --- 2. recomendação ----------------------------------------------------------------

PERFIS = [
    {"estatura_cm": 150, "peso_kg": 50},
    {"estatura_cm": 158, "peso_kg": 62, "orcamento_brl": 1500},
    {"estatura_cm": 168, "peso_kg": 72, "orcamento_brl": 2500, "horas_por_dia": 8},
    {"estatura_cm": 175, "peso_kg": 80},
    {"estatura_cm": 183, "peso_kg": 95, "horas_por_dia": 10},
    {"estatura_cm": 192, "peso_kg": 115},
    {"estatura_cm": 200, "peso_kg": 130},
]
CAMPOS_NEC = {"orcamento_brl", "horas_por_dia"}


def avaliar_recomendacao() -> dict:
    violacoes = []
    por_perfil = []
    for perfil in PERFIS:
        medidas = {k: v for k, v in perfil.items() if k not in CAMPOS_NEC}
        nec = Necessidades(**{k: v for k, v in perfil.items() if k in CAMPOS_NEC})
        m = calcular(**medidas)
        recs = recomendar(m, nec, limite=5)
        lo, hi = m.altura_assento_faixa_cm
        for r in recs:
            c = r.cadeira
            if c.altura_assento_min_cm is not None and (c.altura_assento_min_cm > hi or c.altura_assento_max_cm < lo):
                violacoes.append(f"{c.slug} não alcança a altura para {perfil}")
            if c.carga_maxima_kg is not None and c.carga_maxima_kg < perfil["peso_kg"]:
                violacoes.append(f"{c.slug} não aguenta {perfil['peso_kg']} kg")
            if nec.orcamento_brl and c.preco_referencia_brl and float(c.preco_referencia_brl) > nec.orcamento_brl:
                violacoes.append(f"{c.slug} acima do orçamento")
            if c.categoria == "gamer":
                violacoes.append(f"{c.slug} é gamer sem pedido")
        por_perfil.append({
            "perfil": perfil,
            "assento_ideal_cm": round(m.altura_assento_ideal_cm, 1),
            "top3": [r.cadeira.slug for r in recs[:3]],
            "com_dado_incerto_no_top3": sum(1 for r in recs[:3] if r.alertas),
        })
    # Cobertura: quantas cadeiras do catálogo alcançam a altura ideal, por estatura.
    cadeiras = list(Cadeira.objects.all())
    cobertura = {}
    for h in range(145, 206, 5):
        m = calcular(estatura_cm=h)
        alcancam = sum(1 for c in cadeiras if avaliar(c, m, Necessidades(incluir_gamer=True)))
        cobertura[h] = alcancam
    return {"violacoes": violacoes, "perfis": por_perfil, "cobertura_por_estatura": cobertura,
            "total_cadeiras": len(cadeiras)}


# --- 3. agente --------------------------------------------------------------

PROMPT_JUIZ = """Você avalia respostas de um assistente de cadeiras ergonômicas.
Dados: a PERGUNTA, os RESULTADOS das ferramentas (a única fonte válida de números e fatos) e a RESPOSTA.
Dê notas de 1 a 5:
- fundamentada: 5 = todo fato e número da resposta está nos resultados ou é conhecimento geral inofensivo; 1 = inventa dados.
- util: 5 = responde de forma completa e direta ao que foi perguntado; 1 = não responde.
Responda SÓ um JSON: {"fundamentada": n, "util": n, "motivo": "uma frase"}"""


def _juiz(pergunta: str, resultados: list, resposta: str) -> dict:
    from assistente import llm

    contexto = json.dumps(resultados, ensure_ascii=False, default=str)[:9000]
    r = llm.conversar(
        [
            {"role": "system", "content": PROMPT_JUIZ},
            {"role": "user", "content": f"PERGUNTA: {pergunta}\n\nRESULTADOS: {contexto}\n\nRESPOSTA: {resposta}"},
        ],
        [],
    )
    texto = r.conteudo.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        return json.loads(texto[texto.index("{"): texto.rindex("}") + 1])
    except ValueError:
        return {"erro": texto[:200]}


def avaliar_agente(juiz: bool = False) -> dict:
    from assistente.agente import responder
    from assistente.models import ChamadaFerramenta, Conversa

    usuario, _ = get_user_model().objects.get_or_create(username="avaliador")
    usuario.user_permissions.add(Permission.objects.get(codename="usar_assistente"))
    usuario = get_user_model().objects.get(pk=usuario.pk)
    casos = _carregar("casos_agente.json")
    linhas = []
    for caso in casos:
        conversa = Conversa.objects.create(dono=usuario, titulo=f"[eval] {caso['pergunta'][:60]}")
        res = responder(usuario, conversa, caso["pergunta"])
        usadas = [p["ferramenta"] for p in res.passos if "ferramenta" in p]
        esperadas = set(caso["ferramentas"])
        # Sem ferramenta esperada (fora do escopo, injeção): qualquer escolha vale; o que
        # se mede ali é o texto proibido.
        ok_ferr = esperadas.issubset(usadas) if esperadas else True
        proibido = [t for t in caso.get("nao_deve_conter", []) if t.lower() in res.texto.lower()]
        linha = {
            "pergunta": caso["pergunta"],
            "modo": res.modo,
            "modelo": res.modelo,
            "ferramentas_esperadas": sorted(esperadas),
            "ferramentas_usadas": usadas,
            "ferramenta_ok": ok_ferr,
            "numeros_sem_lastro": res.alertas,
            "texto_proibido": proibido,
            "latencia_ms": res.latencia_ms,
            "tokens": res.tokens_entrada + res.tokens_saida,
            "resposta": res.texto,
        }
        if juiz and res.modo == "ia":
            resultados = list(ChamadaFerramenta.objects.filter(conversa=conversa).values_list("resultado", flat=True))
            linha["juiz"] = _juiz(caso["pergunta"], resultados, res.texto)
        linhas.append(linha)
    com_ia = [x for x in linhas if x["modo"] == "ia"]
    lat = sorted(x["latencia_ms"] for x in com_ia) or [0]
    notas = [x["juiz"] for x in com_ia if "juiz" in x and "fundamentada" in x["juiz"]]
    resumo = {
        "casos": len(linhas),
        "respondidos_com_ia": len(com_ia),
        "ferramenta_certa": round(sum(x["ferramenta_ok"] for x in com_ia) / max(len(com_ia), 1), 3),
        "com_numero_sem_lastro": sum(1 for x in com_ia if x["numeros_sem_lastro"]),
        "violou_texto_proibido": sum(1 for x in linhas if x["texto_proibido"]),
        "latencia_p50_ms": lat[len(lat) // 2],
        "latencia_p95_ms": lat[min(len(lat) - 1, int(len(lat) * 0.95))],
        "tokens_medio": round(statistics.mean([x["tokens"] for x in com_ia]), 0) if com_ia else 0,
        "custo_usd": 0.0,  # modelos :free do OpenRouter
    }
    if notas:
        resumo["juiz_fundamentada_media"] = round(statistics.mean(n["fundamentada"] for n in notas), 2)
        resumo["juiz_util_media"] = round(statistics.mean(n["util"] for n in notas), 2)
    return {"resumo": resumo, "casos": linhas}


def rodar(agente: bool = False, juiz: bool = False) -> dict:
    resultado = {
        "quando": time.strftime("%Y-%m-%d %H:%M"),
        "busca_dev": avaliar_busca(_carregar("perguntas_dev.json")),
        "busca_cegas": avaliar_busca(_carregar("perguntas_cegas.json")),
        "recomendacao": avaliar_recomendacao(),
    }
    if agente:
        resultado["agente"] = avaliar_agente(juiz=juiz)
    return resultado


def relatorio_md(r: dict) -> str:
    linhas = [f"# Resultados da avaliação — {r['quando']}", ""]
    for nome in ("busca_dev", "busca_cegas"):
        b = r[nome]
        if not b["n"]:
            continue
        linhas += [f"## Busca — {nome.split('_')[1]} ({b['n']} perguntas no escopo, {b['fora_do_escopo']} fora)", "",
                   "| modo | acerto@1 | acerto@3 | MRR | ms (mediana) |", "|---|---|---|---|---|"]
        for modo, v in b["modos"].items():
            linhas.append(f"| {modo} | {v['acerto@1']:.0%} | {v['acerto@3']:.0%} | {v['mrr']:.2f} | {v['ms_mediana']} |")
        linhas += ["", "Corte de escopo por distância (fora recusadas / boas perdidas): " + ", ".join(
            f"{k}: {v['fora_recusadas']}/{v['boas_perdidas']}" for k, v in b["corte_escopo"].items()), ""]
        if b["erros_hibrido"]:
            linhas.append("Erros do híbrido (o esperado não veio em 1º):")
            linhas += [f"- \"{e['pergunta']}\" → esperado {e['esperados']}, veio {e['veio']}" for e in b["erros_hibrido"]]
            linhas.append("")
    rec = r["recomendacao"]
    linhas += ["## Recomendação", "", f"Violações de invariantes: **{len(rec['violacoes'])}**", ""]
    linhas += [f"- {v}" for v in rec["violacoes"]]
    linhas += ["| perfil | assento ideal | top 3 |", "|---|---|---|"]
    for p in rec["perfis"]:
        linhas.append(f"| {p['perfil']} | {p['assento_ideal_cm']} cm | {', '.join(p['top3']) or '—'} |")
    linhas += ["", f"Cobertura (cadeiras de {rec['total_cadeiras']} que alcançam a altura ideal, por estatura): "
               + ", ".join(f"{h} cm: {n}" for h, n in rec["cobertura_por_estatura"].items()), ""]
    if "agente" in r:
        a = r["agente"]["resumo"]
        linhas += ["## Agente", "", *[f"- {k}: {v}" for k, v in a.items()], ""]
        for c in r["agente"]["casos"]:
            marca = "✔" if c["ferramenta_ok"] else "✘"
            linhas.append(f"- {marca} \"{c['pergunta']}\" — usou {c['ferramentas_usadas']} ({c['modo']}, "
                          f"{c['latencia_ms']} ms){' ⚠ ' + '; '.join(c['numeros_sem_lastro']) if c['numeros_sem_lastro'] else ''}"
                          f"{' juiz=' + json.dumps(c['juiz'], ensure_ascii=False) if 'juiz' in c else ''}")
    return "\n".join(linhas) + "\n"
