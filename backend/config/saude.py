from django.db import connection
from django.http import JsonResponse


class SaudeMiddleware:
    """Responde /api/saude antes da checagem de ALLOWED_HOSTS.

    O health check do Fly chega pelo IP interno da máquina, não pelo domínio;
    sem isso o Django devolveria 400 (DisallowedHost) e o Fly mataria a máquina.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/api/saude":
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
            return JsonResponse({"ok": True})
        return self.get_response(request)
