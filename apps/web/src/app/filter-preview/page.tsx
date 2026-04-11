"use client";

import { useState } from "react";
import {
  Cloud, ChevronDown, DollarSign, Shield, KeyRound, Rocket,
  BarChart3, Check, Filter,
} from "lucide-react";

const t = {
  bg: "#1E1E2A", card: "#252535", sidebar: "#1A1A26", surface: "#2A2A3A",
  text: "#E8E8ED", muted: "#9090A0", accent: "#00FF88", border: "rgba(255,255,255,0.10)",
};

const accounts = [
  { id: "nx", name: "nexus", provider: "AWS", role: "Hub" },
  { id: "shared", name: "shared", provider: "AWS", role: "Spoke" },
  { id: "nw", name: "prod-a", provider: "AWS", role: "Spoke" },
  { id: "dp", name: "prod-b", provider: "AWS", role: "Spoke" },
];

/* ================================================================
   OPTION A: Context Bar below title — full-width, always visible
   "You are viewing data for: [All Accounts ▼]"
   ================================================================ */
function OptionA() {
  return (
    <div className="rounded-xl overflow-hidden border" style={{ borderColor: t.border, background: t.bg }}>
      {/* Page header */}
      <div className="px-8 pt-6 pb-3">
        <div className="flex items-center gap-3">
          <DollarSign size={24} style={{ color: t.accent }} />
          <h1 style={{ color: t.text, fontSize: 22, fontWeight: 700 }}>FinOps Dashboard</h1>
        </div>
      </div>

      {/* Context bar — SERVICE ACCOUNT as full-width row */}
      <div className="mx-6 mb-4 flex items-center gap-4 rounded-xl px-5 py-3" style={{ background: `${t.accent}08`, border: `1px solid ${t.accent}20` }}>
        <Cloud size={20} style={{ color: t.accent }} />
        <span style={{ color: t.muted, fontSize: 13, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>Service Account</span>
        <div className="flex items-center gap-2 rounded-lg px-4 py-2 cursor-pointer" style={{ background: t.card, border: `1px solid ${t.border}` }}>
          <div className="h-2.5 w-2.5 rounded-full bg-green-400" />
          <span style={{ color: t.text, fontSize: 15, fontWeight: 600 }}>All Accounts</span>
          <span style={{ color: t.muted, fontSize: 12 }}>(4 connected)</span>
          <ChevronDown size={16} style={{ color: t.accent }} />
        </div>
        <div className="ml-auto flex items-center gap-2">
          {accounts.map(a => (
            <div key={a.id} className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 cursor-pointer" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
              <div className="h-2 w-2 rounded-full bg-green-400" />
              <span style={{ color: t.muted, fontSize: 12, fontWeight: 500 }}>{a.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 px-6 pb-4">
        {["Overview", "Budgets", "Right-Sizing"].map((tab, i) => (
          <div key={tab} className="rounded-lg px-5 py-2.5 cursor-pointer" style={{
            background: i === 0 ? t.accent : t.surface,
            color: i === 0 ? t.sidebar : t.muted,
            fontSize: 14, fontWeight: i === 0 ? 700 : 500,
          }}>{tab}</div>
        ))}
      </div>

      {/* Mock content */}
      <div className="px-6 pb-6">
        <div className="grid grid-cols-3 gap-4">
          {[{ l: "Monthly Cost", v: "$12,450" }, { l: "Budget Used", v: "78%" }, { l: "Savings", v: "$970" }].map(m => (
            <div key={m.l} className="rounded-xl p-5" style={{ background: t.card, border: `1px solid ${t.border}` }}>
              <div style={{ color: t.muted, fontSize: 13 }}>{m.l}</div>
              <div style={{ color: t.text, fontSize: 32, fontWeight: 700, fontFamily: "JetBrains Mono" }}>{m.v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   OPTION B: Integrated with tabs row — account + tabs on same line
   ================================================================ */
function OptionB() {
  return (
    <div className="rounded-xl overflow-hidden border" style={{ borderColor: t.border, background: t.bg }}>
      {/* Page header */}
      <div className="px-8 pt-6 pb-4">
        <div className="flex items-center gap-3">
          <DollarSign size={24} style={{ color: t.accent }} />
          <h1 style={{ color: t.text, fontSize: 22, fontWeight: 700 }}>FinOps Dashboard</h1>
        </div>
      </div>

      {/* Account + Tabs on same row */}
      <div className="flex items-center justify-between px-6 pb-4">
        {/* Left: Account selector as prominent pill */}
        <div className="flex items-center gap-3 rounded-xl px-4 py-2.5 cursor-pointer" style={{ background: `${t.accent}10`, border: `1px solid ${t.accent}25` }}>
          <Cloud size={18} style={{ color: t.accent }} />
          <div>
            <div style={{ color: t.muted, fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>Account</div>
            <div className="flex items-center gap-1.5">
              <span style={{ color: t.text, fontSize: 14, fontWeight: 600 }}>All Accounts</span>
              <ChevronDown size={14} style={{ color: t.accent }} />
            </div>
          </div>
        </div>

        {/* Right: Tabs */}
        <div className="flex items-center gap-1">
          {["Overview", "Budgets", "Right-Sizing"].map((tab, i) => (
            <div key={tab} className="rounded-lg px-5 py-2.5 cursor-pointer" style={{
              background: i === 0 ? t.accent : t.surface,
              color: i === 0 ? t.sidebar : t.muted,
              fontSize: 14, fontWeight: i === 0 ? 700 : 500,
            }}>{tab}</div>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="px-6 pb-6">
        <div className="grid grid-cols-3 gap-4">
          {[{ l: "Monthly Cost", v: "$12,450" }, { l: "Budget Used", v: "78%" }, { l: "Savings", v: "$970" }].map(m => (
            <div key={m.l} className="rounded-xl p-5" style={{ background: t.card, border: `1px solid ${t.border}` }}>
              <div style={{ color: t.muted, fontSize: 13 }}>{m.l}</div>
              <div style={{ color: t.text, fontSize: 32, fontWeight: 700, fontFamily: "JetBrains Mono" }}>{m.v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   OPTION C: Account as quick-switch chips below title
   Clickable account chips — selected one highlighted
   ================================================================ */
function OptionC() {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="rounded-xl overflow-hidden border" style={{ borderColor: t.border, background: t.bg }}>
      {/* Page header */}
      <div className="px-8 pt-6 pb-2">
        <div className="flex items-center gap-3">
          <DollarSign size={24} style={{ color: t.accent }} />
          <h1 style={{ color: t.text, fontSize: 22, fontWeight: 700 }}>FinOps Dashboard</h1>
        </div>
      </div>

      {/* Account chips — click to filter */}
      <div className="flex items-center gap-2 px-6 pb-4">
        <Filter size={16} style={{ color: t.muted }} />
        <span style={{ color: t.muted, fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>Account:</span>

        <div
          onClick={() => setSelected(null)}
          className="flex items-center gap-2 rounded-lg px-4 py-2 cursor-pointer transition-all"
          style={{
            background: !selected ? t.accent : t.surface,
            color: !selected ? t.sidebar : t.text,
            fontSize: 13, fontWeight: 600,
            border: !selected ? `1px solid ${t.accent}` : `1px solid ${t.border}`,
          }}
        >
          {!selected && <Check size={14} />}
          All
        </div>

        {accounts.map(a => (
          <div
            key={a.id}
            onClick={() => setSelected(a.id === selected ? null : a.id)}
            className="flex items-center gap-2 rounded-lg px-4 py-2 cursor-pointer transition-all"
            style={{
              background: selected === a.id ? t.accent : t.surface,
              color: selected === a.id ? t.sidebar : t.text,
              fontSize: 13, fontWeight: selected === a.id ? 700 : 500,
              border: selected === a.id ? `1px solid ${t.accent}` : `1px solid ${t.border}`,
            }}
          >
            {selected === a.id && <Check size={14} />}
            <span className="rounded px-1.5 py-0.5 text-[10px] font-bold" style={{
              background: selected === a.id ? `${t.sidebar}30` : `${t.accent}15`,
              color: selected === a.id ? t.sidebar : t.accent,
            }}>{a.provider}</span>
            {a.name}
            <span style={{ color: selected === a.id ? `${t.sidebar}80` : t.muted, fontSize: 11 }}>({a.role})</span>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 px-6 pb-4">
        {["Overview", "Budgets", "Right-Sizing"].map((tab, i) => (
          <div key={tab} className="rounded-lg px-5 py-2.5 cursor-pointer" style={{
            background: i === 0 ? t.card : "transparent",
            color: i === 0 ? t.text : t.muted,
            fontSize: 14, fontWeight: i === 0 ? 600 : 400,
            border: i === 0 ? `1px solid ${t.border}` : "1px solid transparent",
          }}>{tab}</div>
        ))}
      </div>

      {/* Content */}
      <div className="px-6 pb-6">
        <div className="grid grid-cols-3 gap-4">
          {[{ l: "Monthly Cost", v: "$12,450" }, { l: "Budget Used", v: "78%" }, { l: "Savings", v: "$970" }].map(m => (
            <div key={m.l} className="rounded-xl p-5" style={{ background: t.card, border: `1px solid ${t.border}` }}>
              <div style={{ color: t.muted, fontSize: 13 }}>{m.l}</div>
              <div style={{ color: t.text, fontSize: 32, fontWeight: 700, fontFamily: "JetBrains Mono" }}>{m.v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function FilterPreviewPage() {
  const [selected, setSelected] = useState<string | null>(null);

  const options = [
    { key: "A", name: "Option A: Context Bar", desc: "Full-width green bar below title showing 'Service Account: All Accounts' + quick access chips for each account", component: <OptionA /> },
    { key: "B", name: "Option B: Account + Tabs Row", desc: "Account selector pill on left, tabs on right — same row. Compact but visible.", component: <OptionB /> },
    { key: "C", name: "Option C: Clickable Account Chips (Recommended)", desc: "Account chips below title — click to filter instantly. Selected chip highlighted green. Most intuitive, like Grafana's label filters.", component: <OptionC /> },
  ];

  return (
    <div className="min-h-screen p-8" style={{ background: "#0E0E16" }}>
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 style={{ color: t.text, fontFamily: "JetBrains Mono", fontSize: 28, fontWeight: 700 }}>
            Service Account Filter Placement
          </h1>
          <p style={{ color: t.muted, fontSize: 15, marginTop: 6 }}>
            Where should the account filter live? Below the title, integrated with tabs, or as clickable chips?
          </p>
          <p style={{ color: t.muted, fontSize: 13, marginTop: 4 }}>
            This applies to: FinOps, Security, IAM Audit, Deployments, SLO, and all other pages.
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
          <h3 style={{ color: t.text, fontSize: 16, fontWeight: 600 }}>My recommendation: Option C</h3>
          <ul className="mt-3 space-y-2" style={{ color: t.muted, fontSize: 14 }}>
            <li>• <b style={{ color: t.text }}>Most discoverable</b> — accounts are visible chips, not hidden in a dropdown</li>
            <li>• <b style={{ color: t.text }}>One-click filtering</b> — no dropdown menu to open, just click the account chip</li>
            <li>• <b style={{ color: t.text }}>Shows all accounts at once</b> — you see nexus, shared, nw, dp without opening anything</li>
            <li>• <b style={{ color: t.text }}>Grafana-style</b> — similar to how Grafana handles label/variable filters at dashboard top</li>
            <li>• Works consistently on ALL pages (FinOps, Security, IAM, Deployments, SLO, etc.)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
