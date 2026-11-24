"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { SwarmResult } from "../lib/types";

interface SwarmEvent { stage: string; event?: any; result?: SwarmResult }

function resolveWebSocketUrl() {
  const configured = process.env.NEXT_PUBLIC_WS_URL;
  if (configured) return configured;

  if (typeof window === "undefined") return "ws://localhost:8000/ws/swarm";

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.hostname || "localhost";
  return `${protocol}://${host}:8000/ws/swarm`;
}

function resolveApiBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_API_URL;
  if (configured) return configured.replace(/\/$/, "");

  if (typeof window === "undefined") return "http://localhost:8000";

  return window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : window.location.origin;
}

export function useSwarmSocket(url = resolveWebSocketUrl()) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [stage, setStage] = useState<string>("idle");
  const [trail, setTrail] = useState<string[]>([]);
  const [result, setResult] = useState<SwarmResult | null>(null);
  const [loading, setLoading] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimeoutRef = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => setConnected(false);
      ws.onerror = () => setConnected(false);
      ws.onmessage = (ev) => {
        try {
          const msg: SwarmEvent = JSON.parse(ev.data);
          if (msg.stage) setStage(msg.stage);
          if (msg.stage === "done" && msg.result) {
            clearTimeoutRef();
            setResult(msg.result);
            setLoading(false);
          } else if (msg.stage === "error") {
            clearTimeoutRef();
            setLoading(false);
          } else if (msg.event) {
            setTrail((t) => [...t.slice(-49), `${msg.event.stage ?? msg.stage}`]);
          } else if (msg.stage && msg.stage !== "done") {
            setTrail((t) => [...t.slice(-49), msg.stage]);
          }
        } catch { /* ignore */ }
      };
    } catch { setConnected(false); }
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeoutRef();
      wsRef.current?.close();
    };
  }, [connect, clearTimeoutRef]);

  const ask = useCallback(async (query: string) => {
    const sessionId = `session-${Date.now()}`;
    setLoading(true); setResult(null); setTrail([]); setStage("started");
    clearTimeoutRef();

    // WebSocket path
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ query, session_id: sessionId }));
      // Fallback to HTTP if WebSocket doesn't respond within 10s
      timeoutRef.current = setTimeout(() => {
        timeoutRef.current = null;
        performHttpAsk(query, sessionId);
      }, 10000);
      return;
    }

    // HTTP fallback path
    await performHttpAsk(query, sessionId);
  }, []);

  const performHttpAsk = useCallback(async (query: string, sessionId: string) => {
    try {
      const apiBase = resolveApiBaseUrl();
      const endpoint = apiBase.endsWith("/api") ? `${apiBase}/v1/rag-chat` : `${apiBase}/api/v1/rag-chat`;
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, session_id: sessionId }),
      });
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      const data = await res.json();
      setResult({
        query_id: data.query_id ?? "",
        seeds: data.seeds ?? [],
        validated: data.validated ?? [],
        metrics: data.swarm_metrics ?? data.metrics ?? { latency_s: 0, visited: 0, pruned: 0, candidates: 0, validated: 0, llm_calls: 0 },
        answer: data.answer,
        used_gpt: data.used_gpt,
        gpt_available: data.gpt_available,
      });
      setStage("done");
    } catch (e) {
      setStage("error");
    } finally {
      setLoading(false);
    }
  }, []);

  return { connected, stage, trail, result, loading, ask };
}
