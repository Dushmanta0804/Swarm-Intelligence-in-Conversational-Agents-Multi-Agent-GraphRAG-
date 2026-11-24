"""Phase 1 acceptance tests (F-01)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.loaders import ensure_sample_docs
from src.ingestion.deduplicator import normalize


def test_ingestion_builds_graph_and_vectors(tmp_path):
    ensure_sample_docs(tmp_path)
    pipe = IngestionPipeline()
    result = pipe.run(tmp_path)
    assert result["docs"] >= 3, result
    assert result["chunks"] >= 3, result
    assert result["entities"] >= 5, result
    assert result["relations"] >= 3, result
    assert result["graph_stats"]["nodes"] == result["entities"]
    assert result["vectors"] == result["chunks"]


def test_synonym_resolution():
    assert normalize("Google") == "Alphabet Inc."
    assert normalize("google") == "Alphabet Inc."
    assert normalize("Alphabet") == "Alphabet Inc."


def test_hybrid_lookup_returns_hits(tmp_path):
    ensure_sample_docs(tmp_path)
    pipe = IngestionPipeline()
    pipe.run(tmp_path)
    out = pipe.hybrid_lookup("Who acquired DeepMind?")
    assert len(out["vector_hits"]) > 0
    assert out["graph_stats"]["nodes"] > 0


def test_google_alphabet_merged(tmp_path):
    ensure_sample_docs(tmp_path)
    pipe = IngestionPipeline()
    pipe.run(tmp_path)
    names = [n[1]["name"] for n in pipe.graph._g.nodes(data=True)]
    assert "Alphabet Inc." in names
    assert "Google" not in names, f"Google should merge into Alphabet Inc., got {names}"
