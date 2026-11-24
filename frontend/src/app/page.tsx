"use client";

import { useEffect, useState } from "react";
import { QuantumScene } from "../components/ui/QuantumScene";
import { ChatContainer } from "../components/chat/ChatContainer";
import { useSwarmSocket } from "../hooks/useSwarmSocket";
import type { ChatMessage, SwarmResult } from "../lib/types";

function buildSummary(result: SwarmResult): string {
  if (result.answer) return result.answer;
  const parts: string[] = [];
  for (const v of result.validated) {
    parts.push(v.node_names.join(" \u2192 "));
    if (v.edges.length) {
      parts.push(`(edge: ${v.edges.join(" \u2192 ")})`);
    }
  }
  return parts.join("\n\n") || "No validated paths.";
}

export default function Page() {
  const triggerCollapse = () => {
    window.dispatchEvent(new Event("quantum-collapse"));
  };

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "sys-1",
      role: "assistant",
      text: "Ask about the knowledge graph or a general question. General GPT answers require OPENAI_API_KEY.",
      ts: Date.now(),
    },
  ]);
  const [focusNode, setFocusNode] = useState<string | null>(null);
  const { result, loading, ask } = useSwarmSocket();

  useEffect(() => {
    if (!result) return;
    setMessages((prev) => [
      ...prev,
      {
        id: `asst-${Date.now()}`,
        role: "assistant",
        text: buildSummary(result),
        result,
        ts: Date.now(),
      },
    ]);
  }, [result]);

  const handleAsk = (q: string) => {
    const userId = `user-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: userId, role: "user", text: q, ts: Date.now() },
    ]);
    ask(q);
  };

  return (
  <>

      <header className="hud-nav glass-chassis">
        <div className="reticle-tl" />
        <div className="reticle-tr" />
        <div className="reticle-bl" />
        <div className="reticle-br" />

        <div className="brand-wrap">
          <div className="brand-glyph" />
          <span className="brand-title">NEXURA // QUANTUM</span>
        </div>

        <nav className="nav-links" aria-label="Navigation">
          <a href="#stage-hero">Bloch Core</a>
          <a href="#stage-strata">Superposition</a>
          <a href="#stage-multihop">Entanglement</a>
          <a href="#stage-docking">Blackboard</a>
        </nav>

        <button className="hud-cta" type="button" onClick={triggerCollapse}>
          Collapse State
        </button>
      </header>

      <main className="scroll-orchestration">
        <section id="stage-hero">
          <div className="interactive-card-wrapper">
            <div className="glass-chassis terminal-box">
              <div className="reticle-tl" />
              <div className="reticle-tr" />
              <div className="reticle-bl" />
              <div className="reticle-br" />

              <div className="quantum-meta">
                <span className="quantum-dot" />
                STATE: |Ψ⟩ = α|0⟩ + β|1⟩ // COHERENCE ACTIVE
              </div>

              <h1 className="hero-heading">Quantum Multi-Agent GraphRAG.</h1>

              <p className="lead-copy">
                Deploy decentralized agent swarms that navigate knowledge graphs as superposed probability fields. Collapse thousands of multi-hop search trajectories into verifiable, deterministic proofs.
              </p>

              <div className="quantum-qubit-states">
                <span className="qubit-chip active">Scout // Bell-Φ+</span>
                <span className="qubit-chip plasma">Tracer // Spin-Up</span>
                <span className="qubit-chip gold">Synthesizer // Locked</span>
              </div>

              <div className="mt-6" />

              <div className="telemetry-grid">
                <div>
                  <div className="metric-caption">Fidelity</div>
                  <div className="metric-data metric-cyan">99.98%</div>
                </div>
                <div>
                  <div className="metric-caption">Superposed Paths</div>
                  <div className="metric-data metric-plasma">256 Hops</div>
                </div>
                <div>
                  <div className="metric-caption">Decoherence</div>
                  <div className="metric-data metric-emerald">&lt; 0.001%</div>
                </div>
              </div>
            </div>
</div>
</section>


        <section
          id="chat"
          style={{ height: "64vh", padding: "1rem", paddingTop: "1.25rem" }}
        >
          <div className="h-full rounded-2xl border border-white/10 bg-gradient-to-b from-black/20 to-black/10 backdrop-blur-xl overflow-hidden">
            <ChatContainer
              messages={messages}
              loading={loading}
              onAsk={handleAsk}
              onFocusNode={setFocusNode}
            />
          </div>
        </section>

        <section id="stage-strata" className="align-right">
          <div className="interactive-card-wrapper">
            <div className="glass-chassis inspector-chassis">
              <div className="reticle-tl" />
              <div className="reticle-tr" />
              <div className="reticle-bl" />
              <div className="reticle-br" />

              <div className="quantum-meta">
                <span
                  className="quantum-dot"
                  style={{ background: "var(--quantum-plasma)", boxShadow: "0 0 10px var(--quantum-plasma)" }}
                />
                STRATA_FLUX // BELL-STATE ENTANGLEMENT
              </div>

              <h2 className="section-heading">Non-Local Agent Coordination.</h2>

              <p className="lead-copy">
                Rather than passing expensive prompt contexts between agents, the swarm shares an entangled blackboard in Redis. When Agent A measures a relationship node, Agent B updates its state vector instantaneously.
              </p>

              <div className="inspector-head">
                <span className="pulse-indicator pulse-plasma" />
                Probability Cloud Traversal
              </div>

              <div className="inspector-body">
                Graph edges are evaluated as continuous quantum amplitudes. Unpromising branches decohere into dark vacuum; winning paths intensify with constructive interference.
              </div>
            </div>
          </div>
        </section>

        <section id="stage-multihop">
          <div className="interactive-card-wrapper">
            <div className="glass-chassis inspector-chassis">
              <div className="reticle-tl" />
              <div className="reticle-tr" />
              <div className="reticle-bl" />
              <div className="reticle-br" />

              <div className="quantum-meta">
                <span
                  className="quantum-dot"
                  style={{ background: "var(--quantum-emerald)", boxShadow: "0 0 10px var(--quantum-emerald)" }}
                />
                WAVEFUNCTION_COLLAPSE // VERIFIED EIGENSTATE
              </div>

              <h2 className="section-heading">Deterministic Multi-Hop Proof.</h2>

              <p className="lead-copy">
                Upon measurement, the probabilistic graph collapses into an exact, verifiable sub-graph topology. Every assertion is mathematically bonded to an immutable property graph ID.
              </p>

              <div className="inspector-head inspector-head-emerald">
                ● Collapsed Knowledge Eigenpath
              </div>

              <div className="inspector-body inspector-mono">
                |Entity_α⟩ &otimes; |Entity_β⟩ &rarr; |Consensus_State: §104b⟩
                <br />
                <span className="measurement-value">Measurement Eigenvalue: λ = 1.000 // Grounded</span>
              </div>
            </div>
          </div>
        </section>

        <section id="stage-docking" className="align-right">
          <div className="interactive-card-wrapper">
            <div className="glass-chassis inspector-chassis">
              <div className="reticle-tl" />
              <div className="reticle-tr" />
              <div className="reticle-bl" />
              <div className="reticle-br" />

              <div className="quantum-meta">
                <span
                  className="quantum-dot"
                  style={{ background: "var(--quantum-gold)", boxShadow: "0 0 10px var(--quantum-gold)" }}
                />
                QUANTUM COMPUTING RUNTIME
              </div>

              <h2 className="section-heading">Connect Your Topology.</h2>

              <p className="lead-copy">
                Seamlessly bridge your Neo4j property graphs and vector databases into the Nexura Quantum runtime. Scale from 8 to 512 parallel swarm agents with zero context latency.
              </p>

              <button className="dispatch-btn full-width" type="button" onClick={triggerCollapse}>
                Initialize Bloch Engine
              </button>
            </div>
          </div>
        </section>
      </main>

      <section id="chat" className="flex flex-col h-[64vh] border-t border-white/10">
        <div className="flex-1 min-h-0 flex flex-col">
          <ChatContainer
            messages={messages}
            loading={loading}
            onAsk={handleAsk}
            onFocusNode={setFocusNode}
          />
        </div>
      </section>

      <div className="telemetry-ticker">
        <div className="quantum-dot" />
        <span>QUANTUM_CORE: ACTIVE</span>
        <span>//</span>
        <span>ENTANGLEMENT_FIDELITY: 99.98%</span>
        <span>//</span>
        <span id="coordDisplay">BLOCH_VECTOR: [0.00, 1.00, 0.00]</span>
      </div>
    </>
  );
}
