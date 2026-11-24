"use client";
import { motion } from "framer-motion";
import { ChevronDown, Quote } from "lucide-react";
import { useState } from "react";
import type { ChatMessage } from "../../lib/types";

/** Renders assistant text with [n] inline citations that focus graph nodes on hover. */
function CitedText({ text, names, onFocus }: { text: string; names: string[]; onFocus: (n: string | null) => void }) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <span>
      {parts.map((p, i) => {
        const m = p.match(/\[(\d+)\]/);
        if (m) {
          const idx = parseInt(m[1], 10) - 1;
          const name = names[idx];
          if (!name) return <span key={i}>{p}</span>;
          return (
            <button
              key={i}
              onMouseEnter={() => onFocus(name)}
              onMouseLeave={() => onFocus(null)}
              onClick={() => onFocus(name)}
              title={name}
              className="mx-0.5 inline-flex items-center gap-0.5 rounded-md bg-emerald-400/10 border border-emerald-400/40 px-1.5 py-0.5 text-[11px] text-emerald-200 hover:bg-emerald-400/20 transition-colors"
            >
              <Quote className="w-2.5 h-2.5" />{m[1]}
            </button>
          );
        }
        return <span key={i}>{p}</span>;
      })}
    </span>
  );
}

export function MessageList({ messages, onFocusNode }: { messages: ChatMessage[]; onFocusNode: (n: string | null) => void }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  return (
    <div className="flex flex-col gap-3 overflow-y-auto scroll-slim pr-1">
      {messages.map((m, idx) => (
        <motion.div
          key={m.id}
          initial={{ y: 12, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.25, ease: "easeOut", delay: Math.min(idx * 0.03, 0.3) }}
          className={m.role === "user" ? "self-end max-w-[85%]" : "self-start max-w-[95%] w-full"}
        >
          <div
            className={
              m.role === "user"
                ? "rounded-2xl rounded-br-md bg-cyan-400/10 border border-cyan-400/30 px-4 py-2.5 text-sm"
                : "glass-card text-sm leading-relaxed"
            }
          >
            {m.role === "assistant" && m.result ? (
              <>
                <CitedText text={m.text} names={m.result.validated.flatMap((p) => p.node_names)} onFocus={onFocusNode} />
                {m.thinking && m.thinking.length > 0 && (
                  <div className="mt-2 border-t border-white/10 pt-2">
                    <button
                      onClick={() => setOpen((o) => ({ ...o, [m.id]: !o[m.id] }))}
                      className="flex items-center gap-1 text-xs text-slate-400 hover:text-cyan-300 transition-colors"
                    >
                      <ChevronDown className={`w-3.5 h-3.5 transition-transform ${open[m.id] ? "rotate-180" : ""}`} />
                      Thought process ({m.thinking.length} steps)
                    </button>
                    {open[m.id] && (
                      <ul className="mt-1.5 space-y-1 text-xs text-slate-400">
                        {m.thinking.map((t, i) => <li key={i} className="flex gap-1.5"><span className="text-violet-300">◆</span>{t}</li>)}
                      </ul>
                    )}
                  </div>
                )}
              </>
            ) : (
              <span className="whitespace-pre-wrap">{m.text}</span>
            )}
          </div>
          {m.role === "assistant" && m.result && (
            <div className="mt-1 flex flex-wrap gap-1.5 text-[11px] text-slate-400">
              <span className="rounded-full bg-white/5 border border-white/10 px-2 py-0.5">⚡ {m.result.metrics.latency_s}s</span>
              <span className="rounded-full bg-white/5 border border-white/10 px-2 py-0.5">🟣 {m.result.metrics.visited} visited</span>
              <span className="rounded-full bg-white/5 border border-white/10 px-2 py-0.5">🔥 {m.result.metrics.pruned} pruned</span>
              <span className="rounded-full bg-emerald-400/10 border border-emerald-400/30 px-2 py-0.5 text-emerald-200">✓ {m.result.metrics.validated} validated</span>
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}
