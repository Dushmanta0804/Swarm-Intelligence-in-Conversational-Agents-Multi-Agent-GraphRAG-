"""GPT Agent — OpenAI-backed chat/completion client with retry, token budgeting,
and graceful fallback when no API key is configured."""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import SETTINGS


@dataclass
class GPTConfig:
    model: str = SETTINGS.openai_model
    temperature: float = SETTINGS.openai_temperature
    max_tokens: int = SETTINGS.openai_max_tokens
    api_key: str = os.getenv("OPENAI_API_KEY", SETTINGS.openai_api_key)
    base_url: Optional[str] = os.getenv("OPENAI_BASE_URL", None)
    timeout_s: float = 60.0
    max_retries: int = 3


class GPTAgent:
    """Thin wrapper around OpenAI chat completions.

    Features:
    - Lazy client creation (no import-time hard dependency on network)
    - Retry with exponential backoff
    - Token budgeting via tiktoken (when available)
    - Returns None/raises gracefully when no API key is present
    """

    def __init__(self, config: Optional[GPTConfig] = None):
        self.cfg = config or GPTConfig()
        self._client = None
        self._encoder = None
        self._available = bool(self.cfg.api_key)

    # ---- lazy client ----
    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self._available:
            return None
        try:
            from openai import OpenAI
            kwargs: Dict[str, Any] = {"api_key": self.cfg.api_key}
            if self.cfg.base_url:
                kwargs["base_url"] = self.cfg.base_url
            self._client = OpenAI(**kwargs)
        except ImportError:
            print("[gpt_agent] openai package not installed; GPTAgent disabled")
            self._available = False
        except Exception as e:  # noqa: BLE001
            print(f"[gpt_agent] failed to create OpenAI client: {e}")
            self._available = False
        return self._client

    # ---- token helpers ----
    def _encoder_instance(self):
        if self._encoder is not None:
            return self._encoder
        try:
            import tiktoken
            self._encoder = tiktoken.encoding_for_model(self.cfg.model)
        except Exception:
            try:
                import tiktoken
                self._encoder = tiktoken.get_encoding("cl100k_base")
            except Exception:
                self._encoder = None
        return self._encoder

    def count_tokens(self, text: str) -> int:
        enc = self._encoder_instance()
        if enc is None:
            return max(1, len(text) // 4)  # rough fallback
        return len(enc.encode(text))

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        enc = self._encoder_instance()
        if enc is None:
            return text[: max_tokens * 4]
        toks = enc.encode(text)
        if len(toks) <= max_tokens:
            return text
        return enc.decode(toks[:max_tokens])

    # ---- completion ----
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Send a chat completion request. Returns None if GPT is unavailable."""
        if not self._available:
            return None
        client = self._ensure_client()
        if client is None:
            return None

        last_err: Optional[Exception] = None
        for attempt in range(self.cfg.max_retries):
            try:
                resp = client.chat.completions.create(
                    model=model or self.cfg.model,
                    messages=messages,
                    temperature=temperature if temperature is not None else self.cfg.temperature,
                    max_tokens=max_tokens or self.cfg.max_tokens,
                )
                choice = resp.choices[0]
                return choice.message.content or ""
            except Exception as e:  # noqa: BLE001
                last_err = e
                wait = min(2 ** attempt, 8)
                print(f"[gpt_agent] attempt {attempt + 1} failed: {e}; retrying in {wait}s")
                time.sleep(wait)
        print(f"[gpt_agent] all retries failed: {last_err}")
        return None

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """Convenience: single-turn completion with optional system prompt."""
        msgs: List[Dict[str, str]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        return self.chat(msgs, temperature=temperature, max_tokens=max_tokens)

    @property
    def available(self) -> bool:
        return self._available