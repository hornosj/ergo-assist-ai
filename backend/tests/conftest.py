import pytest
from django.contrib.auth.models import Permission
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from catalogo.models import Cadeira
from conhecimento.embeddings import obter_embedder


@pytest.fixture(autouse=True)
def _sem_rede(settings):
    """Testes nunca chamam o OpenRouter nem baixam modelo de embedding."""
    settings.OPENROUTER_APIKEY = ""
    settings.EMBEDDINGS = "fake"
    obter_embedder.cache_clear()
    yield
    obter_embedder.cache_clear()


def criar_usuario(django_user_model, nome="ana", com_permissao=True):
    u = django_user_model.objects.create_user(username=nome, password="Senha-forte-123")
    if com_permissao:
        u.user_permissions.add(Permission.objects.get(codename="usar_assistente"))
    return django_user_model.objects.get(pk=u.pk)  # recarrega o cache de permissões


@pytest.fixture
def usuario(django_user_model):
    return criar_usuario(django_user_model)


@pytest.fixture
def cliente(usuario):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=usuario).key}")
    return c


def cadeira(**kw) -> Cadeira:
    base = dict(
        slug="teste-boa", marca="Marca", modelo="Boa", categoria="escritorio",
        preco_referencia_brl=2000, faixa_preco="intermediaria",
        altura_assento_min_cm=40, altura_assento_max_cm=52,
        profundidade_assento_min_cm=42, profundidade_assento_max_cm=48,
        regula_profundidade_assento=True, largura_assento_cm=48,
        apoio_lombar="regulavel_altura", bracos="4D", mecanismo="syncro",
        carga_maxima_kg=120, garantia_anos=5, certificacao_nbr13962=True,
        fontes=["https://exemplo.com/ficha"],
    )
    base.update(kw)
    return Cadeira.objects.create(**base)
