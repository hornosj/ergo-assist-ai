from django.conf import settings
from django.contrib import admin
from django.db import connection
from django.http import FileResponse, Http404, JsonResponse
from django.urls import include, path, re_path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from assistente import views as a
from catalogo.views import CadeiraViewSet
from conhecimento.views import BuscaView
from medidas.views import CalcularView, PerfilView

def saude(request):
    """Health check do Fly: responde e confere o banco."""
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
    return JsonResponse({"ok": True})


def spa(request, caminho=""):
    """Rotas do React (/, /medidas, /catalogo…) devolvem o index.html do build."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        raise Http404("frontend não compilado (rode npm run build)")
    return FileResponse(open(index, "rb"), content_type="text/html")


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
    path("api/saude", saude),
    # Tudo que não é API/admin/arquivo é rota do SPA.
    re_path(r"^(?!api/|admin/|static/)(?P<caminho>[^.]*)$", spa),
]
