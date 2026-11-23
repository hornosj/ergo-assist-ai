from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from pgvector.django import HnswIndex, VectorField


class Documento(models.Model):
    """Um texto da base de conhecimento (data/conhecimento/*.md), com fontes."""

    slug = models.SlugField(max_length=120, unique=True)
    titulo = models.CharField(max_length=200)
    fontes = models.JSONField(default=list)
    hash_conteudo = models.CharField(max_length=64)
    indexado_em = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.titulo


class Trecho(models.Model):
    """Pedaço de documento que o RAG recupera (por texto e por vetor)."""

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="trechos")
    ordem = models.PositiveIntegerField()
    secao = models.CharField(max_length=200, blank=True)
    texto = models.TextField()
    tsv = SearchVectorField(null=True)
    embedding = VectorField(dimensions=settings.EMBEDDING_DIM, null=True)

    class Meta:
        ordering = ["documento", "ordem"]
        indexes = [
            GinIndex(fields=["tsv"], name="trecho_tsv_gin"),
            HnswIndex(
                name="trecho_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"{self.documento.slug}#{self.ordem}"
