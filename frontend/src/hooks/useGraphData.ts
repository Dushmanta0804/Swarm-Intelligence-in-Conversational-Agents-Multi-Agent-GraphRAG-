"use client";
import { useMemo } from "react";
import type { GraphEdgeDatum, GraphNodeDatum, SwarmResult } from "../lib/types";

/** Converts swarm validated paths + seeds into ReactFlow-ready nodes/edges. */
export function useGraphData(result: SwarmResult | null) {
  return useMemo(() => {
    if (!result) return { nodes: [] as GraphNodeDatum[], edges: [] as GraphEdgeDatum[] };
    const nodeMap = new Map<string, GraphNodeDatum>();
    const seedIds = new Set(result.seeds.map((s) => s.node_id));
    // seeds first
    result.seeds.forEach((s) =>
      nodeMap.set(s.node_id, { id: s.node_id, label: s.name, kind: "seed", score: s.anchor_score })
    );
    const evidenceIds = new Set<string>();
    result.validated.forEach((p) => {
      if (p.nodes.length > 0) evidenceIds.add(p.nodes[p.nodes.length - 1]);
    });
    const edges: GraphEdgeDatum[] = [];
    result.validated.forEach((p, pi) => {
      p.node_names.forEach((name, i) => {
        const id = p.nodes[i] ?? `${pi}-${i}-${name}`;
        if (!nodeMap.has(id)) {
          const kind = evidenceIds.has(id) ? "evidence" : seedIds.has(id) ? "seed" : "traversed";
          nodeMap.set(id, { id, label: name, kind, score: p.score });
        } else if (evidenceIds.has(id)) {
          nodeMap.get(id)!.kind = "evidence";
        }
        if (i > 0) {
          const prev = p.nodes[i - 1] ?? `${pi}-${i - 1}`;
          edges.push({ id: `e-${pi}-${i}`, source: prev, target: id, label: p.edges[i - 1] ?? "RELATED", active: true });
        }
      });
    });
    return { nodes: Array.from(nodeMap.values()), edges };
  }, [result]);
}
