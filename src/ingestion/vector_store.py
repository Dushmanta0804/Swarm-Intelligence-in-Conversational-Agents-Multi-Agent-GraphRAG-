"""Vector store: local hashed-TF embeddings (zero-dep) + Qdrant interface ready."""
from __future__ import annotations
import hashlib
import math
import re
from pathlib import Path
import sys
from typing import Dict, List, Tuple
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.models import Chunk

DIM = 256
TOKEN_RE = re.compile(r"[a-z0-9]+")


def embed_text(text: str, dim: int = DIM) -> List[float]:
    tokens = TOKEN_RE.findall(text.lower())
    vec = [0.0] * dim
    for tok in tokens:
        h = int(hashlib.sha256(tok.encode()).hexdigest(), 16) % dim
        vec[h] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class VectorStore:
    def __init__(self, mode: str = "local"):
        self.mode = mode
        self._vecs: Dict[str, Tuple[List[float], Chunk]] = {}
        self._client = None
        if mode == "qdrant":
            from config import SETTINGS
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import Distance, VectorParams
            except ImportError as e:
                raise ImportError("pip install qdrant-client to use EMBEDDING_MODE=qdrant") from e
            self._client = QdrantClient(url=SETTINGS.qdrant_url)
            try:
                self._client.create_collection(SETTINGS.qdrant_collection,
                                               vectors_config=VectorParams(size=DIM, distance=Distance.COSINE))
            except Exception:
                pass

    def add_chunks(self, chunks: List[Chunk]):
        if self.mode == "local":
            for c in chunks:
                self._vecs[c.chunk_id] = (embed_text(c.text), c)
        else:
            from config import SETTINGS
            from qdrant_client.models import PointStruct
            pts = [PointStruct(id=abs(hash(c.chunk_id)) % (2**63),
                               vector=embed_text(c.text),
                               payload={"chunk_id": c.chunk_id, "text": c.text,
                                        "doc_id": c.doc_id}) for c in chunks]
            self._client.upsert(collection_name=SETTINGS.qdrant_collection, points=pts)
            for c in chunks:
                self._vecs[c.chunk_id] = (embed_text(c.text), c)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        q = embed_text(query)
        scored = [(c, cosine(q, v)) for v, c in self._vecs.values()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def __len__(self):
        return len(self._vecs)
