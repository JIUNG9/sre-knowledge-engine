"use client";

import { useState } from "react";
import {
  Zap, Brain, Sparkles, TrendingUp, DollarSign, AlertTriangle,
  Check, ChevronDown, Gauge, Shield, BarChart3, Settings2,
} from "lucide-react";

const t = {
  bg: "#1E1E2A", card: "#252535", sidebar: "#1A1A26", surface: "#2A2A3A",
  text: "#E8E8ED", muted: "#9090A0", accent: "#00FF88", border: "rgba(255,255,255,0.10)",
};

/* ================================================================
   OPTION A: Mode selector as toggle pills in AI panel header
   + Budget bar + cost per operation preview
   ================================================================ */
function OptionA() {
  const [mode, setMode] = useState<"eco" | "standard" | "deep">("standard");

  const modes = {
    eco: { label: "Eco", icon: Zap, color: "#00BFFF", desc: "Haiku · Fast & cheap", cost: "$0.01", model: "Haiku 4.5", maxTokens: "2K" },
    standard: { label: "Standard", icon: Brain, color: "#00FF88", desc: "Sonnet · Balanced", cost: "$0.08", model: "Sonnet 4.6", maxTokens: "8K" },
    deep: { label: "Deep", icon: Sparkles, color: "#A855F7", desc: "Opus · Thorough", cost: "$0.25", model: "Opus 4.6", maxTokens: "Unlimited" },
  };

  return (
    <div className="rounded-xl overflow-hidden border" style={{ borderColor: t.border, background: t.bg }}>
      {/* Simulated AI Panel */}
      <div className="w-full max-w-lg mx-auto p-6 space-y-5">
        <div className="text-center">
          <h2 style={{ color: t.text, fontSize: 18, fontWeight: 700 }}>AI Assistant — Mode Selector</h2>
          <p style={{ color: t.muted, fontSize: 13, marginTop: 4 }}>Shown in the AI panel header</p>
        </div>

        {/* Mode toggle pills */}
        <div className="flex items-center gap-2 rounded-xl p-1.5" style={{ background: t.surface }}>
          {(Object.entries(modes) as [keyof typeof modes, typeof modes.eco][]).map(([key, m]) => (
            <button
              key={key}
              onClick={() => setMode(key)}
              className="flex-1 flex items-center justify-center gap-2 rounded-lg py-3 px-4 transition-all"
              style={{
                background: mode === key ? t.card : "transparent",
                border: mode === key ? `1px solid ${m.color}40` : "1px solid transparent",
                boxShadow: mode === key ? `0 0 12px ${m.color}20` : "none",
              }}
            >
              <m.icon size={18} style={{ color: mode === key ? m.color : t.muted }} />
              <div className="text-left">
                <div style={{ color: mode === key ? m.color : t.muted, fontSize: 14, fontWeight: 700 }}>{m.label}</div>
                <div style={{ color: t.muted, fontSize: 11 }}>{m.desc}</div>
              </div>
            </button>
          ))}
        </div>

        {/* Active mode details */}
        <div className="rounded-xl p-5" style={{ background: t.card, border: `1px solid ${modes[mode].color}25` }}>
          <div className="flex items-center gap-3 mb-3">
            {(() => { const Icon = modes[mode].icon; return <Icon size={22} style={{ color: modes[mode].color }} />; })()}
            <span style={{ color: t.text, fontSize: 18, fontWeight: 700 }}>{modes[mode].label} Mode</span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div style={{ color: t.muted, fontSize: 11, fontWeight: 600, textTransform: "uppercase" }}>Model</div>
              <div style={{ color: t.text, fontSize: 15, fontWeight: 600, fontFamily: "JetBrains Mono" }}>{modes[mode].model}</div>
            </div>
            <div>
              <div style={{ color: t.muted, fontSize: 11, fontWeight: 600, textTransform: "uppercase" }}>Avg Cost</div>
              <div style={{ color: modes[mode].color, fontSize: 15, fontWeight: 600, fontFamily: "JetBrains Mono" }}>{modes[mode].cost}/query</div>
            </div>
            <div>
              <div style={{ color: t.muted, fontSize: 11, fontWeight: 600, textTransform: "uppercase" }}>Max Output</div>
              <div style={{ color: t.text, fontSize: 15, fontWeight: 600, fontFamily: "JetBrains Mono" }}>{modes[mode].maxTokens}</div>
            </div>
          </div>
        </div>

        {/* Pre-operation cost preview */}
        <div className="rounded-xl p-5" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
          <div style={{ color: t.muted, fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
            Before each AI operation:
          </div>
          <div className="flex items-center justify-between rounded-lg px-4 py-3" style={{ background: t.card, border: `1px solid ${t.border}` }}>
            <div>
              <div style={{ color: t.text, fontSize: 14 }}>Investigate incident INC-042</div>
              <div style={{ color: t.muted, fontSize: 12 }}>~15K tokens · {modes[mode].model}</div>
            </div>
            <div className="flex items-center gap-3">
              <span style={{ color: modes[mode].color, fontSize: 18, fontWeight: 700, fontFamily: "JetBrains Mono" }}>
                ~{modes[mode].cost}
              </span>
              <div className="flex gap-2">
                <button className="rounded-lg px-4 py-2" style={{ background: modes[mode].color, color: t.sidebar, fontSize: 13, fontWeight: 700 }}>Run</button>
                <button className="rounded-lg px-4 py-2" style={{ background: t.surface, color: t.muted, fontSize: 13, border: `1px solid ${t.border}` }}>Cancel</button>
              </div>
            </div>
          </div>
        </div>

        {/* Budget bar */}
        <div className="rounded-xl p-5" style={{ background: t.card, border: `1px solid ${t.border}` }}>
          <div className="flex items-center justify-between mb-3">
            <span style={{ color: t.text, fontSize: 14, fontWeight: 600 }}>Monthly Budget</span>
            <span style={{ color: t.muted, fontSize: 13 }}>$3.20 / $10.00</span>
          </div>
          <div className="h-3 rounded-full overflow-hidden" style={{ background: t.surface }}>
            <div className="h-full rounded-full" style={{ width: "32%", background: t.accent }} />
          </div>
          <div className="flex items-center justify-between mt-2">
            <span style={{ color: t.muted, fontSize: 12 }}>32% used</span>
            <span style={{ color: t.accent, fontSize: 12, fontWeight: 600 }}>$6.80 remaining</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   OPTION B: Mode as part of Settings page — with auto-downgrade
   + detailed cost breakdown dashboard
   ================================================================ */
function OptionB() {
  const [mode, setMode] = useState<"eco" | "standard" | "deep">("standard");

  return (
    <div className="rounded-xl overflow-hidden border" style={{ borderColor: t.border, background: t.bg }}>
      <div className="p-6 space-y-5">
        <div>
          <h2 style={{ color: t.text, fontSize: 20, fontWeight: 700 }}>Settings → AI & Token Management</h2>
          <p style={{ color: t.muted, fontSize: 13, marginTop: 4 }}>Full token management dashboard in Settings</p>
        </div>

        {/* Mode cards — larger, more detail */}
        <div className="grid grid-cols-3 gap-4">
          {[
            {
              key: "eco" as const, label: "Eco", icon: Zap, color: "#00BFFF",
              model: "Haiku 4.5", pricing: "$1 / $5 per 1M",
              features: ["Fast responses (<2s)", "Cached system prompts", "2K max output", "Best for: monitoring, status checks"],
              savings: "10x cheaper than Standard",
            },
            {
              key: "standard" as const, label: "Standard", icon: Brain, color: "#00FF88",
              model: "Sonnet 4.6", pricing: "$3 / $15 per 1M",
              features: ["Balanced speed & quality", "Full tool-use loop", "8K max output", "Best for: investigations, analysis"],
              savings: "Recommended for daily use",
            },
            {
              key: "deep" as const, label: "Deep Analysis", icon: Sparkles, color: "#A855F7",
              model: "Opus 4.6", pricing: "$5 / $25 per 1M",
              features: ["Deepest reasoning", "Unlimited tool calls", "No output limit", "Best for: initial setup, critical incidents"],
              savings: "Use sparingly — 5x Standard cost",
            },
          ].map((m) => (
            <div
              key={m.key}
              onClick={() => setMode(m.key)}
              className="rounded-xl p-5 cursor-pointer transition-all"
              style={{
                background: mode === m.key ? `${m.color}08` : t.card,
                border: mode === m.key ? `2px solid ${m.color}40` : `1px solid ${t.border}`,
                boxShadow: mode === m.key ? `0 0 20px ${m.color}15` : "none",
              }}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <m.icon size={20} style={{ color: m.color }} />
                  <span style={{ color: m.color, fontSize: 16, fontWeight: 700 }}>{m.label}</span>
                </div>
                {mode === m.key && (
                  <div className="flex items-center gap-1 rounded-full px-2.5 py-1" style={{ background: `${m.color}20` }}>
                    <Check size={12} style={{ color: m.color }} />
                    <span style={{ color: m.color, fontSize: 11, fontWeight: 600 }}>Active</span>
                  </div>
                )}
              </div>
              <div style={{ color: t.text, fontSize: 14, fontWeight: 600, fontFamily: "JetBrains Mono", marginBottom: 4 }}>{m.model}</div>
              <div style={{ color: t.muted, fontSize: 12, marginBottom: 12 }}>{m.pricing}</div>
              <ul className="space-y-1.5">
                {m.features.map((f, i) => (
                  <li key={i} style={{ color: t.muted, fontSize: 12 }}>• {f}</li>
                ))}
              </ul>
              <div className="mt-3 rounded-lg px-3 py-2" style={{ background: t.surface }}>
                <span style={{ color: m.color, fontSize: 12, fontWeight: 600 }}>{m.savings}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Auto-downgrade settings */}
        <div className="rounded-xl p-5" style={{ background: t.card, border: `1px solid ${t.border}` }}>
          <h3 style={{ color: t.text, fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Budget Guardrails</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div style={{ color: t.text, fontSize: 14 }}>Monthly budget</div>
                <div style={{ color: t.muted, fontSize: 12 }}>Hard stop when exhausted</div>
              </div>
              <div className="flex items-center gap-2 rounded-lg px-4 py-2" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
                <DollarSign size={14} style={{ color: t.accent }} />
                <span style={{ color: t.text, fontSize: 16, fontWeight: 700, fontFamily: "JetBrains Mono" }}>10.00</span>
                <span style={{ color: t.muted, fontSize: 12 }}>/month</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div style={{ color: t.text, fontSize: 14 }}>Auto-downgrade to Eco at</div>
                <div style={{ color: t.muted, fontSize: 12 }}>Switches to Haiku to preserve budget</div>
              </div>
              <div className="flex items-center gap-2 rounded-lg px-4 py-2" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
                <Gauge size={14} style={{ color: "#FFB020" }} />
                <span style={{ color: t.text, fontSize: 16, fontWeight: 700, fontFamily: "JetBrains Mono" }}>80</span>
                <span style={{ color: t.muted, fontSize: 12 }}>% used</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div style={{ color: t.text, fontSize: 14 }}>Notify when budget reaches</div>
                <div style={{ color: t.muted, fontSize: 12 }}>Slack + in-app notification</div>
              </div>
              <div className="flex items-center gap-3">
                {[50, 80, 100].map(p => (
                  <div key={p} className="rounded-lg px-3 py-1.5" style={{ background: p === 100 ? "#FF444420" : t.surface, border: `1px solid ${p === 100 ? "#FF444440" : t.border}` }}>
                    <span style={{ color: p === 100 ? "#FF4444" : t.text, fontSize: 13, fontWeight: 600 }}>{p}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Rate limit handling */}
        <div className="rounded-xl p-5" style={{ background: "#FF444410", border: "1px solid #FF444425" }}>
          <div className="flex items-center gap-3 mb-2">
            <AlertTriangle size={18} style={{ color: "#FF4444" }} />
            <span style={{ color: t.text, fontSize: 14, fontWeight: 600 }}>When rate-limited or budget exhausted:</span>
          </div>
          <ul className="space-y-1.5 ml-8">
            <li style={{ color: t.muted, fontSize: 13 }}>• Show &ldquo;Token budget exhausted. Resets on May 1st. Increase budget in Settings.&rdquo;</li>
            <li style={{ color: t.muted, fontSize: 13 }}>• Offer to switch to Eco mode (cheaper, may still work)</li>
            <li style={{ color: t.muted, fontSize: 13 }}>• Show countdown to reset</li>
            <li style={{ color: t.muted, fontSize: 13 }}>• All dashboard data still works — only AI features paused</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default function TokenPreviewPage() {
  const [selected, setSelected] = useState<string | null>(null);

  const options = [
    { key: "A", name: "Option A: Mode Toggle in AI Panel", desc: "3-pill toggle (Eco/Standard/Deep) in the AI assistant header. Pre-operation cost shown before each query. Compact budget bar.", component: <OptionA /> },
    { key: "B", name: "Option B: Full Settings Dashboard (Recommended)", desc: "Detailed mode cards in Settings. Budget guardrails with auto-downgrade. Rate limit handling. Per-feature cost breakdown.", component: <OptionB /> },
  ];

  return (
    <div className="min-h-screen p-8" style={{ background: "#0E0E16" }}>
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-8">
          <h1 style={{ color: t.text, fontFamily: "JetBrains Mono", fontSize: 28, fontWeight: 700 }}>
            AI Token Management
          </h1>
          <p style={{ color: t.muted, fontSize: 15, marginTop: 6 }}>
            3 modes: Eco (Haiku, cheap), Standard (Sonnet, balanced), Deep (Opus, thorough)
          </p>
          <p style={{ color: t.muted, fontSize: 13, marginTop: 4 }}>
            Budget guardrails, auto-downgrade, rate limit handling, per-operation cost preview
          </p>
        </div>

        <div className="space-y-10">
          {options.map(opt => (
            <div key={opt.key}>
              <button onClick={() => setSelected(opt.key)} className="w-full text-left" style={{
                outline: selected === opt.key ? `2px solid ${t.accent}` : "2px solid transparent",
                borderRadius: 16, transition: "outline 0.2s",
              }}>
                <div className="flex items-center gap-3 mb-3 px-1">
                  <div className="h-6 w-6 rounded-full border-2 flex items-center justify-center" style={{
                    borderColor: selected === opt.key ? t.accent : "#555",
                    background: selected === opt.key ? t.accent : "transparent",
                  }}>
                    {selected === opt.key && <span style={{ color: t.sidebar, fontSize: 12, fontWeight: 700 }}>✓</span>}
                  </div>
                  <span style={{ color: t.text, fontSize: 18, fontWeight: 600 }}>{opt.name}</span>
                  <span style={{ color: t.muted, fontSize: 14 }}>— {opt.desc}</span>
                </div>
                {opt.component}
              </button>
            </div>
          ))}
        </div>

        <div className="mt-8 p-5 rounded-xl" style={{ background: t.card, border: `1px solid ${t.border}` }}>
          <h3 style={{ color: t.text, fontSize: 16, fontWeight: 600 }}>My recommendation: Both A + B together</h3>
          <ul className="mt-3 space-y-2" style={{ color: t.muted, fontSize: 14 }}>
            <li>• <b style={{ color: t.text }}>Option A (mode toggle)</b> goes in the AI assistant panel header — quick switching while chatting</li>
            <li>• <b style={{ color: t.text }}>Option B (full dashboard)</b> goes in Settings → AI & Tokens — budget management, guardrails, history</li>
            <li>• Both share the same mode state via Zustand store</li>
            <li>• Pre-operation cost confirmation shown regardless of where you trigger AI</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
