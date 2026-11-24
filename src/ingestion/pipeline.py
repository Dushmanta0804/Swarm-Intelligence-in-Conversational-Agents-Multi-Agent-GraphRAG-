"""Phase 1 orchestration pipeline: load -> chunk -> extract -> dedupe -> store."""
from __future__ import annotations
from pathlib import Path
import sys
from typing import Dict, List
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.models import Chunk, Document
from src.ingestion.loaders import load_directory, ensure_sample_docs
from src.ingestion.entity_extractor import extract_from_chunk, LLMExtractorHook
from src.ingestion.deduplicator import deduplicate
from src.ingestion.graph_store import GraphStore
from src.ingestion.vector_store import VectorStore


class IngestionPipeline:
    def __init__(self, graph_backend: str = "local", embedding_mode: str = "local",
                 extractor=None, persist_path: str | None = None):
        self.graph = GraphStore(backend=graph_backend, persist_path=persist_path)
        self.vectors = VectorStore(mode=embedding_mode if embedding_mode in ("local",) else "local")
        # qdrant mode still keeps local mirror for offline search
        if embedding_mode == "qdrant":
            try:
                self.vectors = VectorStore(mode="qdrant")
            except Exception as e:
                print(f"[pipeline] qdrant unavailable, local fallback: {e}")
                self.vectors = VectorStore(mode="local")
        self.extractor = extractor or LLMExtractorHook()

    def run(self, data_dir: str | Path) -> Dict:
        data_dir = Path(data_dir)
        if not data_dir.exists() or not any(data_dir.iterdir()):
            ensure_sample_docs(data_dir)
        docs: List[Document] = load_directory(data_dir)
        all_chunks: List[Chunk] = []
        for d in docs:
            all_chunks.extend(d.chunks)

        raw_entities, raw_relations = [], []
        for ch in all_chunks:
            try:
                ents, rels = self.extractor.extract(ch)
            except Exception:
                ents, rels = extract_from_chunk(ch)
            raw_entities.extend(ents)
            raw_relations.extend(rels)

        entities, relations, report = deduplicate(raw_entities, raw_relations)
        self.graph.upsert_entities(entities)
        self.graph.upsert_relations(relations)
        self.vectors.add_chunks(all_chunks)

        return {
            "docs": len(docs),
            "chunks": len(all_chunks),
            "entities": len(entities),
            "relations": len(relations),
            "graph_stats": self.graph.stats(),
            "vectors": len(self.vectors),
            "dedup_report": report,
            "sample_entities": [{"id": e.entity_id, "name": e.name, "type": e.type} for e in entities[:10]],
        }

    def hybrid_lookup(self, query: str, top_k: int = 5):
        """Scout preview (Phase 2 will expand): vector hits + graph anchor nodes."""
        hits = self.vectors.search(query, top_k=top_k)
        anchors = []
        for chunk, score in hits:
            # naive anchor: graph nodes whose name appears in chunk text
            for node in self.graph.find_by_name(query.split()[0] if query.split() else query):
                anchors.append(node)
                break
        return {"vector_hits": [(c.chunk_id, round(s, 3), c.text[:160]) for c, s in hits],
                "graph_stats": self.graph.stats()}
