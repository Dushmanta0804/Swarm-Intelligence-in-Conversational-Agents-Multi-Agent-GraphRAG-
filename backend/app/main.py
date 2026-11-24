"""FastAPI Gateway — chat / ingestion / telemetry + WebSocket (arch §3)."""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
import sys
from typing import Any, Dict
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from config import SETTINGS
from src.ingestion.pipeline import IngestionPipeline
from src.swarm.workflow import SwarmOrchestrator
from src.swarm.session_memory import make_session_memory
from src.llm.gpt_agent import GPTAgent, GPTConfig
from src.llm.answer_synthesizer import AnswerSynthesizer
from src.llm.random_question_agent import RandomQuestionAgent

app = FastAPI(title="Swarm Intelligence GraphRAG", version="0.7.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
PIPE = IngestionPipeline(graph_backend=SETTINGS.graph_backend, embedding_mode="local")
try:
    PIPE.run(SETTINGS.data_dir)
except Exception as e:
    print(f"[gateway] initial ingest skipped: {e}")
SESSION_MEM = make_session_memory()

# ---- Phase 3: GPT + RAG agents (global singletons) ----
GPT_AGENT = GPTAgent()
SYNTHESIZER = AnswerSynthesizer(gpt_agent=GPT_AGENT)
RANDOM_AGENT = RandomQuestionAgent(
    data_dir=SETTINGS.data_dir,
    graph_backend=SETTINGS.graph_backend,
    embedding_mode="local",
    gpt_agent=GPT_AGENT,
    synthesizer=SYNTHESIZER,
    auto_ingest=False,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def homepage():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index), media_type="text/html")
    return {"message": "Swarm Intelligence GraphRAG API — see /docs"}


class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"
    max_hops: int | None = None
    prune_threshold: float | None = None


class RAGChatRequest(BaseModel):
    query: str
    session_id: str = "default"
    force_gpt: bool = False
    max_hops: int | None = None
    prune_threshold: float | None = None


class RandomQuestionRequest(BaseModel):
    question: str | None = None
    session_id: str = "default"


def _orch() -> SwarmOrchestrator:
    return SwarmOrchestrator(PIPE.graph, PIPE.vectors,
                             prune_threshold=SETTINGS.prune_threshold,
                             max_hops=SETTINGS.max_hops,
                             max_workers=SETTINGS.max_workers,
                             top_k_scout=SETTINGS.top_k_scout,
                             session_memory=SESSION_MEM)
