"""Recomendação determinística de cadeiras para um corpo e um uso.

Filtros eliminatórios (o que a cadeira PRECISA ter) + pontuação (o que é
melhor). Dado desconhecido não elimina, mas pesa contra e vira aviso: a
recomendação nunca afirma que uma cadeira serve com base em chute.
"""

from dataclasses import dataclass, field

from catalogo.models import Cadeira

from .calculo import Medidas

PESO_LOMBAR = {
    "adaptativo": 3.0,
    "regulavel_altura_profundidade": 3.0,
    "regulavel_altura": 2.0,
    "fixo": 1.0,
    "nenhum": 0.0,
}
PESO_BRACOS = {"4D": 3.0, "3D": 2.5, "2D": 1.5, "1D": 1.0, "fixo": 0.5, "opcional": 0.5, "nenhum": 0.0}
PESO_MECANISMO = {"syncro": 2.0, "autoajustavel": 2.0, "back_system": 1.5, "relax": 0.5, "outro": 0.5}


@dataclass
class Necessidades:
    orcamento_brl: float | None = None
    horas_por_dia: float | None = None
    material_preferido: str | None = None  # tela | espuma
    incluir_gamer: bool = False
    quer_apoio_cabeca: bool = False


@dataclass
class Recomendacao:
    cadeira: Cadeira
    pontos: float
    motivos: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)

    def como_dict(self) -> dict:
        c = self.cadeira
        return {
            "slug": c.slug,
            "nome": c.nome,
            "variante": c.variante,
            "preco_referencia_brl": float(c.preco_referencia_brl) if c.preco_referencia_brl else None,
            "faixa_preco": c.faixa_preco,
            "altura_assento_cm": [c.altura_assento_min_cm, c.altura_assento_max_cm],
            "pontos": round(self.pontos, 1),
            "motivos": self.motivos,
            "alertas": self.alertas,
            "fontes": c.fontes,
        }


