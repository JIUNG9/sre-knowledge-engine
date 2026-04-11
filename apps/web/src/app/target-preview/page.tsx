"use client";

import { useState } from "react";
import {
  Target, Clock, Shield, DollarSign, TrendingUp, TrendingDown,
  Settings2, ChevronDown, Check, AlertTriangle, Activity,
  Pencil, Save, X,
} from "lucide-react";

const t = {
  bg: "#1E1E2A", card: "#252535", sidebar: "#1A1A26", surface: "#2A2A3A",
  text: "#E8E8ED", muted: "#9090A0", accent: "#00FF88", border: "rgba(255,255,255,0.10)",
};

type LayoutKey = "A" | "B";

/* ================================================================
   OPTION A: Inline editable cards — click to edit targets
   ================================================================ */
function OptionA() {
  const [editing, setEditing] = useState<string | null>(null);

  const targets = [
    { id: "slo", label: "SLO Target", target: "99.9%", actual: "99.85%", delta: "-0.05%", meeting: false, icon: Target, color: "#FF6B6B" },
    { id: "mttr", label: "MTTR Target", target: "30 min", actual: "42 min", delta: "+12 min", meeting: false, icon: Clock, color: "#FFB020" },
    { id: "sla", label: "SLA Commitment", target: "99.5%", actual: "99.91%", delta: "+0.41%", meeting: true, icon: Shield, color: t.accent },
    { id: "budget", label: "Error Budget", target: "43.2 min", actual: "18.5 min used", delta: "57% remaining", meeting: true, icon: Activity, color: t.accent },
    { id: "cost", label: "Cost Budget", target: "$15,000/mo", actual: "$12,450", delta: "$2,550 under", meeting: true, icon: DollarSign, color: t.accent },
  ];

  return (
    <div className="rounded-xl overflow-hidden border" style={{ borderColor: t.border, background: t.bg }}>
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: t.border }}>
        <div className="flex items-center gap-3">
          <Target size={22} style={{ color: t.accent }} />
          <span style={{ color: t.text, fontSize: 20, fontWeight: 700 }}>Team Targets</span>
          <span className="rounded-lg px-3 py-1" style={{ background: t.surface, color: t.muted, fontSize: 13 }}>
            nexus account
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span style={{ color: t.muted, fontSize: 13 }}>Click any target to edit</span>
          <div className="rounded-lg px-4 py-2 cursor-pointer flex items-center gap-2" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
            <Settings2 size={16} style={{ color: t.muted }} />
            <span style={{ color: t.text, fontSize: 14 }}>Configure All</span>
          </div>
        </div>
      </div>

      {/* Target cards — inline editable */}
      <div className="grid grid-cols-5 gap-0 divide-x" style={{ borderColor: t.border }}>
        {targets.map((item) => (
          <div
            key={item.id}
            className="p-5 cursor-pointer transition-colors hover:bg-white/[0.02] relative"
            style={{ borderColor: t.border }}
            onClick={() => setEditing(editing === item.id ? null : item.id)}
          >
            {/* Edit indicator */}
            <Pencil size={12} className="absolute top-3 right-3" style={{ color: `${t.muted}50` }} />

            <div className="flex items-center gap-2 mb-3">
              <item.icon size={18} style={{ color: item.meeting ? t.accent : item.color }} />
              <span style={{ color: t.muted, fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>
                {item.label}
              </span>
            </div>

            {/* Target line */}
            <div className="flex items-center gap-2 mb-1">
              <span style={{ color: t.muted, fontSize: 12 }}>Target:</span>
              {editing === item.id ? (
                <div className="flex items-center gap-1">
                  <input
                    defaultValue={item.target}
                    className="rounded border px-2 py-0.5 w-24 text-sm font-bold"
                    style={{ background: t.surface, borderColor: t.accent, color: t.text, fontFamily: "JetBrains Mono" }}
                    onClick={(e) => e.stopPropagation()}
                  />
                  <button className="rounded p-0.5" style={{ background: t.accent }} onClick={(e) => { e.stopPropagation(); setEditing(null); }}>
                    <Check size={12} style={{ color: t.sidebar }} />
                  </button>
                </div>
              ) : (
                <span style={{ color: t.text, fontSize: 14, fontWeight: 700, fontFamily: "JetBrains Mono" }}>{item.target}</span>
              )}
            </div>

            {/* Actual line */}
            <div className="flex items-center gap-2 mb-2">
              <span style={{ color: t.muted, fontSize: 12 }}>Actual:</span>
              <span style={{ color: t.text, fontSize: 20, fontWeight: 700, fontFamily: "JetBrains Mono" }}>{item.actual}</span>
            </div>

            {/* Delta */}
            <div className="flex items-center gap-1.5">
              {item.meeting ? (
                <TrendingUp size={14} style={{ color: t.accent }} />
              ) : (
                <TrendingDown size={14} style={{ color: item.color }} />
              )}
              <span style={{ color: item.meeting ? t.accent : item.color, fontSize: 13, fontWeight: 600 }}>
                {item.delta}
              </span>
            </div>

            {/* Progress bar */}
            <div className="mt-3 h-2 rounded-full overflow-hidden" style={{ background: t.surface }}>
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: item.meeting ? "85%" : "65%",
                  background: item.meeting ? t.accent : item.color,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ================================================================
   OPTION B: Separate config panel — targets + configuration side by side
   ================================================================ */
function OptionB() {
  const [configOpen, setConfigOpen] = useState(true);

  const targets = [
    { id: "slo", label: "SLO", target: 99.9, actual: 99.85, unit: "%", meeting: false },
    { id: "mttr", label: "MTTR", target: 30, actual: 42, unit: "min", meeting: false },
    { id: "sla", label: "SLA", target: 99.5, actual: 99.91, unit: "%", meeting: true },
    { id: "budget_err", label: "Error Budget", target: 43.2, actual: 18.5, unit: "min used", meeting: true },
    { id: "budget_cost", label: "Cost Budget", target: 15000, actual: 12450, unit: "$/mo", meeting: true },
  ];

  return (
    <div className="rounded-xl overflow-hidden border" style={{ borderColor: t.border, background: t.bg }}>
      <div className="flex">
        {/* Left: Target overview — large visual cards */}
        <div className="flex-1 p-6">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <Target size={22} style={{ color: t.accent }} />
              <span style={{ color: t.text, fontSize: 20, fontWeight: 700 }}>Team Targets vs Actual</span>
            </div>
            <button
              onClick={() => setConfigOpen(!configOpen)}
              className="rounded-lg px-4 py-2 flex items-center gap-2 cursor-pointer transition-colors"
              style={{ background: configOpen ? t.accent : t.surface, color: configOpen ? t.sidebar : t.text, fontSize: 14, fontWeight: 600 }}
            >
              <Settings2 size={16} />
              {configOpen ? "Hide Config" : "Configure Targets"}
            </button>
          </div>

          {/* Large target cards — 2x2 + 1 */}
          <div className="grid grid-cols-3 gap-4">
            {targets.map((item) => {
              const pct = item.id === "budget_err"
                ? (item.actual / item.target) * 100
                : item.id === "budget_cost"
                  ? (item.actual / item.target) * 100
                  : item.id === "mttr"
                    ? Math.min((item.target / item.actual) * 100, 100)
                    : (item.actual / item.target) * 100;

              return (
                <div key={item.id} className="rounded-xl p-5" style={{ background: t.card, border: `1px solid ${t.border}` }}>
                  <div className="flex items-center justify-between mb-3">
                    <span style={{ color: t.muted, fontSize: 13, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>
                      {item.label}
                    </span>
                    {item.meeting ? (
                      <span className="flex items-center gap-1 rounded-full px-2.5 py-1" style={{ background: `${t.accent}15`, color: t.accent, fontSize: 12, fontWeight: 600 }}>
                        <Check size={12} /> Meeting
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 rounded-full px-2.5 py-1" style={{ background: "rgba(255,107,107,0.1)", color: "#FF6B6B", fontSize: 12, fontWeight: 600 }}>
                        <AlertTriangle size={12} /> Behind
                      </span>
                    )}
                  </div>

                  <div className="flex items-baseline gap-2 mb-1">
                    <span style={{ color: t.text, fontSize: 32, fontWeight: 700, fontFamily: "JetBrains Mono" }}>
                      {item.id === "budget_cost" ? `$${(item.actual / 1000).toFixed(1)}K` : item.actual}
                    </span>
                    <span style={{ color: t.muted, fontSize: 14 }}>{item.unit}</span>
                  </div>

                  <div className="flex items-center gap-2 mb-3">
                    <span style={{ color: t.muted, fontSize: 13 }}>
                      Target: {item.id === "budget_cost" ? `$${(item.target / 1000).toFixed(0)}K` : item.target} {item.unit}
                    </span>
                  </div>

                  {/* Progress */}
                  <div className="h-3 rounded-full overflow-hidden" style={{ background: t.surface }}>
                    <div className="h-full rounded-full" style={{
                      width: `${Math.min(pct, 100)}%`,
                      background: item.meeting ? t.accent : pct > 90 ? "#FFB020" : "#FF6B6B",
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Config panel (toggleable) */}
        {configOpen && (
          <div className="w-80 border-l p-5 space-y-4" style={{ borderColor: t.border, background: t.sidebar }}>
            <div className="flex items-center justify-between">
              <span style={{ color: t.text, fontSize: 16, fontWeight: 700 }}>Configure Targets</span>
              <button onClick={() => setConfigOpen(false)}>
                <X size={18} style={{ color: t.muted }} />
              </button>
            </div>

            {/* Account selector */}
            <div>
              <label style={{ color: t.muted, fontSize: 12, fontWeight: 600, textTransform: "uppercase" }}>Account</label>
              <div className="mt-1 flex items-center gap-2 rounded-lg px-3 py-2.5" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
                <span style={{ color: t.text, fontSize: 14 }}>nexus (hub)</span>
                <ChevronDown size={14} style={{ color: t.muted, marginLeft: "auto" }} />
              </div>
            </div>

            {/* Target inputs */}
            {[
              { label: "SLO Target (%)", value: "99.9", placeholder: "e.g., 99.9" },
              { label: "MTTR Target (min)", value: "30", placeholder: "e.g., 30" },
              { label: "SLA Commitment (%)", value: "99.5", placeholder: "e.g., 99.5" },
              { label: "Error Budget (min/mo)", value: "43.2", placeholder: "e.g., 43.2" },
              { label: "Cost Budget ($/mo)", value: "15000", placeholder: "e.g., 15000" },
            ].map((field) => (
              <div key={field.label}>
                <label style={{ color: t.muted, fontSize: 12, fontWeight: 600, textTransform: "uppercase" }}>{field.label}</label>
                <input
                  defaultValue={field.value}
                  placeholder={field.placeholder}
                  className="mt-1 w-full rounded-lg border px-3 py-2.5 text-sm font-mono font-bold"
                  style={{ background: t.surface, borderColor: t.border, color: t.text }}
                />
              </div>
            ))}

            <button className="w-full rounded-lg py-3 flex items-center justify-center gap-2 font-semibold" style={{ background: t.accent, color: t.sidebar, fontSize: 14 }}>
              <Save size={16} />
              Save Targets
            </button>

            <p style={{ color: t.muted, fontSize: 12, lineHeight: 1.5 }}>
              Targets are per-account. Switch account above to set different targets for each.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function TargetPreviewPage() {
  const [selected, setSelected] = useState<LayoutKey | null>(null);

  const options: { key: LayoutKey; name: string; desc: string; component: React.ReactNode }[] = [
    {
      key: "A",
      name: "Option A: Inline Editable",
      desc: "Click any target card to edit in-place. Quick and minimal. 5 targets in one row.",
      component: <OptionA />,
    },
    {
      key: "B",
      name: "Option B: Side Config Panel",
      desc: "Large visual cards + slide-out config panel on the right. Per-account target setting. More spacious.",
      component: <OptionB />,
    },
  ];

  return (
    <div className="min-h-screen p-8" style={{ background: "#0E0E16" }}>
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-8">
          <h1 style={{ color: t.text, fontFamily: "JetBrains Mono", fontSize: 28, fontWeight: 700 }}>
            Target Configuration Preview
          </h1>
          <p style={{ color: t.muted, fontSize: 15, marginTop: 6 }}>
            Set team targets for SLO, MTTR, SLA, Error Budget, and Cost Budget — per account.
          </p>
        </div>

        <div className="space-y-10">
          {options.map((opt) => (
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
      </div>
    </div>
  );
}
