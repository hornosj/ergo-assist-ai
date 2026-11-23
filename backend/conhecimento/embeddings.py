"""Embeddings locais (fastembed/ONNX, sem GPU e sem custo por chamada).

`EMBEDDINGS=on` usa o modelo multilíngue; `off` desliga a metade vetorial da
busca (fica só a textual); `fake` é determinístico, para testes.
"""

import hashlib
import math
from functools import lru_cache

from django.conf import settings


class EmbedderFalso:
    """Vetor por hash de palavras: estável, rápido, sem download (testes)."""

    dim = settings.EMBEDDING_DIM

    def embed(self, textos: list[str]) -> list[list[float]]:
        saida = []
        for texto in textos:
            v = [0.0] * self.dim
            for palavra in texto.lower().split():
                h = int(hashlib.md5(palavra.encode()).hexdigest(), 16)
                v[h % self.dim] += 1.0
            norma = math.sqrt(sum(x * x for x in v)) or 1.0
            saida.append([x / norma for x in v])
        return saida


class EmbedderFastembed:
    dim = settings.EMBEDDING_DIM

    def __init__(self):
        from fastembed import TextEmbedding

        cache = settings.BASE_DIR / ".cache" / "fastembed"
        self._modelo = TextEmbedding(settings.EMBEDDING_MODEL, cache_dir=str(cache))

    def embed(self, textos: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._modelo.embed(textos)]


@lru_cache(maxsize=1)
def obter_embedder():
    modo = settings.EMBEDDINGS
    if modo == "off":
        return None
    if modo == "fake":
        return EmbedderFalso()
    return EmbedderFastembed()
