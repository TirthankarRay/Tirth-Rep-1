"""Local embedder.

Uses sentence-transformers/all-MiniLM-L6-v2 (384-dim). Model is loaded
lazily on first call and cached for the process lifetime. NEVER calls out
to a hosted embedding API — that's an architectural commitment.
"""

from __future__ import annotations

import os
from threading import Lock
from typing import Iterable

_model = None
_lock = Lock()

EMBEDDING_DIM = 384


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                name = os.environ.get(
                    "EMBEDDING_MODEL",
                    "sentence-transformers/all-MiniLM-L6-v2",
                )
                _model = SentenceTransformer(name)
    return _model


def embed(texts: Iterable[str]) -> list[list[float]]:
    texts = list(texts)
    if not texts:
        return []
    model = _get_model()
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vecs]
