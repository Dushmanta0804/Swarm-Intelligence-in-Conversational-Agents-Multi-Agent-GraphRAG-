"use client";
import { motion } from "framer-motion";
import { Bot } from "lucide-react";

const ROLE_COLOR: Record<string, string> = {
  dispatcher: "#4FACFE",
  scout: "#00F2FE",
  tracer: "#7F00FF",
  validator: "#00F5A0",
};

export function AgentStatusBadge({ role, stage }: { role: string; stage: string }) {
  const color = ROLE_COLOR[role] ?? "#94A3B8";
  const active = stage !== "idle" && stage !== "done";
  return (
    <motion.div
      animate={active ? { scale: [1, 1.06, 1] } : {}}
      transition={{ duration: 1.8, repeat: Infinity }}
      className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-slate-200"
      style={{ boxShadow: active ? `0 0 12px ${color}55` : undefined }}
    >
      <Bot className="w-3 h-3" style={{ color }} />
      <span className="capitalize">{role}</span>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: active ? color : "#475569" }} />
    </motion.div>
  );
}
