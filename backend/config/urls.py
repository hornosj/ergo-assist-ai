from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from assistente import views as a
from catalogo.views import CadeiraViewSet
from conhecimento.views import BuscaView
from medidas.views import CalcularView, PerfilView

router = DefaultRouter()
router.register("cadeiras", CadeiraViewSet, basename="cadeira")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/auth/cadastro", a.CadastroView.as_view()),
    path("api/auth/token", obtain_auth_token),
    path("api/auth/eu", a.EuView.as_view()),
    path("api/medidas/calcular", CalcularView.as_view()),
    path("api/perfil", PerfilView.as_view()),
    path("api/conhecimento/busca", BuscaView.as_view()),
    path("api/conversas", a.ConversasView.as_view()),
    path("api/conversas/<int:pk>", a.ConversaView.as_view()),
    path("api/conversas/<int:pk>/mensagens", a.MensagensView.as_view()),
    path("api/acoes/<int:pk>/<str:decisao>", a.AcaoView.as_view()),
    path("api/auditoria", a.AuditoriaView.as_view()),
]