def avaliar(c: Cadeira, m: Medidas, n: Necessidades) -> Recomendacao | None:
    """Devolve a recomendação pontuada, ou None se a cadeira é eliminada."""
    motivos: list[str] = []
    alertas: list[str] = []
    pontos = 0.0
    ideal = m.altura_assento_ideal_cm
    lo, hi = m.altura_assento_faixa_cm

    # --- eliminatórios ------------------------------------------------------
    if c.categoria == Cadeira.Categoria.GAMER and not n.incluir_gamer:
        return None
    if n.orcamento_brl is not None:
        # Sem preço no Brasil não dá para afirmar que cabe no orçamento.
        if c.preco_referencia_brl is None or float(c.preco_referencia_brl) > n.orcamento_brl:
            return None
    elif c.preco_referencia_brl is None:
        alertas.append("Sem preço de referência no Brasil (importação ou venda sob consulta).")
    if c.altura_assento_min_cm is not None and c.altura_assento_max_cm is not None:
        if c.altura_assento_min_cm > hi or c.altura_assento_max_cm < lo:
            return None  # não chega numa altura aceitável para este corpo
        if c.altura_assento_min_cm <= ideal <= c.altura_assento_max_cm:
            pontos += 3
            motivos.append(
                f"O assento regula de {c.altura_assento_min_cm:g} a {c.altura_assento_max_cm:g} cm "
                f"e alcança os seus {ideal:.0f} cm."
            )
        else:
            pontos += 1
            alertas.append(
                f"O assento ({c.altura_assento_min_cm:g}–{c.altura_assento_max_cm:g} cm) só chega "
                f"perto dos {ideal:.0f} cm ideais."
            )
    else:
        pontos -= 2
        alertas.append("Faixa de altura do assento não confirmada na fonte.")

    if m.peso_kg is not None:
        if c.carga_maxima_kg is not None:
            if c.carga_maxima_kg < m.peso_kg:
                return None
            if c.carga_maxima_kg < m.peso_kg * 1.1:
                alertas.append(f"Carga máxima ({c.carga_maxima_kg:g} kg) com pouca folga para o seu peso.")
        else:
            pontos -= 1
            alertas.append("Carga máxima não confirmada na fonte.")

    # --- profundidade ---------------------------------------------------------
    if c.profundidade_assento_min_cm is not None:
        if c.profundidade_assento_min_cm > m.profundidade_assento_max_cm:
            pontos -= 3
            alertas.append(
                f"Assento fundo para você ({c.profundidade_assento_min_cm:g} cm; o máximo seria "
                f"~{m.profundidade_assento_max_cm:.0f} cm): a borda pode pressionar a dobra do joelho."
            )
        else:
            pontos += 1
    if c.regula_profundidade_assento:
        pontos += 2
        motivos.append("Regula a profundidade do assento (ajusta ao comprimento da sua coxa).")

    if c.largura_assento_cm is not None and c.largura_assento_cm < m.largura_assento_min_cm:
        pontos -= 2
        alertas.append(f"Assento estreito ({c.largura_assento_cm:g} cm) para o seu quadril estimado.")

    # --- recursos ------------------------------------------------------------
    pontos += PESO_LOMBAR.get(c.apoio_lombar, 0)
    if c.apoio_lombar in ("adaptativo", "regulavel_altura_profundidade", "regulavel_altura"):
        motivos.append(f"Apoio lombar {_lombar_legivel(c.apoio_lombar)}.")
    pontos += PESO_BRACOS.get(c.bracos, 0)
    if c.bracos in ("4D", "3D"):
        motivos.append(f"Braços {c.bracos} (sobem até a altura do cotovelo e acompanham a mesa).")
    elif c.bracos in ("", "nenhum", "fixo"):
        alertas.append("Braços sem regulagem de altura.")
    pontos += PESO_MECANISMO.get(c.mecanismo, 0)
    if c.mecanismo in ("syncro", "autoajustavel"):
        motivos.append("Mecanismo sincronizado: o encosto reclina acompanhando o assento.")

    uso_intenso = (n.horas_por_dia or 0) >= 6
    if uso_intenso:
        # Para quem passa o dia sentado, regulagem pesa mais.
        pontos += 0.5 * PESO_BRACOS.get(c.bracos, 0) + (1.5 if c.regula_profundidade_assento else 0)

    if c.certificacao_nbr13962:
        pontos += 1.5
        motivos.append("Fabricante declara conformidade com a ABNT NBR 13962.")
    if c.garantia_anos and c.garantia_anos >= 5:
        pontos += 1
        motivos.append(f"Garantia de {c.garantia_anos:g} anos.")
    if n.material_preferido and n.material_preferido in (c.material_encosto, c.material_assento):
        pontos += 1
    if n.quer_apoio_cabeca:
        pontos += 1.5 if c.apoio_cabeca in ("regulavel", "fixo") else -1
    if c.categoria == Cadeira.Categoria.GAMER:
        alertas.append("Cadeira gamer: costuma ter encosto e lombar fixos (almofadas soltas).")

    incertos = len(c.campos_incertos or [])
    pontos -= 0.3 * incertos

    return Recomendacao(cadeira=c, pontos=pontos, motivos=motivos, alertas=alertas)


def recomendar(m: Medidas, n: Necessidades, limite: int = 5, qs=None) -> list[Recomendacao]:
    qs = qs if qs is not None else Cadeira.objects.all()
    avaliadas = [r for c in qs if (r := avaliar(c, m, n)) is not None]
    avaliadas.sort(
        key=lambda r: (-r.pontos, float(r.cadeira.preco_referencia_brl or 10**9))
    )
    return avaliadas[:limite]


def _lombar_legivel(valor: str) -> str:
    return {
        "adaptativo": "adaptativo (acompanha a coluna)",
        "regulavel_altura_profundidade": "regulável em altura e profundidade",
        "regulavel_altura": "regulável em altura",
        "fixo": "fixo",
    }.get(valor, valor)

