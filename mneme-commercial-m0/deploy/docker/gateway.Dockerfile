# Shared image for gateway + console-api + validator + demo. The MiniLM
# weights are baked in at build time so first-run doesn't reach the network.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/hf-cache \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf-cache \
    MNEME_MANIFEST_PATH=/manifest \
    MNEME_SCHEMA_SQL=/app/deploy/docker/postgres-init.sql

RUN apt-get update && apt-get install -y --no-install-recommends \
        git build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy everything that's needed for editable installs of the libs.
COPY libs /app/libs
COPY services /app/services
COPY demo /app/demo
COPY manifest /manifest
COPY deploy/docker/postgres-init.sql /app/deploy/docker/postgres-init.sql

# Install all packages — order matters because gateway depends on classifier,
# schemas, and index-sync (for the embedder import).
RUN pip install --upgrade pip wheel \
 && pip install -e /app/libs/classifier \
 && pip install -e /app/libs/schemas \
 && pip install -e /app/services/index_sync \
 && pip install -e /app/services/validator \
 && pip install -e /app/services/console_api \
 && pip install -e /app/services/gateway \
 && pip install -e /app/demo

# Pre-download the embedding model so first call is fast.
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" \
 || echo "warn: model pre-download skipped (offline build); will download on first use"

# Default command is overridden per service in docker-compose.yml.
EXPOSE 8001 8002 8003 8004
CMD ["python", "-m", "mneme_gateway.main"]
