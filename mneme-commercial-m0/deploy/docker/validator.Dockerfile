# Same base image as gateway — all services use this layer.
# We keep two filenames so compose can target them independently if we want
# to slim them later.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/hf-cache \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf-cache \
    MNEME_MANIFEST_PATH=/manifest

RUN apt-get update && apt-get install -y --no-install-recommends \
        git build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY libs /app/libs
COPY services /app/services
COPY demo /app/demo
COPY manifest /manifest

RUN pip install --upgrade pip wheel \
 && pip install -e /app/libs/classifier \
 && pip install -e /app/libs/schemas \
 && pip install -e /app/services/index_sync \
 && pip install -e /app/services/validator \
 && pip install -e /app/services/console_api \
 && pip install -e /app/demo

RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" \
 || echo "warn: model pre-download skipped (offline build); will download on first use"

EXPOSE 8002 8003 8004
CMD ["python", "-m", "mneme_index_sync.main"]
