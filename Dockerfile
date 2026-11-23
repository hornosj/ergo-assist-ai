# Imagem única: build do React + Django (gunicorn) servindo API e SPA.
# Nenhum segredo entra aqui: chaves chegam em runtime por `fly secrets`.

# --- 1) frontend -------------------------------------------------------------
FROM node:22-alpine AS front
WORKDIR /front
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- 2) backend ----------------------------------------------------------------
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE=/opt/fastembed \
    FRONTEND_DIST=/app/frontend_dist \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Modelo de embeddings baixado no build (versão fixa pelo nome do modelo), para a
# máquina não baixar ~220 MB a cada boot.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', cache_dir='/opt/fastembed')"

COPY backend/ .
COPY --from=front /front/dist /app/frontend_dist
RUN python manage.py collectstatic --noinput

RUN useradd --create-home app && chown -R app /app /opt/fastembed
USER app

EXPOSE 8000
# 1 processo com threads: o modelo de embeddings fica carregado uma vez só na memória.
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "8", "--timeout", "120"]
