"""Gera os segredos de produção em `.env.fly` (fora do git e da imagem).

Uso:
    python scripts/gerar_segredos_fly.py            # cria .env.fly se não existir
    python scripts/gerar_segredos_fly.py db         # imprime o bloco do app do banco
    python scripts/gerar_segredos_fly.py web        # imprime o bloco do app web

A saída de `db`/`web` é para ir direto para `fly secrets import` por pipe,
sem passar pela tela nem pelo histórico do shell.
"""

import secrets
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQ = RAIZ / ".env.fly"
LOCAL = RAIZ / "backend" / ".env"


def ler(caminho: Path) -> dict:
    dados = {}
    if caminho.exists():
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.lstrip().startswith("#"):
                k, v = linha.split("=", 1)
                dados[k.strip()] = v.strip()
    return dados


def gerar() -> None:
    if ARQ.exists():
        return
    chave = ler(LOCAL).get("OPENROUTER_APIKEY", "")
    if not chave:
        sys.exit("OPENROUTER_APIKEY não encontrada em backend/.env")
    senha_db = secrets.token_urlsafe(32)
    ARQ.write_text(
        "# Segredos de produção do Fly. NÃO commitar (está no .gitignore).\n"
        f"POSTGRES_PASSWORD={senha_db}\n"
        f"DATABASE_URL=postgres://ergo:{senha_db}@ergo-assist-db.internal:5432/ergo\n"
        f"DJANGO_SECRET_KEY={secrets.token_urlsafe(50)}\n"
        f"CODIGO_CONVITE=ergo-{secrets.token_hex(4)}\n"
        f"OPENROUTER_APIKEY={chave}\n",
        encoding="utf-8",
    )


def bloco(app: str) -> str:
    s = ler(ARQ)
    chaves = ["POSTGRES_PASSWORD"] if app == "db" else [
        "DATABASE_URL", "DJANGO_SECRET_KEY", "CODIGO_CONVITE", "OPENROUTER_APIKEY"]
    return "".join(f"{k}={s[k]}\n" for k in chaves)


if __name__ == "__main__":
    gerar()
    if len(sys.argv) > 1:
        sys.stdout.write(bloco(sys.argv[1]))
