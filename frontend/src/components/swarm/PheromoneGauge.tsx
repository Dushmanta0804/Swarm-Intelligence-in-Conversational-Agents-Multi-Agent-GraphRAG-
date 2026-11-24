"use client";
import { Flame } from "lucide-react";

export function PheromoneGauge({ pruned, visited }: { pruned: number; visited: number }) {
  const total = Math.max(1, visited + pruned);
  const pct = Math.round((visited / total) * 100);
  return (
    <div className="flex items-center gap-2 text-[11px] text-slate-300">
      <Flame className="w-3.5 h-3.5 text-violet-300" />
      <div className="w-24 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, background: "linear-gradient(90deg,#7F00FF,#00F2FE)" }}
        />
      </div>
      <span>{visited} kept · {pruned} pruned</span>
    </div>
  );
}
