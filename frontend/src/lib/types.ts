export interface Seed { node_id: string; name: string; anchor_score: number; source: string; }
export interface ValidatedPath {
  nodes: string[]; node_names: string[]; edges: string[]; score: number;
  hops: number; evidence_chunks: string[];
}
export interface SwarmResult {
  query_id: string; seeds: Seed[]; validated: ValidatedPath[];
  metrics: { latency_s: number; visited: number; pruned: number; candidates: number; validated: number; llm_calls: number };
  answer?: string; used_gpt?: boolean; gpt_available?: boolean;
}
export interface ChatMessage {
  id: string; role: "user" | "assistant"; text: string; result?: SwarmResult;
  thinking?: string[]; ts: number;
}
export interface GraphNodeDatum { id: string; label: string; kind: "seed" | "traversed" | "evidence" | "pruned"; score?: number; }
export interface GraphEdgeDatum { id: string; source: string; target: string; label: string; active?: boolean; }
