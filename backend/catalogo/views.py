from django.db.models import Q
from rest_framework import permissions, viewsets

from .models import Cadeira
from .serializers import CadeiraSerializer


class CadeiraViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo público, só leitura. A escrita é feita no admin do Django."""

    serializer_class = CadeiraSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        qs = Cadeira.objects.all()
        p = self.request.query_params
        if texto := p.get("q"):
            qs = qs.filter(Q(marca__icontains=texto) | Q(modelo__icontains=texto))
        if faixa := p.get("faixa_preco"):
            qs = qs.filter(faixa_preco=faixa)
        if categoria := p.get("categoria"):
            qs = qs.filter(categoria=categoria)
        if preco_max := p.get("preco_max"):
            qs = qs.filter(preco_referencia_brl__lte=preco_max)
        return qs
