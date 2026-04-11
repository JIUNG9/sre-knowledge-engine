"use client";

import { useState } from "react";
import {
  Shield, Search, BarChart3, DollarSign, AlertTriangle, ShieldCheck,
  KeyRound, Rocket, Phone, BookOpen, Settings, Sparkles, User, Globe,
  ChevronDown, Cloud, Bell, ChevronRight, Users, Activity, Zap,
} from "lucide-react";

const t = {
  bg: "#1E1E2A", card: "#252535", sidebar: "#1A1A26", surface: "#2A2A3A",
  text: "#E8E8ED", muted: "#9090A0", accent: "#00FF88", border: "rgba(255,255,255,0.10)",
};

const navItems = [
  { label: "Log Explorer", icon: Search },
  { label: "SLO Dashboard", icon: BarChart3 },
  { label: "FinOps", icon: DollarSign },
  { label: "Incidents", icon: AlertTriangle },
  { label: "Security", icon: ShieldCheck },
  { label: "IAM Audit", icon: KeyRound },
  { label: "Deployments", icon: Rocket },
  { label: "On-Call", icon: Phone },
  { label: "Services", icon: BookOpen },
];

/* ================================================================
   OPTION 1: Stretched sidebar + top-bar account + floating AI
   - Nav items spread to fill sidebar (larger gaps)
   - Account switcher prominent in top bar with "Service Account" label
   - Language at top-right
   - Floating AI pill bottom-right
   ================================================================ */
