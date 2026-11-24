"""Central configuration for all phases. Phase 1 uses local backends by default."""
import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


@dataclass
class Settings:
    graph_backend: str = os.getenv("GRAPH_BACKEND", "local")  # local | neo4j
    embedding_mode: str = os.getenv("EMBEDDING_MODE", "local")  # local | qdrant | openai
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "swarm_password")
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "swarm_docs")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    data_dir: str = os.getenv("DATA_DIR", "data_docs")
    persist_dir: str = os.getenv("PERSIST_DIR", "storage")
    # ---- Phase 2: swarm engine ----
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    use_redis: bool = os.getenv("USE_REDIS", "false").lower() in ("1", "true", "yes")
    prune_threshold: float = float(os.getenv("PRUNE_THRESHOLD", "0.60"))
    max_hops: int = int(os.getenv("MAX_HOPS", "3"))
    max_workers: int = int(os.getenv("MAX_WORKERS", "8"))
    top_k_scout: int = int(os.getenv("TOP_K_SCOUT", "5"))
    pheromone_decay: float = float(os.getenv("PHEROMONE_DECAY", "0.85"))
    pheromone_deposit: float = float(os.getenv("PHEROMONE_DEPOSIT", "1.0"))
    # ---- Phase 5: stigmergy memory ----
    pheromone_evaporation: float = float(os.getenv("PHEROMONE_EVAPORATION", "0.15"))
    focus_cache_top_k: int = int(os.getenv("FOCUS_CACHE_TOP_K", "10"))
    focus_cache_ttl_s: int = int(os.getenv("FOCUS_CACHE_TTL_S", "1800"))
    # ---- Phase 3: GPT + RAG Agent ----
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    openai_max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "800"))
    rag_system_prompt: str = os.getenv(
        "RAG_SYSTEM_PROMPT",
        "You are a Swarm Intelligence GraphRAG assistant. You can answer TWO types of questions:\n"
        "1) GRAPH/RAG questions: Use the provided knowledge graph evidence and document chunks to answer, citing sources with [n] references.\n"
        "2) GENERAL knowledge questions: If no graph evidence is relevant or available, answer from your own general knowledge.\n"
        "Always clearly distinguish between 'evidence from your data' and 'general knowledge'. Be concise, accurate, and transparent about uncertainty.",
    )


SETTINGS = Settings()
