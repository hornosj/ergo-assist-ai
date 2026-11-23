"""Busca híbrida: texto (full-text português, sem acento) + vetor (pgvector).

As duas listas são fundidas por Reciprocal Rank Fusion (RRF): cada trecho
soma 1/(k + posição) em cada lista em que aparece. RRF não precisa calibrar
escalas diferentes (ts_rank x distância de cosseno), só posições.
"""

import json
from dataclasses import dataclass

from django.db import connection

from .embeddings import obter_embedder

K_RRF = 60
DIST_MAX_PADRAO = 0.6  # calibrado nos evals: separa dentro/fora do escopo
CANDIDATOS = 20


@dataclass
class Resultado:
    trecho_id: int
    documento: str
    titulo: str
    secao: str
    texto: str
    fontes: list[str]
    pontuacao: float
    pos_texto: int | None
    pos_vetor: int | None
    distancia: float | None = None

    def como_dict(self) -> dict:
        return self.__dict__.copy()


# A pergunta vira um tsquery com OU entre os termos (plainto usa E, que é
# exigente demais para perguntas em linguagem natural).
SQL_TEXTO = """
SELECT t.id, row_number() OVER (ORDER BY ts_rank_cd(t.tsv, qq.q) DESC) AS pos
FROM conhecimento_trecho t,
     (SELECT replace(plainto_tsquery('portuguese', unaccent(%s))::text, '&', '|')::tsquery AS q) qq
WHERE qq.q::text <> '' AND t.tsv @@ qq.q
ORDER BY ts_rank_cd(t.tsv, qq.q) DESC
LIMIT %s
"""

SQL_VETOR = """
SELECT t.id, row_number() OVER (ORDER BY t.embedding <=> %s::vector) AS pos,
       t.embedding <=> %s::vector AS dist
FROM conhecimento_trecho t
WHERE t.embedding IS NOT NULL
ORDER BY t.embedding <=> %s::vector
LIMIT %s
"""

SQL_TRECHOS = """
SELECT t.id, d.slug, d.titulo, t.secao, t.texto, d.fontes
FROM conhecimento_trecho t JOIN conhecimento_documento d ON d.id = t.documento_id
WHERE t.id = ANY(%s)
"""


def buscar(
    pergunta: str, k: int = 4, modo: str = "hibrido", dist_max: float | None = None
) -> list[Resultado]:
    """modo: hibrido | texto | vetor (os dois últimos servem para os evals).

    dist_max: se o trecho mais próximo por vetor está mais longe que isso
    (distância de cosseno), a busca devolve vazio: pergunta fora do escopo.
    """
    pergunta = (pergunta or "").strip()[:500]
    if not pergunta:
        return []
    pos_texto: dict[int, int] = {}
    pos_vetor: dict[int, int] = {}
    dist: dict[int, float] = {}
    with connection.cursor() as cur:
        if modo in ("hibrido", "texto"):
            cur.execute(SQL_TEXTO, [pergunta, CANDIDATOS])
            pos_texto = {i: p for i, p in cur.fetchall()}
        embedder = obter_embedder() if modo in ("hibrido", "vetor") else None
        if embedder:
            vetor = str(embedder.embed([pergunta])[0])
            cur.execute(SQL_VETOR, [vetor, vetor, vetor, CANDIDATOS])
            linhas_v = cur.fetchall()
            pos_vetor = {i: p for i, p, _ in linhas_v}
            dist = {i: float(d) for i, _, d in linhas_v}
        # Casamento textual é fraco para decidir escopo ("dor nas costas" casa com
        # tudo); a distância vetorial do trecho mais próximo separa melhor
        # (ver evals/RESULTADOS.md).
        if dist_max is not None and dist and min(dist.values()) > dist_max:
            return []
        ids = set(pos_texto) | set(pos_vetor)
        if not ids:
            return []
        pontos = {
            i: (1 / (K_RRF + pos_texto[i]) if i in pos_texto else 0)
            + (1 / (K_RRF + pos_vetor[i]) if i in pos_vetor else 0)
            for i in ids
        }
        melhores = sorted(ids, key=lambda i: -pontos[i])[:k]
        cur.execute(SQL_TRECHOS, [melhores])
        linhas = {r[0]: r for r in cur.fetchall()}
    return [
        Resultado(
            trecho_id=i,
            documento=linhas[i][1],
            titulo=linhas[i][2],
            secao=linhas[i][3],
            texto=linhas[i][4],
            fontes=json.loads(linhas[i][5]) if isinstance(linhas[i][5], str) else linhas[i][5],
            pontuacao=round(pontos[i], 5),
            pos_texto=pos_texto.get(i),
            pos_vetor=pos_vetor.get(i),
            distancia=round(dist[i], 4) if i in dist else None,
        )
        for i in melhores
    ]