function Option1() {
  return (
    <div className="flex h-[600px] overflow-hidden rounded-xl border" style={{ borderColor: t.border, background: t.bg }}>
      <div className="flex w-60 flex-col border-r" style={{ background: t.sidebar, borderColor: t.border }}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl" style={{ background: `${t.accent}15`, border: `1px solid ${t.accent}25` }}>
            <Shield size={24} style={{ color: t.accent }} />
          </div>
          <div>
            <div style={{ color: t.text, fontFamily: "JetBrains Mono", fontSize: 20, fontWeight: 700, letterSpacing: 3 }}>AEGIS</div>
          </div>
        </div>
        <div className="mx-4 h-px" style={{ background: t.border }} />

        {/* Nav items — USE FLEX-1 + justify-between to FILL space */}
        <nav className="flex flex-1 flex-col justify-start gap-1 px-3 py-4">
          {navItems.map((item, i) => {
            const active = i === 1;
            return (
              <div key={item.label} className="flex items-center gap-3 rounded-lg px-4 py-3 cursor-pointer" style={{
                background: active ? `${t.accent}12` : "transparent",
                borderLeft: active ? `3px solid ${t.accent}` : "3px solid transparent",
              }}>
                <item.icon size={20} style={{ color: active ? t.accent : t.muted }} />
                <span style={{ color: active ? t.text : t.muted, fontSize: 15, fontWeight: active ? 600 : 400 }}>{item.label}</span>
              </div>
            );
          })}
        </nav>

        {/* Bottom: Settings — PINNED at bottom */}
        <div className="mx-3 h-px" style={{ background: t.border }} />
        <div className="px-3 py-3">
          <div className="flex items-center gap-3 rounded-lg px-4 py-3 cursor-pointer">
            <Settings size={20} style={{ color: t.muted }} />
            <span style={{ color: t.muted, fontSize: 15 }}>Settings</span>
          </div>
        </div>
        <div className="px-4 pb-3 flex items-center justify-between">
          <span style={{ color: `${t.muted}60`, fontSize: 12, fontFamily: "JetBrains Mono" }}>v2.0.0</span>
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 flex flex-col relative">
        {/* Top bar: Search | Service Account (BIG) | Language + User */}
        <div className="flex items-center border-b px-6 py-3" style={{ borderColor: t.border, height: 56 }}>
          <div className="flex items-center gap-2 rounded-lg px-4 py-2.5 w-72" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
            <Search size={16} style={{ color: t.muted }} />
            <span style={{ color: t.muted, fontSize: 14 }}>Search... ⌘K</span>
          </div>

          {/* Service Account — LARGE and centered */}
          <div className="flex-1 flex justify-center">
            <div className="flex items-center gap-3 rounded-xl px-5 py-2.5 cursor-pointer" style={{ background: t.surface, border: `1px solid ${t.accent}30` }}>
              <Cloud size={18} style={{ color: t.accent }} />
              <div>
                <div style={{ color: `${t.muted}`, fontSize: 11, fontWeight: 500 }}>Service Account</div>
                <div style={{ color: t.text, fontSize: 15, fontWeight: 600 }}>All Accounts (4 connected)</div>
              </div>
              <ChevronDown size={16} style={{ color: t.accent }} />
            </div>
          </div>

          {/* Right: Language + Notifications + User */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 rounded-lg px-3 py-2 cursor-pointer" style={{ background: t.surface }}>
              <Globe size={14} style={{ color: t.accent }} />
              <span style={{ color: t.text, fontSize: 13, fontWeight: 600 }}>EN</span>
              <ChevronDown size={12} style={{ color: t.muted }} />
            </div>
            <div className="relative">
              <Bell size={20} style={{ color: t.muted }} />
              <span className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold" style={{ background: "#FF4444", color: "white" }}>3</span>
            </div>
            <div className="h-9 w-9 rounded-full flex items-center justify-center" style={{ background: t.surface }}>
              <User size={18} style={{ color: t.muted }} />
            </div>
          </div>
        </div>

        {/* Page header + Tabs — ALL VISIBLE, BIGGER */}
        <div className="flex items-center justify-between border-b px-6" style={{ borderColor: t.border, height: 52 }}>
          <div className="flex items-center gap-4">
            <h1 style={{ color: t.text, fontSize: 20, fontWeight: 700 }}>SLO Dashboard</h1>
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5" style={{ color: t.accent, fontSize: 13 }}>● 6 meeting</span>
              <span className="flex items-center gap-1.5" style={{ color: "#FFB020", fontSize: 13 }}>▲ 2 at risk</span>
              <span className="flex items-center gap-1.5" style={{ color: "#FF4444", fontSize: 13 }}>● 2 breaching</span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {["All", "Weekly", "Monthly", "Quarterly", "Annually"].map((tab, i) => (
              <div key={tab} className="rounded-lg px-5 py-2.5 cursor-pointer" style={{
                background: i === 0 ? t.accent : "transparent",
                color: i === 0 ? t.sidebar : t.muted,
                fontSize: 14,
                fontWeight: i === 0 ? 700 : 500,
              }}>{tab}</div>
            ))}
            <div className="ml-3 rounded-lg px-5 py-2.5 cursor-pointer" style={{ background: t.accent, color: t.sidebar, fontSize: 14, fontWeight: 700 }}>
              + Create SLO
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-6">
          <div className="grid grid-cols-3 gap-5">
            {[
              { label: "SLOs Meeting Target", value: "6/10", color: t.accent },
              { label: "Avg Error Budget", value: "42%", color: "#00BFFF" },
              { label: "Worst Burn Rate", value: "3.2x", color: "#FF4444" },
            ].map(m => (
              <div key={m.label} className="rounded-xl p-6" style={{ background: t.card, border: `1px solid ${t.border}` }}>
                <div style={{ color: t.muted, fontSize: 14 }}>{m.label}</div>
                <div style={{ color: m.color, fontSize: 36, fontWeight: 700, fontFamily: "JetBrains Mono", marginTop: 8 }}>{m.value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Floating AI — large pill */}
        <div className="absolute bottom-6 right-6 flex items-center gap-3 rounded-2xl px-6 py-4 cursor-pointer" style={{ background: t.accent, boxShadow: `0 4px 30px ${t.accent}50` }}>
          <Sparkles size={22} style={{ color: t.sidebar }} />
          <span style={{ color: t.sidebar, fontSize: 16, fontWeight: 700 }}>AI Assistant</span>
          <kbd className="rounded px-1.5 py-0.5 text-xs font-mono" style={{ background: `${t.sidebar}40`, color: t.sidebar }}>⌘J</kbd>
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   OPTION 2: Account in sidebar top + compact header
   - Account at sidebar top (Datadog-style)
   - Sidebar items use ALL vertical space with bigger padding
   - Language in top-right of header
   - Full-width tabs below header
   ================================================================ */
function Option2() {
  return (
    <div className="flex h-[600px] overflow-hidden rounded-xl border" style={{ borderColor: t.border, background: t.bg }}>
      <div className="flex w-64 flex-col border-r" style={{ background: t.sidebar, borderColor: t.border }}>
        {/* Logo row */}
        <div className="flex items-center justify-between px-4 py-4">
          <div className="flex items-center gap-2.5">
            <Shield size={22} style={{ color: t.accent }} />
            <span style={{ color: t.text, fontFamily: "JetBrains Mono", fontSize: 18, fontWeight: 700, letterSpacing: 2 }}>AEGIS</span>
          </div>
        </div>

        {/* Service Account — IN SIDEBAR, prominent card */}
        <div className="mx-3 mb-3">
          <div className="rounded-xl px-4 py-3 cursor-pointer" style={{ background: `${t.accent}08`, border: `1px solid ${t.accent}20` }}>
            <div style={{ color: t.muted, fontSize: 11, fontWeight: 500, textTransform: "uppercase", letterSpacing: 1 }}>Service Account</div>
            <div className="flex items-center justify-between mt-1">
              <div className="flex items-center gap-2">
                <div className="h-2.5 w-2.5 rounded-full bg-green-400" />
                <span style={{ color: t.text, fontSize: 15, fontWeight: 600 }}>All Accounts</span>
              </div>
              <ChevronDown size={16} style={{ color: t.accent }} />
            </div>
            <div style={{ color: t.muted, fontSize: 12, marginTop: 2 }}>4 AWS · 0 GCP · 0 Azure</div>
          </div>
        </div>
        <div className="mx-4 h-px" style={{ background: t.border }} />

        {/* Nav — STRETCHED with bigger items */}
        <nav className="flex flex-1 flex-col gap-0.5 px-3 py-3">
          {navItems.map((item, i) => {
            const active = i === 1;
            return (
              <div key={item.label} className="flex items-center gap-3 rounded-xl px-4 py-3.5 cursor-pointer" style={{
                background: active ? `${t.accent}12` : "transparent",
              }}>
                <item.icon size={20} style={{ color: active ? t.accent : t.muted }} />
                <span style={{ color: active ? t.text : t.muted, fontSize: 15, fontWeight: active ? 600 : 400 }}>{item.label}</span>
                {i === 3 && <span className="ml-auto flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold" style={{ background: "#FF4444", color: "white" }}>2</span>}
              </div>
            );
          })}
        </nav>

        {/* Settings + Account Management at bottom */}
        <div className="mx-4 h-px" style={{ background: t.border }} />
        <div className="px-3 py-2 space-y-0.5">
          <div className="flex items-center gap-3 rounded-xl px-4 py-3 cursor-pointer">
            <Users size={19} style={{ color: t.muted }} />
            <span style={{ color: t.muted, fontSize: 14 }}>Account Mgmt</span>
          </div>
          <div className="flex items-center gap-3 rounded-xl px-4 py-3 cursor-pointer">
            <Settings size={19} style={{ color: t.muted }} />
            <span style={{ color: t.muted, fontSize: 14 }}>Settings</span>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col relative">
        {/* Compact header: page title + search + lang + user */}
        <div className="flex items-center justify-between border-b px-6" style={{ borderColor: t.border, height: 56 }}>
          <h1 style={{ color: t.text, fontSize: 22, fontWeight: 700 }}>SLO Dashboard</h1>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-lg px-3 py-2" style={{ background: t.surface }}>
              <Search size={14} style={{ color: t.muted }} />
              <span style={{ color: t.muted, fontSize: 13 }}>⌘K</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-lg px-2.5 py-2 cursor-pointer" style={{ background: t.surface }}>
              <Globe size={14} style={{ color: t.accent }} />
              <span style={{ color: t.text, fontSize: 12, fontWeight: 600 }}>EN</span>
            </div>
            <Bell size={18} style={{ color: t.muted }} />
            <div className="h-8 w-8 rounded-full" style={{ background: t.surface }} />
          </div>
        </div>

        {/* Status + Tabs row — FULL WIDTH, BIG */}
        <div className="flex items-center justify-between border-b px-6" style={{ borderColor: t.border, height: 52 }}>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5" style={{ color: t.accent, fontSize: 14, fontWeight: 500 }}>● 6 meeting</span>
            <span className="flex items-center gap-1.5" style={{ color: "#FFB020", fontSize: 14, fontWeight: 500 }}>▲ 2 at risk</span>
            <span className="flex items-center gap-1.5" style={{ color: "#FF4444", fontSize: 14, fontWeight: 500 }}>● 2 breaching</span>
          </div>
          <div className="flex items-center gap-1.5">
            {["All", "Weekly", "Monthly", "Quarterly", "Annually"].map((tab, i) => (
              <div key={tab} className="rounded-lg px-5 py-2.5 cursor-pointer" style={{
                background: i === 0 ? t.accent : t.surface,
                color: i === 0 ? t.sidebar : t.muted,
                fontSize: 14,
                fontWeight: i === 0 ? 700 : 500,
              }}>{tab}</div>
            ))}
            <div className="ml-2 rounded-lg px-5 py-2.5 cursor-pointer flex items-center gap-1.5" style={{ border: `1px solid ${t.accent}`, color: t.accent, fontSize: 14, fontWeight: 600 }}>
              + Create SLO
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-6">
          <div className="grid grid-cols-3 gap-5">
            {[
              { label: "SLOs Meeting Target", value: "6/10", color: t.accent },
              { label: "Avg Error Budget", value: "42%", color: "#00BFFF" },
              { label: "Worst Burn Rate", value: "3.2x", color: "#FF4444" },
            ].map(m => (
              <div key={m.label} className="rounded-xl p-6" style={{ background: t.card, border: `1px solid ${t.border}` }}>
                <div style={{ color: t.muted, fontSize: 14 }}>{m.label}</div>
                <div style={{ color: m.color, fontSize: 36, fontWeight: 700, fontFamily: "JetBrains Mono", marginTop: 8 }}>{m.value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Floating AI */}
        <div className="absolute bottom-6 right-6 flex items-center gap-3 rounded-2xl px-6 py-4 cursor-pointer" style={{ background: t.accent, boxShadow: `0 4px 30px ${t.accent}50` }}>
          <Sparkles size={22} style={{ color: t.sidebar }} />
          <span style={{ color: t.sidebar, fontSize: 16, fontWeight: 700 }}>Ask AI</span>
          <kbd className="rounded px-1.5 py-0.5 text-xs font-mono" style={{ background: `${t.sidebar}40`, color: t.sidebar }}>⌘J</kbd>
        </div>
      </div>
    </div>
  );
}

export default function DesignPreviewPage() {
  const [selected, setSelected] = useState<string | null>(null);

  const options = [
    {
      key: "1",
      name: "Option 1: Account in Top Bar",
      desc: "Service Account prominent in center of top bar. Language top-right. Sidebar fills height. Floating AI pill.",
      component: <Option1 />,
    },
    {
      key: "2",
      name: "Option 2: Account in Sidebar (Datadog-style)",
      desc: "Service Account card in sidebar top. Account Management link at bottom. Page title in header. Compact search.",
      component: <Option2 />,
    },
  ];

  return (
    <div className="min-h-screen p-8" style={{ background: "#0E0E16" }}>
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-6">
          <h1 style={{ color: t.text, fontFamily: "JetBrains Mono", fontSize: 28, fontWeight: 700 }}>Layout Options</h1>
          <p style={{ color: t.muted, fontSize: 15, marginTop: 6 }}>
            Fixed: Sidebar fills full height. Tabs all visible and bigger. AI as floating pill. Language visible.
          </p>
          <p style={{ color: t.muted, fontSize: 13, marginTop: 4 }}>
            Key difference: Where does the Service Account switcher live?
          </p>
          {selected && (
            <p className="mt-3" style={{ color: t.accent, fontFamily: "JetBrains Mono", fontSize: 14 }}>
              Selected: {options.find(o => o.key === selected)?.name}
            </p>
          )}
        </div>

        <div className="space-y-10">
          {options.map(opt => (
            <div key={opt.key}>
              <button onClick={() => setSelected(opt.key)} className="w-full text-left" style={{
                outline: selected === opt.key ? `2px solid ${t.accent}` : "2px solid transparent",
                borderRadius: 16,
                transition: "outline 0.2s",
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
                <div className="relative">{opt.component}</div>
              </button>
            </div>
          ))}
        </div>

        <div className="mt-8 p-5 rounded-xl" style={{ background: t.card, border: `1px solid ${t.border}` }}>
          <h3 style={{ color: t.text, fontSize: 16, fontWeight: 600 }}>What&apos;s fixed in both options:</h3>
          <ul className="mt-3 space-y-2" style={{ color: t.muted, fontSize: 14 }}>
            <li>✅ Sidebar fills <b style={{ color: t.text }}>full height</b> — no wasted space at bottom</li>
            <li>✅ Nav items are <b style={{ color: t.text }}>bigger</b> (py-3.5, text-15px, icons 20px)</li>
            <li>✅ Tabs show <b style={{ color: t.text }}>all options flat</b> — no scroll, bigger buttons (px-5 py-2.5)</li>
            <li>✅ AI button is a <b style={{ color: t.text }}>large floating pill</b> at bottom-right</li>
            <li>✅ Language switcher is <b style={{ color: t.text }}>visible</b> in top-right area</li>
            <li>✅ Service Account clearly labeled as <b style={{ color: t.text }}>&quot;Service Account&quot;</b></li>
            <li>✅ Metric numbers are <b style={{ color: t.text }}>36px</b>, labels 14px</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
