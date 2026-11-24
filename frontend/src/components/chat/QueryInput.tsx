"use client";
import { useState } from "react";
import { SendHorizonal, Loader2 } from "lucide-react";
import { GlassButton } from "../ui/GlassButton";

export function QueryInput({ onAsk, loading }: { onAsk: (q: string) => void; loading: boolean }) {
  const [value, setValue] = useState("Who acquired DeepMind?");
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => { e.preventDefault(); if (value.trim() && !loading) onAsk(value.trim()); }}
    >
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask a multi-hop question…"
        className="flex-1 rounded-xl bg-white/5 border border-white/10 px-4 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-cyan-400/50 focus:shadow-aurora-glow transition-all"
      />
      <GlassButton type="submit" disabled={loading}>
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <SendHorizonal className="w-4 h-4" />}
      </GlassButton>
    </form>
  );
}
