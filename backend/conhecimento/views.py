from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .busca import buscar


class BuscaView(APIView):
    """GET ?q=... -> trechos da base com fonte (a busca do RAG, exposta)."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        q = request.query_params.get("q", "")
        modo = request.query_params.get("modo", "hibrido")
        if modo not in ("hibrido", "texto", "vetor"):
            modo = "hibrido"
        return Response([r.como_dict() for r in buscar(q, k=5, modo=modo)])
