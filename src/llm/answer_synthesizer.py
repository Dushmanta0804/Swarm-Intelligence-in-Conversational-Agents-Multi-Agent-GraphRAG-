"""Answer Synthesizer — combines Swarm Intelligence evidence (graph paths +
vector chunks) with GPT to produce grounded, cited RAG answers."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import SETTINGS
from src.llm.gpt_agent import GPTAgent, GPTConfig


@dataclass
class SynthesizedAnswer:
    answer: str
    evidence_chunks: List[str] = field(default_factory=list)
    graph_paths: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    used_gpt: bool = False
    gpt_available: bool = False
    fallback_reason: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class AnswerSynthesizer:
    """Builds RAG answers from swarm output using GPT."""

    def __init__(
        self,
        gpt_agent: Optional[GPTAgent] = None,
        max_evidence_chars: int = 3500,
        max_paths: int = 6,
    ):
        self.gpt = gpt_agent or GPTAgent()
        self.max_evidence_chars = max_evidence_chars
        self.max_paths = max_paths

    # ---- evidence context building ----
    def _format_swarm_evidence(
        self,
        query: str,
        swarm_output: Dict[str, Any],
    ) -> str:
        """Compress swarm output into a compact evidence block for the LLM."""
        parts: List[str] = []
        parts.append(f"USER QUESTION: {query}")
        parts.append("\n--- SWARM EVIDENCE (knowledge graph + vector retrieval) ---")

        validated = swarm_output.get("validated", []) or []
        candidates = swarm_output.get("candidates", []) or []
        seeds = swarm_output.get("seeds", []) or []
        metrics = swarm_output.get("metrics", {})

        if validated:
            parts.append(f"\nValidated reasoning paths ({len(validated)}):")
            for i, p in enumerate(validated[: self.max_paths], 1):
                names = p.get("node_names", [])
                edges = p.get("edges", [])
                score = p.get("score", 0)
                hops = p.get("hops", 0)
                chain = " -> ".join(names)
                parts.append(f"  Path {i} (score={score}, hops={hops}): {chain}")
                for ec in p.get("evidence_chunks", []) or []:
                    if ec:
                        parts.append(f"    evidence_chunk: {ec}")

        if not validated and candidates:
            parts.append(f"\nCandidate paths ({len(candidates)}):")
            for i, p in enumerate(candidates[: self.max_paths], 1):
                names = p.get("node_names", [])
                score = p.get("score", 0)
                parts.append(f"  Candidate {i} (score={score}): {' -> '.join(names)}")

        if seeds:
            parts.append(f"\nAnchor/seed nodes: {', '.join(s.get('name', '') for s in seeds[:5])}")

        parts.append(
            f"\nSwarm metrics: visited={metrics.get('visited', 0)}, "
            f"pruned={metrics.get('pruned', 0)}, "
            f"validated={metrics.get('validated', 0)}, "
            f"latency={metrics.get('latency_s', 0)}s"
        )

        vector_hits = swarm_output.get("_vector_hits", [])
        if vector_hits:
            parts.append(f"\nTop vector-retrieved chunks:")
            for hit in vector_hits[:3]:
                if isinstance(hit, dict):
                    score = hit.get("score", 0)
                    text = hit.get("text", "")
                else:
                    # Legacy tuple format: (Chunk, score)
                    chunk, score = hit
                    text = getattr(chunk, "text", str(chunk))
                    score = float(score)
                parts.append(f"  [score={score:.3f}] {text[:300]}")

        evidence = "\n".join(parts)
        if len(evidence) > self.max_evidence_chars:
            evidence = evidence[: self.max_evidence_chars] + "\n...[truncated]..."
        return evidence

    # ---- main synthesis ----
    def synthesize(
        self,
        query: str,
        swarm_output: Dict[str, Any],
        force_gpt: bool = False,
    ) -> SynthesizedAnswer:
        """Produce a grounded answer. Uses GPT when available; otherwise falls
        back to an evidence-summary answer."""
        evidence = self._format_swarm_evidence(query, swarm_output)

        sources: List[Dict[str, Any]] = []
        validated = swarm_output.get("validated", []) or []
        for p in validated[: self.max_paths]:
            sources.append({
                "type": "graph_path",
                "score": p.get("score", 0),
                "hops": p.get("hops", 0),
                "nodes": p.get("node_names", []),
                "edges": p.get("edges", []),
                "evidence_chunks": p.get("evidence_chunks", []) or [],
            })

        result = SynthesizedAnswer(
            answer="",
            graph_paths=sources,
            used_gpt=False,
            gpt_available=self.gpt.available,
        )

        if self.gpt.available:
            system_prompt = SETTINGS.rag_system_prompt
            user_prompt = (
                f"{evidence}\n\n"
                "INSTRUCTION: First use relevant graph and document evidence above, "
                "citing it with [n] references when possible. If that evidence is "
                "missing or insufficient, still answer the question using your general "
                "knowledge, and clearly label that portion as general knowledge rather "
                "than evidence from the user's data. If uncertain, say so. Be concise "
                "and accurate."
            )
            try:
                answer = self.gpt.complete(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                )
                if answer:
                    result.answer = answer.strip()
                    result.used_gpt = True
                    result.metrics["synthesis_mode"] = "gpt_rag"
                    result.metrics["evidence_chars"] = len(evidence)
                    return result
            except Exception as e:  # noqa: BLE001
                result.fallback_reason = f"gpt_error: {e}"

        result.answer = self._fallback_answer(query, swarm_output, evidence)
        result.used_gpt = False
        result.metrics["synthesis_mode"] = "evidence_summary_fallback"
        result.metrics["evidence_chars"] = len(evidence)
        return result

    # ---- fallback ----
    def _fallback_answer(
        self,
        query: str,
        swarm_output: Dict[str, Any],
        evidence: str,
    ) -> str:
        """Deterministic answer when GPT is unavailable."""
        validated = swarm_output.get("validated", []) or []
        candidates = swarm_output.get("candidates", []) or []
        seeds = swarm_output.get("seeds", []) or []

        lines: List[str] = []
        lines.append("Swarm RAG answer (no GPT key configured — evidence summary):")
        lines.append(f"Question: {query}")

        if validated:
            lines.append("\nReasoning paths found by the swarm:")
            for i, p in enumerate(validated[:5], 1):
                names = p.get("node_names", [])
                edges = p.get("edges", [])
                chain = " -> ".join(names)
                rel = " | ".join(edges) if edges else ""
                lines.append(f"  {i}. {chain}" + (f"   [{rel}]" if rel else ""))
        elif candidates:
            lines.append("\nCandidate paths (not fully validated):")
            for i, p in enumerate(candidates[:5], 1):
                lines.append(f"  {i}. {' -> '.join(p.get('node_names', []))}")
        else:
            lines.append("\nNo graph paths were traced for this question.")

        if seeds:
            lines.append(f"\nAnchor nodes: {', '.join(s.get('name', '') for s in seeds[:5])}")

        metrics = swarm_output.get("metrics", {})
        lines.append(
            f"\nSwarm stats: {metrics.get('validated', 0)} validated paths, "
            f"{metrics.get('visited', 0)} nodes visited, "
            f"{metrics.get('latency_s', 0)}s latency."
        )
        lines.append(
            "\nNote: Configure OPENAI_API_KEY to get GPT-generated grounded answers "
            "with citations instead of this evidence summary."
        )
        return "\n".join(lines)