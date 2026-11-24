"""Phase 1 demo: ingest sample docs, build graph + vectors, run hybrid lookup.

Run:
    python run_phase1_demo.py
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.ingestion.pipeline import IngestionPipeline

if __name__ == "__main__":
    data_dir = Path("data_docs")
    print("[demo] Ensuring sample documents...")
    from src.ingestion.loaders import ensure_sample_docs

    ensure_sample_docs(data_dir)
    print(f"[demo] Documents directory: {data_dir}")

    print("[demo] Starting ingestion pipeline...")
    pipe = IngestionPipeline()
    result = pipe.run(data_dir)

    print("\n=== INGESTION SUMMARY ===")
    print(f"Docs parsed:        {result['docs']}")
    print(f"Chunks created:     {result['chunks']}")
    print(f"Entities extracted: {result['entities']}")
    print(f"Relations found:    {result['relations']}")
    print(f"Graph nodes:        {result['graph_stats']['nodes']}")
    print(f"Graph edges:        {result['graph_stats']['edges']}")
    print(f"Vectors stored:     {result['vectors']}")
    print("\nSample entities:")
    for e in result["sample_entities"]:
        print(f"  - {e['name']} ({e['type']})")

    print("\n=== HYBRID LOOKUP: 'Who acquired DeepMind?' ===")
    hits = pipe.hybrid_lookup("Who acquired DeepMind?")
    print(f"Vector hits: {len(hits['vector_hits'])}")
    for chunk_id, score, text in hits["vector_hits"]:
        print(f"  [{score}] {text[:140]}...")

    print("\nDemo complete.")
