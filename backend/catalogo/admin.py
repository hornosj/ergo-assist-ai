from django.contrib import admin

from .models import Cadeira


@admin.register(Cadeira)
class CadeiraAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "categoria",
        "faixa_preco",
        "preco_referencia_brl",
        "altura_assento_min_cm",
        "altura_assento_max_cm",
        "carga_maxima_kg",
    )
    list_filter = ("categoria", "faixa_preco", "marca")
    search_fields = ("marca", "modelo")
