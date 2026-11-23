"""Lê `data/conhecimento/*.md`, quebra em trechos e indexa (texto + vetor).

Formato do documento:

    ---
    titulo: Altura do assento
    fontes:
    - https://...
    ---
    Texto de abertura...

    ## Seção
    Texto...
"""

import hashlib
import re
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction

from .embeddings import obter_embedder
from .models import Documento, Trecho

TAMANHO_MAX = 900  # caracteres por trecho (≈ 200 tokens)


def ler_documento(caminho: Path) -> dict:
    bruto = caminho.read_text(encoding="utf-8")
    meta = {"titulo": caminho.stem, "fontes": []}
    corpo = bruto
    if bruto.startswith("---"):
        _, cabecalho, corpo = bruto.split("---", 2)
        chave = None
        for linha in cabecalho.strip().splitlines():
            if linha.startswith("- ") and chave == "fontes":
                meta["fontes"].append(linha[2:].strip())
            elif ":" in linha:
                chave, valor = (p.strip() for p in linha.split(":", 1))
                if valor:
                    meta[chave] = valor
    return {"slug": caminho.stem, "corpo": corpo.strip(), **meta}


def fatiar(titulo: str, corpo: str) -> list[tuple[str, str]]:
    """Quebra por seção (##) e, se a seção for longa, por parágrafo."""
    secoes = re.split(r"^## +", corpo, flags=re.M)
    trechos: list[tuple[str, str]] = []
    for i, bloco in enumerate(secoes):
        if not bloco.strip():
            continue
        if i == 0:
            nome, texto = "Introdução", bloco
        else:
            nome, _, texto = bloco.partition("\n")
        atual = ""
        for paragrafo in re.split(r"\n\s*\n", texto.strip()):
            if atual and len(atual) + len(paragrafo) > TAMANHO_MAX:
                trechos.append((nome.strip(), atual.strip()))
                atual = ""
            atual += paragrafo + "\n\n"
        if atual.strip():
            trechos.append((nome.strip(), atual.strip()))
    # O título vai junto no texto indexado: dá contexto ao trecho isolado.
    return [(secao, f"{titulo} — {secao}\n{texto}") for secao, texto in trechos]


@transaction.atomic
def indexar(pasta: Path | None = None, forcar: bool = False) -> dict:
    pasta = pasta or settings.DATA_DIR / "conhecimento"
    embedder = obter_embedder()
    vistos, indexados, pulados = set(), 0, 0
    for caminho in sorted(pasta.glob("*.md")):
        doc = ler_documento(caminho)
        vistos.add(doc["slug"])
        hash_ = hashlib.sha256(caminho.read_bytes()).hexdigest()
        existente = Documento.objects.filter(slug=doc["slug"]).first()
        if existente and existente.hash_conteudo == hash_ and not forcar:
            pulados += 1
            continue
        documento, _ = Documento.objects.update_or_create(
            slug=doc["slug"],
            defaults={"titulo": doc["titulo"], "fontes": doc["fontes"], "hash_conteudo": hash_},
        )
        documento.trechos.all().delete()
        partes = fatiar(doc["titulo"], doc["corpo"])
        vetores = embedder.embed([t for _, t in partes]) if embedder else [None] * len(partes)
        Trecho.objects.bulk_create(
            Trecho(documento=documento, ordem=i, secao=s, texto=t, embedding=v)
            for i, ((s, t), v) in enumerate(zip(partes, vetores))
        )
        indexados += 1
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE conhecimento_trecho SET tsv = to_tsvector('portuguese', unaccent(texto)) "
            "WHERE tsv IS NULL"
        )
    removidos, _ = Documento.objects.exclude(slug__in=vistos).delete()
    return {"indexados": indexados, "pulados": pulados, "removidos": removidos}
