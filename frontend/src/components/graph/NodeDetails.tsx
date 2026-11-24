"use client";
import { GlassCard } from "../ui/GlassCard";

export function NodeDetails({ focusName }: { focusName: string | null }) {
  if (!focusName) return null;
  return (
    <GlassCard className="absolute bottom-3 left-3 max-w-xs border-emerald-400/30">
      <p className="text-[11px] uppercase tracking-wider text-emerald-300">Focused evidence</p>
      <p className="text-sm text-slate-100 mt-0.5 line-clamp-3">{focusName}</p>
    </GlassCard>
  );
}
