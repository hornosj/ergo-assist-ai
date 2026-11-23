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
