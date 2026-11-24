"""Loaders for PDF / Markdown / TXT / JSON -> Document."""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import List

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.models import Document, make_id


SUPPORTED = {".pdf", ".md", ".markdown", ".txt", ".json"}


def load_file(path: str | Path) -> Document:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _read_pdf(path)
    elif suffix in (".md", ".markdown", ".txt"):
        text = path.read_text(encoding="utf-8", errors="ignore")
    elif suffix == ".json":
        text = _read_json(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix} ({path})")
    doc_id = make_id("doc", str(path.resolve()) + str(len(text)))
    return Document(doc_id=doc_id, source_path=str(path), text=text,
                    metadata={"suffix": suffix, "filename": path.name})


def load_directory(data_dir: str | Path) -> List[Document]:
    data_dir = Path(data_dir)
    docs: List[Document] = []
    if not data_dir.exists():
        return docs
    for f in sorted(data_dir.rglob("*")):
        if f.is_file() and f.suffix.lower() in SUPPORTED:
            try:
                docs.append(load_file(f))
            except Exception as e:
                print(f"[loader] skip {f}: {e}")
    return docs


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        from pypdf import PdfReader  # pypdf package name
    # fallback import
    try:
        reader = PdfReader(str(path))
    except Exception:
        from pypdf import PdfReader as R
        reader = R(str(path))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts)


def _read_json(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    try:
        data = json.loads(raw)
    except Exception:
        return raw
    # flatten json to readable text, keep structure hints
    texts = []
    def walk(o, prefix=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{prefix}{k}: ")
        elif isinstance(o, list):
            for item in o:
                walk(item, prefix)
        else:
            texts.append(f"{prefix}{o}")
    walk(data)
    return "\n".join(texts)


def ensure_sample_docs(data_dir: str | Path) -> List[Path]:
    """Create sample docs so Phase 1 demo runs with zero setup."""
    d = Path(data_dir)
    d.mkdir(parents=True, exist_ok=True)
    samples = {
        "ai_research.md": (
            "# Swarm Intelligence Research\n\n"
            "Alphabet Inc. (also known as Google) published a paper on Path Tracer agents. "
            "Dr. Ada Lovelace leads the Swarm Lab at MIT. "
            "The Swarm Lab collaborates with DeepMind on GraphRAG research.\n\n"
            "Google acquired DeepMind in 2014. DeepMind is located in London. "
            "MIT is located in Cambridge.\n"
        ),
        "fraud_case.json": (
            '{"case": "Shell network", "entities": ['
            '{"name": "Acme Holdings", "owns": "Beacon Ltd"}, '
            '{"name": "Beacon Ltd", "transfers_to": "Cedar Trust"}]}'
        ),
        "notes.txt": (
            "Validator agents resolve conflicting edge assertions. "
            "Scout agents anchor queries to entry nodes. "
            "Microsoft partners with OpenAI on retrieval research."
        ),
    }
    created = []
    for name, content in samples.items():
        p = d / name
        if not p.exists():
            p.write_text(content, encoding="utf-8")
        created.append(p)
    return created
