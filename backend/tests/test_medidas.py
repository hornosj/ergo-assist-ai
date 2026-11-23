import pytest

from medidas.calculo import COMPENSACAO_CALCADO_CM, COEFICIENTES, MedidaInvalida, calcular
from medidas.recomendacao import Necessidades, recomendar

from .conftest import cadeira


def test_estima_pela_estatura_e_avisa():
    m = calcular(estatura_cm=175)
    esperado = 175 * COEFICIENTES["altura_poplitea"] + COMPENSACAO_CALCADO_CM
    assert m.altura_assento_ideal_cm == pytest.approx(esperado)
    assert "altura_poplitea_cm" in m.estimadas
    assert any("estimadas" in a for a in m.avisos)


def test_medida_informada_vence_a_estimativa():
    m = calcular(estatura_cm=175, altura_poplitea_cm=40)
    assert m.altura_assento_ideal_cm == pytest.approx(40 + COMPENSACAO_CALCADO_CM)
    assert "altura_poplitea_cm" not in m.estimadas


def test_profundidade_deixa_folga_no_joelho():
    m = calcular(estatura_cm=170, comprimento_nadega_poplitea_cm=48)
    assert m.profundidade_assento_max_cm == pytest.approx(45)


def test_mesa_alta_pede_apoio_para_os_pes():
    m = calcular(estatura_cm=160, altura_mesa_cm=75)
    assert m.apoio_pes_cm and m.apoio_pes_cm > 0
    assert any("apoio para os pés" in a for a in m.avisos)


@pytest.mark.parametrize("kw", [{"estatura_cm": 90}, {"estatura_cm": 175, "peso_kg": 500}, {"estatura_cm": "abc"}])
def test_rejeita_medida_implausivel(kw):
    with pytest.raises(MedidaInvalida):
        calcular(**kw)


@pytest.mark.django_db
class TestRecomendacao:
    def test_elimina_quem_nao_alcanca_a_altura(self):
        cadeira(slug="alta-demais", altura_assento_min_cm=50, altura_assento_max_cm=60)
        cadeira(slug="serve")
        m = calcular(estatura_cm=155)  # ideal ~41 cm
        slugs = [r.cadeira.slug for r in recomendar(m, Necessidades())]
        assert slugs == ["serve"]

    def test_elimina_por_peso_e_orcamento(self):
        cadeira(slug="fraca", carga_maxima_kg=100)
        cadeira(slug="cara", preco_referencia_brl=9000, carga_maxima_kg=150)
        cadeira(slug="ok", carga_maxima_kg=150)
        m = calcular(estatura_cm=180, peso_kg=110)
        slugs = [r.cadeira.slug for r in recomendar(m, Necessidades(orcamento_brl=3000))]
        assert slugs == ["ok"]

    def test_sem_preco_sai_quando_ha_orcamento(self):
        cadeira(slug="importada", preco_referencia_brl=None, faixa_preco="")
        cadeira(slug="com-preco")
        m = calcular(estatura_cm=175)
        assert [r.cadeira.slug for r in recomendar(m, Necessidades(orcamento_brl=3000))] == ["com-preco"]
        sem_orcamento = {r.cadeira.slug: r for r in recomendar(m, Necessidades())}
        assert any("Sem preço" in a for a in sem_orcamento["importada"].alertas)

    def test_gamer_so_quando_pedido(self):
        cadeira(slug="gamer", categoria="gamer")
        m = calcular(estatura_cm=175)
        assert recomendar(m, Necessidades()) == []
        assert [r.cadeira.slug for r in recomendar(m, Necessidades(incluir_gamer=True))] == ["gamer"]

    def test_dado_desconhecido_nao_elimina_mas_perde_para_o_confirmado(self):
        cadeira(slug="sem-dados", altura_assento_min_cm=None, altura_assento_max_cm=None,
                carga_maxima_kg=None, campos_incertos=["altura_assento_min_cm"])
        cadeira(slug="confirmada")
        m = calcular(estatura_cm=175, peso_kg=80)
        recs = recomendar(m, Necessidades())
        assert [r.cadeira.slug for r in recs] == ["confirmada", "sem-dados"]
        assert any("não confirmada" in a for a in recs[1].alertas)

    def test_assento_fundo_gera_alerta(self):
        cadeira(slug="funda", profundidade_assento_min_cm=50, profundidade_assento_max_cm=50,
                regula_profundidade_assento=False)
        m = calcular(estatura_cm=155)
        rec = recomendar(m, Necessidades())[0]
        assert any("fundo" in a for a in rec.alertas)


@pytest.mark.django_db
def test_endpoint_calcular_publico(client):
    cadeira()
    r = client.post("/api/medidas/calcular", {"estatura_cm": 175, "peso_kg": 80}, content_type="application/json")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["medidas"]["altura_assento_ideal_cm"] > 40
    assert corpo["recomendacoes"][0]["slug"] == "teste-boa"


@pytest.mark.django_db
def test_endpoint_calcular_valida(client):
    r = client.post("/api/medidas/calcular", {"estatura_cm": 30}, content_type="application/json")
    assert r.status_code == 400
