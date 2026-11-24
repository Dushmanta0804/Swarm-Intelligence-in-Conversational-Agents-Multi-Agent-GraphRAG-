"""FastAPI server for Swarm Intelligence GraphRAG.

Run:
    python server.py
Then open: http://localhost:8000/docs
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import sys
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.loaders import ensure_sample_docs

app = FastAPI(
    title="Swarm Intelligence GraphRAG API",
    description="Phase 1: Hybrid Knowledge Graph & Vector Store ingestion + lookup",
    version="1.0.0",
)

DATA_DIR = Path("data_docs")
PIPE = IngestionPipeline()

# Ensure data on startup
ensure_sample_docs(DATA_DIR)


class IngestRequest(BaseModel):
    data_dir: str = "data_docs"


class IngestResponse(BaseModel):
    message: str
    result: dict


class LookupRequest(BaseModel):
    query: str
    top_k: int = 5


class LookupResponse(BaseModel):
    query: str
    hits: list
    graph_stats: dict


@app.on_event("startup")
async def startup():
    """Pre-warm the pipeline on startup."""
    global PIPE
    PIPE = IngestionPipeline()
    PIPE.run(DATA_DIR)
    print(f"[server] Pre-warmed pipeline with {DATA_DIR}")


@app.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):
    """Run ingestion on a data directory."""
    try:
        result = PIPE.run(req.data_dir)
        return IngestResponse(message="Ingestion complete", result=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/lookup", response_model=LookupResponse)
async def lookup(req: LookupRequest):
    """Run hybrid vector+graph lookup for a natural language query."""
    try:
        out = PIPE.hybrid_lookup(req.query, top_k=req.top_k)
        return LookupResponse(query=req.query, hits=out["vector_hits"], graph_stats=out["graph_stats"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    stats = PIPE.graph.stats() if PIPE else {"nodes": 0, "edges": 0}
    return {"status": "ok", "docs": len(list(DATA_DIR.glob("*.*"))) if DATA_DIR.exists() else 0, "stats": stats}


@app.get("/")
async def root():
    return {"message": "Swarm Intelligence GraphRAG API", "docs": "/docs", "health": "/health"}


if __name__ == "__main__":
    print("Starting Swarm Intelligence GraphRAG API server...")
    print(f"  API docs: http://localhost:8000/docs")
    print(f"  Health:   http://localhost:8000/health")
    uvicorn.run(app, host="127.0.0.1", port=8000)
