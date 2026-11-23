import json

import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from assistente import llm
from assistente.agente import verificar_numeros
from assistente.ferramentas import Contexto, executar
from assistente.models import AcaoPendente, ChamadaFerramenta, Conversa
from medidas.models import Perfil

from .conftest import cadeira, criar_usuario

pytestmark = pytest.mark.django_db


def resposta(conteudo="", chamadas=None):
    return llm.RespostaLLM(modelo="fake/modelo", conteudo=conteudo, chamadas=chamadas or [],
                           tokens_entrada=100, tokens_saida=20, latencia_ms=5)


def chamada(nome, args, id_="c1"):
    return {"id": id_, "type": "function", "function": {"name": nome, "arguments": json.dumps(args)}}


class LLMRoteirizado:
    """Substitui o OpenRouter: devolve respostas prontas, em ordem."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.recebidas = []

    def __call__(self, mensagens, ferramentas, registrar=None):
        self.recebidas.append(mensagens)
        r = self.respostas.pop(0)
        if registrar:
            registrar(r.modelo, True, "", r)
        return r


# --- ferramentas -------------------------------------------------------------


def test_ferramenta_valida_argumentos(usuario):
    ctx = Contexto(usuario, Conversa.objects.create(dono=usuario))
    assert "erro" in executar("calcular_medidas", {"estatura_cm": "alto"}, ctx)
    assert "erro" in executar("calcular_medidas", {"estatura_cm": 900}, ctx)
    assert "erro" in executar("detalhar_cadeiras", {}, ctx)
    assert "erro" in executar("apagar_tudo", {}, ctx)
    ok = executar("calcular_medidas", {"estatura_cm": "175,5"}, ctx)
    assert ok["estatura_cm"] == 175.5


def test_ferramenta_exige_permissao(django_user_model):
    sem = criar_usuario(django_user_model, "bob", com_permissao=False)
    ctx = Contexto(sem, Conversa.objects.create(dono=sem))
    assert executar("calcular_medidas", {"estatura_cm": 170}, ctx) == {"erro": "sem permissão para usar o assistente"}


def test_ferramenta_usa_perfil_salvo_do_proprio_usuario(usuario, django_user_model):
    Perfil.objects.create(dono=usuario, estatura_cm=160)
    outro = criar_usuario(django_user_model, "bia")
    Perfil.objects.create(dono=outro, estatura_cm=190)
    ctx = Contexto(usuario, Conversa.objects.create(dono=usuario))
    assert executar("calcular_medidas", {}, ctx)["estatura_cm"] == 160


def test_propor_perfil_nao_grava_ate_confirmar(usuario, cliente):
    conversa = Conversa.objects.create(dono=usuario)
    r = executar("propor_salvar_perfil", {"estatura_cm": 172, "peso_kg": 70}, Contexto(usuario, conversa))
    assert r["status"] == "pendente"
    assert not Perfil.objects.filter(dono=usuario).exists()
    ok = cliente.post(f"/api/acoes/{r['acao_id']}/confirmar")
    assert ok.status_code == 200
    assert Perfil.objects.get(dono=usuario).estatura_cm == 172
    assert cliente.post(f"/api/acoes/{r['acao_id']}/confirmar").status_code == 409


# --- agente ------------------------------------------------------------------


def test_agente_chama_ferramenta_e_responde(cliente, usuario, monkeypatch, settings):
    settings.OPENROUTER_APIKEY = "x"
    cadeira(slug="boa", carga_maxima_kg=150)
    roteiro = LLMRoteirizado(
        resposta(chamadas=[chamada("recomendar_cadeiras", {"estatura_cm": 175, "peso_kg": 80})]),
        resposta("Para 1,75 m a Marca Boa serve: o assento chega aos 45 cm."),
    )
    monkeypatch.setattr(llm, "conversar", roteiro)
    conv = cliente.post("/api/conversas").json()
    r = cliente.post(f"/api/conversas/{conv['id']}/mensagens", {"texto": "qual cadeira? tenho 1,75 e 80 kg"})
    assert r.status_code == 201, r.content
    corpo = r.json()
    assert corpo["modo"] == "ia"
    assert corpo["passos"][0]["ferramenta"] == "recomendar_cadeiras"
    assert corpo["fontes"][0]["url"] == "https://exemplo.com/ficha"
    assert corpo["alertas"] == []  # 45 e 1,75 têm lastro (ideal 45,0 e a pergunta)
    # o resultado da ferramenta voltou para o modelo como mensagem 'tool'
    assert roteiro.recebidas[1][-1]["role"] == "tool"
    assert ChamadaFerramenta.objects.filter(usuario=usuario, ferramenta="recomendar_cadeiras").count() == 1


def test_agente_sinaliza_numero_inventado(cliente, monkeypatch, settings):
    settings.OPENROUTER_APIKEY = "x"
    monkeypatch.setattr(llm, "conversar", LLMRoteirizado(resposta("A Aeron custa R$ 4.321 e aguenta 199 kg.")))
    conv = cliente.post("/api/conversas").json()
    corpo = cliente.post(f"/api/conversas/{conv['id']}/mensagens", {"texto": "e a aeron?"}).json()
    assert corpo["alertas"] and "4321" in corpo["alertas"][0] and "199" in corpo["alertas"][0]


def test_sem_chave_responde_sem_ia(cliente):
    cadeira(slug="boa")
    conv = cliente.post("/api/conversas").json()
    corpo = cliente.post(f"/api/conversas/{conv['id']}/mensagens",
                         {"texto": "qual cadeira comprar? tenho 1,70 m"}).json()
    assert corpo["modo"] == "sem_ia"
    assert "Marca Boa" in corpo["texto"]


def test_verificar_numeros():
    assert verificar_numeros("assento a 46 cm, 2 dedos", "ideal 46.3") == []
    assert verificar_numeros("custa R$ 1.299", "preco 1299.0") == []
    assert verificar_numeros("aguenta 150 kg", "carga 120") == ["150"]
    # falsos positivos do eval de 23/11: norma, centavos, cm -> m, item de norma
    assert verificar_numeros("segue a NBR 13962 e o item 17.6.6", "") == []
    assert verificar_numeros("custa R$ 1.887,90", '{"preco": 1887.9}') == []
    assert verificar_numeros("indicada para 1,6 a 1,96 m", '{"altura_usuario": [157, 196]}') == []
    assert verificar_numeros("indicada até 1,9 m", '{"altura_usuario": [157, 196]}') == ["1.9"]  # 1,96 m
    assert verificar_numeros("custa R$ 1.950", '{"preco": 1887.9}') == ["1950"]


# --- isolamento e permissões -----------------------------------------------------


def test_conversa_de_outro_usuario_e_404(cliente, django_user_model):
    outro = criar_usuario(django_user_model, "carla")
    alheia = Conversa.objects.create(dono=outro, titulo="segredo")
    assert cliente.get(f"/api/conversas/{alheia.pk}").status_code == 404
    assert cliente.post(f"/api/conversas/{alheia.pk}/mensagens", {"texto": "oi"}).status_code == 404
    acao = AcaoPendente.objects.create(dono=outro, conversa=alheia, tipo="salvar_perfil", resumo="x",
                                       dados={"estatura_cm": 180})
    assert cliente.post(f"/api/acoes/{acao.pk}/confirmar").status_code == 404
    assert [c["id"] for c in cliente.get("/api/conversas").json()] == []


def test_sem_permissao_nao_usa_assistente(django_user_model):
    sem = criar_usuario(django_user_model, "davi", com_permissao=False)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=sem).key}")
    assert c.post("/api/conversas").status_code == 403


def test_anonimo_nao_usa_assistente():
    assert APIClient().post("/api/conversas").status_code == 401


def test_cadastro_da_permissao_e_token():
    r = APIClient().post("/api/auth/cadastro", {"username": "edu", "password": "Senha-forte-123"})
    assert r.status_code == 201
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {r.json()['token']}")
    assert c.get("/api/auth/eu").json()["pode_usar_assistente"] is True
    assert c.post("/api/conversas").status_code == 201


def test_teto_de_gasto_diario_desliga_a_ia(cliente, usuario, monkeypatch, settings):
    from assistente.models import ChamadaLLM

    settings.OPENROUTER_APIKEY = "x"
    settings.LIMITE_GASTO_DIARIO_USD = 0.01
    ChamadaLLM.objects.create(usuario=usuario, modelo="deepseek/x", custo_usd="0.02")
    chamado = []
    monkeypatch.setattr(llm, "conversar", lambda *a, **k: chamado.append(1))
    conv = cliente.post("/api/conversas").json()
    corpo = cliente.post(f"/api/conversas/{conv['id']}/mensagens", {"texto": "como regular o assento?"}).json()
    assert corpo["modo"] == "sem_ia" and chamado == []


def test_custo_da_resposta_e_somado(cliente, monkeypatch, settings):
    settings.OPENROUTER_APIKEY = "x"
    r1 = resposta(chamadas=[chamada("calcular_medidas", {"estatura_cm": 170})])
    r1.custo_usd = 0.0004
    r2 = resposta("Seu assento ideal fica perto de 44 cm.")
    r2.custo_usd = 0.0002
    monkeypatch.setattr(llm, "conversar", LLMRoteirizado(r1, r2))
    conv = cliente.post("/api/conversas").json()
    corpo = cliente.post(f"/api/conversas/{conv['id']}/mensagens", {"texto": "tenho 170 cm"}).json()
    assert float(corpo["custo_usd"]) == pytest.approx(0.0006)


def test_numero_de_turno_anterior_tem_lastro(cliente, monkeypatch, settings):
    settings.OPENROUTER_APIKEY = "x"
    monkeypatch.setattr(llm, "conversar", LLMRoteirizado(resposta("Seu orçamento de R$ 12.000 permite várias.")))
    conv = cliente.post("/api/conversas").json()
    cliente.post(f"/api/conversas/{conv['id']}/mensagens", {"texto": "tenho R$ 12.000 de orçamento"})
    monkeypatch.setattr(llm, "conversar", LLMRoteirizado(resposta("Com R$ 12.000 dá para a premium.")))
    corpo = cliente.post(f"/api/conversas/{conv['id']}/mensagens", {"texto": "e a premium?"}).json()
    assert corpo["alertas"] == []


def test_passos_esgotados_fecham_resposta_sem_ferramentas(cliente, monkeypatch, settings):
    from assistente.agente import MAX_PASSOS

    settings.OPENROUTER_APIKEY = "x"
    em_loop = [resposta(chamadas=[chamada("calcular_medidas", {"estatura_cm": 152}, f"c{i}")]) for i in range(MAX_PASSOS)]
    roteiro = LLMRoteirizado(*em_loop, resposta("Para 1,52 m, poucas cadeiras descem o suficiente."))
    monkeypatch.setattr(llm, "conversar", lambda m, f, registrar=None, **kw: (roteiro.recebidas.append(kw), roteiro(m, f, registrar))[1])
    conv = cliente.post("/api/conversas").json()
    corpo = cliente.post(f"/api/conversas/{conv['id']}/mensagens", {"texto": "sou baixinha, 1,52 m"}).json()
    assert corpo["texto"].startswith("Para 1,52 m")
    assert roteiro.recebidas[-2] == {"tool_choice": "none"}  # a última ida proíbe ferramentas


def test_resposta_vazia_pede_de_novo(cliente, monkeypatch, settings):
    settings.OPENROUTER_APIKEY = "x"
    roteiro = LLMRoteirizado(resposta(""), resposta("Agora sim: regule o assento na altura do joelho."))
    monkeypatch.setattr(llm, "conversar", roteiro)
    conv = cliente.post("/api/conversas").json()
    corpo = cliente.post(f"/api/conversas/{conv['id']}/mensagens", {"texto": "como regular?"}).json()
    assert corpo["texto"].startswith("Agora sim")
    assert roteiro.recebidas[1][-1]["content"].startswith("Escreva agora")


def test_resposta_vazia_pede_de_novo(cliente, monkeypatch, settings):
    settings.OPENROUTER_APIKEY = "x"
    roteiro = LLMRoteirizado(resposta(""), resposta("Agora sim: regule o assento na altura do joelho."))
    monkeypatch.setattr(llm, "conversar", roteiro)
    conv = cliente.post("/api/conversas").json()
    corpo = cliente.post(f"/api/conversas/{conv['id']}/mensagens", {"texto": "como regular?"}).json()
    assert corpo["texto"].startswith("Agora sim")
    assert roteiro.recebidas[1][-1]["content"].startswith("Escreva agora")


def test_teto_global_desliga_a_ia_para_todos(cliente, usuario, django_user_model, monkeypatch, settings):
    from assistente.models import ChamadaLLM

    settings.OPENROUTER_APIKEY = "x"
    settings.LIMITE_GASTO_GLOBAL_DIARIO_USD = 0.05
    outro = criar_usuario(django_user_model, "gastador")
    ChamadaLLM.objects.create(usuario=outro, modelo="deepseek/x", custo_usd="0.06")
    monkeypatch.setattr(llm, "conversar", lambda *a, **k: pytest.fail("não deveria chamar o LLM"))
    conv = cliente.post("/api/conversas").json()
    corpo = cliente.post(f"/api/conversas/{conv['id']}/mensagens", {"texto": "como regular?"}).json()
    assert corpo["modo"] == "sem_ia"


def test_cadastro_exige_convite_quando_configurado(settings):
    settings.CODIGO_CONVITE = "segredo-123"
    c = APIClient()
    assert c.post("/api/auth/cadastro", {"username": "fabi", "password": "Senha-forte-123"}).status_code == 400
    assert c.post("/api/auth/cadastro", {"username": "fabi", "password": "Senha-forte-123",
                                         "convite": "errado"}).status_code == 400
    ok = c.post("/api/auth/cadastro", {"username": "fabi", "password": "Senha-forte-123", "convite": "segredo-123"})
    assert ok.status_code == 201


def test_saude_e_spa(client, settings, tmp_path):
    assert client.get("/api/saude").json() == {"ok": True}
    (tmp_path / "index.html").write_text("<html>ergo</html>", encoding="utf-8")
    settings.FRONTEND_DIST = tmp_path
    r = client.get("/medidas")
    assert r.status_code == 200 and b"ergo" in b"".join(r.streaming_content)
    assert client.get("/api/nao-existe").status_code == 404
