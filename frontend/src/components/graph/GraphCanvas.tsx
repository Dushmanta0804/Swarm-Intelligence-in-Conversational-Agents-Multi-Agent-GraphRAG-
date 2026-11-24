"use client";
import { useEffect, useMemo } from "react";
import ReactFlow, {
  Background, Controls, MiniMap, Node, Edge,
  useNodesState, useEdgesState, useReactFlow, ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphEdgeDatum, GraphNodeDatum } from "../../lib/types";

const KIND_STYLE: Record<string, { glow: string; rim: string }> = {
  seed: { glow: "0 0 18px 2px rgba(0,242,254,0.7)", rim: "#00F2FE" },
  traversed: { glow: "0 0 14px 2px rgba(127,0,255,0.6)", rim: "#7F00FF" },
  evidence: { glow: "0 0 15px 2px rgba(0,245,160,0.6)", rim: "#00F5A0" },
  pruned: { glow: "0 0 10px 1px rgba(255,65,108,0.5)", rim: "#FF416C" },
};

function layout(nodes: GraphNodeDatum[]) {
  // radial layout: seeds center, evidence ring, traversed outer
  return nodes.map((n, i) => {
    const ring = n.kind === "seed" ? 0 : n.kind === "evidence" ? 170 : 300;
    const angle = (2 * Math.PI * i) / Math.max(1, nodes.length);
    return { ...n, x: 400 + ring * Math.cos(angle), y: 300 + ring * Math.sin(angle) };
  });
}

function Canvas({ nodes, edges, focusName }: { nodes: GraphNodeDatum[]; edges: GraphEdgeDatum[]; focusName: string | null }) {
  const [rfNodes, setNodes, onNodesChange] = useNodesState([]);
  const [rfEdges, setEdges, onEdgesChange] = useEdgesState([]);
  const { setCenter, zoomTo } = useReactFlow();

  const positioned = useMemo(() => layout(nodes), [nodes]);

  useEffect(() => {
    setNodes(
      positioned.map((n) => {
        const st = KIND_STYLE[n.kind];
        const focused = focusName && n.label.includes(focusName);
        return {
          id: n.id,
          position: { x: (n as any).x, y: (n as any).y },
          data: { label: n.label },
          style: {
            background: "rgba(15,23,42,0.9)",
            border: `2px solid ${st.rim}`,
            borderRadius: "50%",
            width: focused ? 88 : 64, height: focused ? 88 : 64,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 9, color: "#F8FAFC", textAlign: "center" as const,
            padding: 6, boxShadow: st.glow,
            transition: "all 0.4s ease",
            zIndex: focused ? 10 : 1,
          },
        } as Node;
      })
    );
    setEdges(
      edges.map((e) => ({
        id: e.id, source: e.source, target: e.target, label: e.label,
        animated: e.active,
        className: e.active ? "flow-electric" : undefined,
        style: { stroke: "rgba(79,172,254,0.5)", strokeWidth: 1.5 },
        labelStyle: { fill: "#38BDF8", fontSize: 9 },
      } as Edge))
    );
  }, [positioned, edges]);

  // citation hover -> smooth camera zoom + pan (0.4s per spec)
  useEffect(() => {
    if (!focusName) return;
    const target = positioned.find((n) => n.label.includes(focusName));
    if (target) {
      setCenter((target as any).x + 32, (target as any).y + 32, { zoom: 1.4, duration: 400 });
      const t = setTimeout(() => zoomTo(1.15, { duration: 400 }), 1200);
      return () => clearTimeout(t);
    }
  }, [focusName]);

  if (nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        Ask a question — the swarm&apos;s traversal will light up here.
      </div>
    );
  }
  return (
    <ReactFlow nodes={rfNodes} edges={rfEdges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} fitView proOptions={{ hideAttribution: true }}>
      <Background gap={24} size={1} color="rgba(148,163,184,0.12)" />
      <Controls showInteractive={false} />
      <MiniMap pannable zoomable style={{ background: "rgba(6,8,15,0.8)" }} />
    </ReactFlow>
  );
}

export function GraphCanvas({ nodes, edges, focusName }: { nodes: GraphNodeDatum[]; edges: GraphEdgeDatum[]; focusName: string | null }) {
  return (
    <div className="h-full w-full rounded-2xl overflow-hidden bg-slate-950/50 border border-white/10">
      <ReactFlowProvider>
        <Canvas nodes={nodes} edges={edges} focusName={focusName} />
      </ReactFlowProvider>
    </div>
  );
}