def _serialize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a Swarm run result into a JSON-safe dict.
    Handles non-serializable objects like Chunk, SeedNode, etc.
    """
    def _convert(obj):
        if isinstance(obj, dict):
            return {k: _convert(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [_convert(v) for v in obj]
        elif hasattr(obj, "model_dump"):
            return _convert(obj.model_dump())
        elif hasattr(obj, "model_dump_json"):
            import json
            return _convert(json.loads(obj.model_dump_json()))
        elif hasattr(obj, "__dict__"):
            d = {}
            for k, v in obj.__dict__.items():
                if k.startswith("_") or k in ("graph", "vectors", "state"):
                    continue
                d[k] = _convert(v)
            return d
        return obj
    
    return _convert(result.copy())


def _serialize_vector_hits(hits) -> List[Dict[str, Any]]:
    """Convert VectorStore.search() (List[Tuple[Chunk, float]]) to JSON-serializable dicts."""
    out = []
    for chunk, score in hits:
        out.append({
            "chunk_id": getattr(chunk, "chunk_id", str(chunk)),
            "text": getattr(chunk, "text", str(chunk)),
            "doc_id": getattr(chunk, "doc_id", ""),
            "score": round(float(score), 4),
        })
    return out


def _answer_with_swarm(query: str, swarm_out: Dict[str, Any],
                       force_gpt: bool = False) -> Dict[str, Any]:
    try:
        hits = PIPE.vectors.search(query, top_k=3)
        swarm_out["_vector_hits"] = _serialize_vector_hits(hits)
    except Exception:
        swarm_out["_vector_hits"] = []
    synthesized = SYNTHESIZER.synthesize(query, swarm_out, force_gpt=force_gpt)
    return {
        **swarm_out,
        "answer": synthesized.answer,
        "used_gpt": synthesized.used_gpt,
        "gpt_available": synthesized.gpt_available,
        "fallback_reason": synthesized.fallback_reason,
        "sources": synthesized.sources,
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "graph": PIPE.graph.stats(), "vectors": len(PIPE.vectors)}


@app.post("/api/v1/chat")
def chat(req: ChatRequest) -> Dict[str, Any]:
    orch = _orch()
    if req.max_hops:
        orch.max_hops = req.max_hops
    if req.prune_threshold:
        orch.prune_threshold = req.prune_threshold
    return orch.run(req.query, session_id=req.session_id)


@app.post("/api/v1/rag-chat")
def rag_chat(req: RAGChatRequest) -> Dict[str, Any]:
    """Swarm + GPT RAG answer: trace graph paths, then synthesize with GPT."""
    orch = _orch()
    if req.max_hops:
        orch.max_hops = req.max_hops
    if req.prune_threshold:
        orch.prune_threshold = req.prune_threshold
    swarm_out = _answer_with_swarm(
        req.query,
        orch.run(req.query, session_id=req.session_id),
        force_gpt=req.force_gpt,
    )
    return {
        "query": req.query,
        "query_id": swarm_out.get("query_id", ""),
        "answer": swarm_out["answer"],
        "used_gpt": swarm_out["used_gpt"],
        "gpt_available": swarm_out["gpt_available"],
        "fallback_reason": swarm_out["fallback_reason"],
        "sources": swarm_out["sources"],
        "graph_paths": swarm_out["sources"],
        "seeds": swarm_out.get("seeds", []),
        "validated": swarm_out.get("validated", []),
        "candidates": swarm_out.get("candidates", []),
        "swarm_metrics": swarm_out.get("metrics", {}),
        "session_id": req.session_id,
    }


@app.post("/api/v1/random-question")
def random_question(req: RandomQuestionRequest) -> Dict[str, Any]:
    """Answer a specific or random question using Swarm + RAG + GPT."""
    q = req.question
    if not q:
        res = RANDOM_AGENT.ask_random(session_id=req.session_id)
    else:
        res = RANDOM_AGENT.ask(q, session_id=req.session_id)
    return {
        "question": res.question,
        "answer": res.answer,
        "used_rag": res.used_rag,
        "used_gpt": res.used_gpt,
        "gpt_available": res.gpt_available,
        "metrics": res.metrics,
        "swarm_metrics": res.swarm_output.get("metrics", {}),
        "session_id": req.session_id,
    }


@app.get("/api/v1/random-question")
def random_question_get() -> Dict[str, Any]:
    """Answer a random question (GET convenience endpoint)."""
    res = RANDOM_AGENT.ask_random(session_id="random_agent")
    return {
        "question": res.question,
        "answer": res.answer,
        "used_rag": res.used_rag,
        "used_gpt": res.used_gpt,
        "gpt_available": res.gpt_available,
        "metrics": res.metrics,
    }


@app.get("/api/v1/gpt-status")
def gpt_status() -> Dict[str, Any]:
    """Check whether the GPT agent is configured and available."""
    return {
        "gpt_available": GPT_AGENT.available,
        "model": SETTINGS.openai_model,
        "temperature": SETTINGS.openai_temperature,
        "max_tokens": SETTINGS.openai_max_tokens,
        "api_key_configured": bool(SETTINGS.openai_api_key),
    }


@app.post("/api/v1/ingest")
def ingest() -> Dict[str, Any]:
    return PIPE.run(SETTINGS.data_dir)


@app.get("/api/v1/telemetry")
def telemetry() -> Dict[str, Any]:
    return {"graph": PIPE.graph.stats(), "vectors": len(PIPE.vectors),
            "settings": {"max_hops": SETTINGS.max_hops, "max_workers": SETTINGS.max_workers,
                         "prune_threshold": SETTINGS.prune_threshold,
                         "evaporation_rho": SETTINGS.pheromone_evaporation,
                         "focus_cache_ttl_s": SETTINGS.focus_cache_ttl_s},
            "redis": redis_status()}


@app.get("/api/v1/memory/focus")
def focus_lookup(session_id: str = "default", query: str = "") -> Dict[str, Any]:
    """Phase 5 §4: inspect what the dispatcher would anchor to for a follow-up."""
    try:
        hit = SESSION_MEM.lookup_focus(session_id, query)
        return {"session_id": session_id, "query": query, "focus": hit}
    except Exception as e:
        return {"session_id": session_id, "error": str(e)}


@app.delete("/api/v1/memory/focus")
def focus_clear(session_id: str = "default") -> Dict[str, Any]:
    SESSION_MEM.invalidate(session_id)
    return {"session_id": session_id, "cleared": True}


@app.get("/api/v1/memory/redis")
def redis_status() -> Dict[str, Any]:
    """Live Redis blackboard status — local fallback when unreachable."""
    if not SETTINGS.use_redis:
        return {"mode": "local", "use_redis": False,
                "hint": "Set USE_REDIS=true + REDIS_URL to share blackboard across workers"}
    try:
        import redis
        c = redis.Redis.from_url(SETTINGS.redis_url, socket_connect_timeout=2)
        c.ping()
        info = c.info("memory") if hasattr(c, "info") else {}
        return {"mode": "redis", "url": SETTINGS.redis_url, "reachable": True,
                "used_memory_human": info.get("used_memory_human", "?"),
                "keys_swarm": len(c.keys("swarm:*"))}
    except Exception as e:
        return {"mode": "local-fallback", "url": SETTINGS.redis_url,
                "reachable": False, "error": str(e)}


@app.websocket("/ws/swarm")
async def swarm_socket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
                query = msg.get("query", raw)
                session_id = msg.get("session_id", "default")
            except Exception:
                query = raw
                session_id = "default"
            events: asyncio.Queue = asyncio.Queue()
            try:
                loop = asyncio.get_running_loop()
            except DeprecationWarning:
                loop = asyncio.get_event_loop()
            orch = _orch()
            orch.on_event = lambda e: loop.call_soon_threadsafe(events.put_nowait, e)
            import threading
            holder: Dict[str, Any] = {}

            def _run_swarm():
                try:
                    holder["result"] = _answer_with_swarm(
                        query, orch.run(query, session_id=session_id))
                except Exception as e:  # noqa: BLE001
                    holder["error"] = str(e)

            threading.Thread(target=_run_swarm, daemon=True).start()
            await ws.send_json({"stage": "started", "query": query, "session_id": session_id})
            deadline = asyncio.get_event_loop().time() + 30.0  # 30s overall timeout
            while "result" not in holder and "error" not in holder:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    await ws.send_json({"stage": "error", "event": {"stage": "timeout"}})
                    break
                try:
                    ev = await asyncio.wait_for(events.get(), timeout=min(0.25, remaining))
                    await ws.send_json({"stage": ev.get("stage"), "event": ev})
                except asyncio.TimeoutError:
                    continue
            if "error" in holder:
                await ws.send_json({"stage": "error", "event": {"stage": "error", "message": holder["error"]}})
            else:
                while not events.empty():
                    await ws.send_json({"stage": "event", "event": events.get_nowait()})
                # Serialize result for JSON safety (Chunk/SeedNode objects aren't serializable)
                safe_result = _serialize_result(holder["result"])
                await ws.send_json({"stage": "done", "result": safe_result})
                await ws.send_json({"stage": "done", "result": holder["result"]})
    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        try:
            await ws.send_json({"stage": "error", "event": {"stage": "error", "message": str(e)}})
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
