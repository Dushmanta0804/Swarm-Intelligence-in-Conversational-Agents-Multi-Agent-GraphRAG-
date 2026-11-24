"use client";
import { GlassCard } from "../ui/GlassCard";

const LEGEND = [
  { color: "#00F2FE", label: "Seed node (scout anchor)" },
  { color: "#7F00FF", label: "Traversed (pheromone trail)" },
  { color: "#00F5A0", label: "Evidence (validated)" },
  { color: "#FF416C", label: "Pruned / dead-end" },
];

export function GraphControls({ counts }: { counts: { nodes: number; edges: number } }) {
  return (
    <GlassCard className="absolute top-3 left-3 px-3 py-2 text-xs text-slate-300">
      <div className="flex items-center gap-3">
        <span>{counts.nodes} nodes · {counts.edges} edges</span>
        <span className="flex gap-2">
          {LEGEND.map((l) => (
            <span key={l.label} title={l.label} className="w-2.5 h-2.5 rounded-full" style={{ background: l.color, boxShadow: `0 0 8px ${l.color}` }} />
          ))}
        </span>
      </div>
    </GlassCard>
  );
}
