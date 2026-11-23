"""Importa os JSONs de `data/catalogo/cadeiras_*.json` para o banco."""

import json
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import Cadeira

CAMPOS = {f.name for f in Cadeira._meta.get_fields() if f.concrete} - {"id", "slug"}
CAMPOS_TEXTO = {
    f.name
    for f in Cadeira._meta.get_fields()
    if f.concrete and f.get_internal_type() in ("CharField", "TextField", "URLField")
}


def faixa_de_preco(preco: float | None) -> str:
    if preco is None:
        return ""
    if preco < 1000:
        return "economica"
    if preco < 2500:
        return "intermediaria"
    if preco <= 6000:
        return "alta"
    return "premium"


def normalizar(item: dict) -> dict:
    dados = {k: v for k, v in item.items() if k in CAMPOS}
    for campo in CAMPOS_TEXTO & dados.keys():
        if dados[campo] is None:
            dados[campo] = ""
    if item.get("consultado_em"):
        dados["consultado_em"] = date.fromisoformat(item["consultado_em"])
    # Com preço, a faixa sai do preço (o rótulo do pesquisador pode divergir).
    if item.get("preco_referencia_brl") is not None:
        dados["faixa_preco"] = faixa_de_preco(item["preco_referencia_brl"])
    dados["fontes"] = item.get("fontes") or []
    dados["campos_incertos"] = item.get("campos_incertos") or []
    return dados


@transaction.atomic
def importar(pasta: Path | None = None) -> dict:
    pasta = pasta or settings.DATA_DIR / "catalogo"
    vistos: set[str] = set()
    criados = atualizados = 0
    erros: list[str] = []
    for arquivo in sorted(pasta.glob("cadeiras_*.json")):
        for item in json.loads(arquivo.read_text(encoding="utf-8")):
            slug = item.get("id")
            if not slug or not item.get("fontes"):
                erros.append(f"{arquivo.name}: item sem id ou sem fonte ({item.get('modelo')})")
                continue
            if slug in vistos:
                erros.append(f"{arquivo.name}: id repetido {slug}")
                continue
            vistos.add(slug)
            _, criado = Cadeira.objects.update_or_create(slug=slug, defaults=normalizar(item))
            criados += criado
            atualizados += not criado
    removidos, _ = Cadeira.objects.exclude(slug__in=vistos).delete()
    return {"criados": criados, "atualizados": atualizados, "removidos": removidos, "erros": erros}
