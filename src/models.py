"""Shared models used across all swarm phases."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import hashlib
import re


def make_id(kind: str, text: str) -> str:
    h = hashlib.sha256(f"{kind}:{text.strip().lower()}".encode()).hexdigest()[:12]
    return f"{kind}_{h}"


@dataclass
class Document:
    doc_id: str
    source_path: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def chunks(self) -> List["Chunk"]:
        return chunk_text(self)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    index: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Entity:
    entity_id: str
    name: str
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    source: str  # entity_id
    target: str  # entity_id
    type: str
    confidence: float = 1.0
    evidence_chunk_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def chunk_text(doc: Document, max_chars: int = 1200, overlap: int = 150) -> List[Chunk]:
    text = re.sub(r"\s+", " ", doc.text).strip()
    chunks: List[Chunk] = []
    if not text:
        return chunks
    start, idx = 0, 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        # prefer sentence boundary
        if end < len(text):
            cut = text.rfind(". ", start, end)
            if cut > start + 200:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(Chunk(
                chunk_id=f"{doc.doc_id}_c{idx}",
                doc_id=doc.doc_id,
                text=piece,
                index=idx,
                metadata={**doc.metadata, "source_path": doc.source_path},
            ))
            idx += 1
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks
