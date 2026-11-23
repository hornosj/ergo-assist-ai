import json

import pytest

from catalogo.importacao import importar
from catalogo.models import Cadeira
from conhecimento.busca import buscar
from conhecimento.indexacao import fatiar, indexar

DOC_ASSENTO = """---
titulo: Altura do assento
fontes:
- https://exemplo.com/assento
---
A altura do assento define a posição das pernas.

## Como regular
Os pés ficam apoiados no chão e as coxas na horizontal. A altura poplítea é a referência.

## Erros comuns
Assento alto demais pressiona a parte de trás das coxas.
"""

DOC_MONITOR = """---
titulo: Posição do monitor
fontes:
- https://exemplo.com/monitor
---
## Altura da tela
O topo da tela fica na altura dos olhos ou um pouco abaixo, a um braço de distância.
"""


@pytest.fixture
def base(tmp_path):
    (tmp_path / "altura-do-assento.md").write_text(DOC_ASSENTO, encoding="utf-8")
    (tmp_path / "monitor.md").write_text(DOC_MONITOR, encoding="utf-8")
    indexar(tmp_path)
    return tmp_path


def test_fatiar_por_secao_com_titulo():
    partes = fatiar("Altura do assento", DOC_ASSENTO.split("---", 2)[2])
    secoes = [s for s, _ in partes]
    assert secoes == ["Introdução", "Como regular", "Erros comuns"]
    assert all(t.startswith("Altura do assento — ") for _, t in partes)


@pytest.mark.django_db
class TestBusca:
    def test_hibrida_acha_o_documento_certo(self, base):
        r = buscar("como regular a altura do assento", k=2)
        assert r[0].documento == "altura-do-assento"
        assert r[0].fontes == ["https://exemplo.com/assento"]

    def test_texto_ignora_acento_e_flexao(self, base):
        r = buscar("monitores e olhos", k=1, modo="texto")
        assert r and r[0].documento == "monitor"

    def test_vetor_sozinho_funciona(self, base):
        r = buscar("topo da tela", k=1, modo="vetor")
        assert r and r[0].documento == "monitor"

    def test_reindexar_sem_mudanca_pula(self, base):
        assert indexar(base)["pulados"] == 2

    def test_pergunta_vazia(self, base):
        assert buscar("   ") == []


@pytest.mark.django_db
def test_importar_catalogo(tmp_path):
    itens = [
        {"id": "a-x", "marca": "A", "modelo": "X", "categoria": "escritorio", "preco_referencia_brl": 7000,
         "faixa_preco": "alta", "fontes": ["https://a"], "variante": None, "consultado_em": "2026-11-23"},
        {"id": "sem-fonte", "marca": "B", "modelo": "Y", "categoria": "escritorio", "fontes": []},
    ]
    (tmp_path / "cadeiras_teste.json").write_text(json.dumps(itens), encoding="utf-8")
    r = importar(tmp_path)
    assert r["criados"] == 1 and len(r["erros"]) == 1
    c = Cadeira.objects.get(slug="a-x")
    assert c.faixa_preco == "premium"  # a faixa sai do preço
    assert c.variante == ""
