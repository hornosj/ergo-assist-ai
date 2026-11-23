import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

# Em produção, carrega o modelo de embeddings no boot: sem isso, a primeira
# busca depois de a máquina acordar levava ~18 s (medido no Fly em 23/11/2026).
if os.environ.get("FLY_APP_NAME"):
    from conhecimento.embeddings import obter_embedder

    embedder = obter_embedder()
    if embedder:
        embedder.embed(["aquecimento"])
