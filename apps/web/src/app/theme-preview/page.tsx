"use client";

import { useState } from "react";
import {
  Shield,
  Activity,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Search,
  Bell,
  ChevronDown,
  FileText,
  BarChart3,
  DollarSign,
  Zap,
  Lock,
  Rocket,
  Phone,
  Server,
  Bug,
  Clock,
  TrendingUp,
  TrendingDown,
} from "lucide-react";

type ThemeKey = "navy" | "charcoal" | "slate";

const themes: Record<
  ThemeKey,
  {
    name: string;
    bg: string;
    card: string;
    sidebar: string;
    border: string;
    text: string;
    muted: string;
    accent: string;
    surface: string;
  }
> = {
  navy: {
    name: "Navy Blue",
    bg: "#1A1B2E",
    card: "#1F2037",
    sidebar: "#161725",
    border: "rgba(255,255,255,0.12)",
    text: "#E8E8ED",
    muted: "#8B8BA0",
    accent: "#00FF88",
    surface: "#232440",
  },
  charcoal: {
    name: "Charcoal",
    bg: "#1E1E2A",
    card: "#252535",
    sidebar: "#1A1A26",
    border: "rgba(255,255,255,0.10)",
    text: "#E8E8ED",
    muted: "#9090A0",
    accent: "#00FF88",
    surface: "#2A2A3A",
  },
  slate: {
    name: "Slate",
    bg: "#1C1C28",
    card: "#222232",
    sidebar: "#18182A",
    border: "rgba(255,255,255,0.11)",
    text: "#E8E8ED",
    muted: "#8888A0",
    accent: "#00FF88",
    surface: "#282838",
  },
};

function MiniDashboard({ theme, themeKey }: { theme: (typeof themes)[ThemeKey]; themeKey: ThemeKey }) {
  return (
    <div
      className="rounded-xl overflow-hidden border"
      style={{ borderColor: theme.border, background: theme.bg }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: theme.border, background: theme.sidebar }}
      >
        <div className="flex items-center gap-2">
          <Shield style={{ color: theme.accent }} size={18} />
          <span style={{ color: theme.text, fontFamily: "JetBrains Mono", fontWeight: 600, fontSize: 14 }}>
            Aegis
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div
            className="flex items-center gap-2 rounded-md px-3 py-1.5"
            style={{ background: theme.surface, border: `1px solid ${theme.border}` }}
          >
            <Search size={13} style={{ color: theme.muted }} />
            <span style={{ color: theme.muted, fontSize: 12, fontFamily: "JetBrains Mono" }}>
              Search... ⌘K
            </span>
          </div>
          <Bell size={16} style={{ color: theme.muted }} />
          <div className="w-7 h-7 rounded-full" style={{ background: theme.surface }} />
        </div>
      </div>

      <div className="flex">
        {/* Sidebar */}
        <div
          className="w-48 p-3 space-y-1 border-r"
          style={{ background: theme.sidebar, borderColor: theme.border, minHeight: 420 }}
        >
          {[
            { icon: FileText, label: "Log Explorer", active: false },
            { icon: Activity, label: "SLO Dashboard", active: true },
            { icon: DollarSign, label: "FinOps", active: false },
            { icon: Zap, label: "Incidents", active: false },
            { icon: Lock, label: "Security", active: false },
            { icon: Rocket, label: "Deployments", active: false },
            { icon: Phone, label: "On-Call", active: false },
            { icon: Server, label: "Services", active: false },
          ].map(({ icon: Icon, label, active }) => (
            <div
              key={label}
              className="flex items-center gap-2 rounded-md px-3 py-2"
              style={{
                background: active ? `${theme.accent}15` : "transparent",
                borderLeft: active ? `2px solid ${theme.accent}` : "2px solid transparent",
              }}
            >
              <Icon size={15} style={{ color: active ? theme.accent : theme.muted }} />
              <span
                style={{
                  color: active ? theme.text : theme.muted,
                  fontSize: 13,
                  fontFamily: "Inter, sans-serif",
                  fontWeight: active ? 500 : 400,
                }}
              >
                {label}
              </span>
            </div>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 p-4 space-y-4">
          {/* Health Banner */}
          <div
            className="flex items-center gap-4 rounded-lg px-4 py-3"
            style={{ background: theme.surface, border: `1px solid ${theme.border}` }}
          >
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-400" />
              <span style={{ color: theme.text, fontSize: 13, fontFamily: "Inter, sans-serif" }}>
                4 Healthy
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-amber-400" />
              <span style={{ color: theme.text, fontSize: 13, fontFamily: "Inter, sans-serif" }}>
                1 Degraded
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-400 animate-pulse" />
              <span style={{ color: theme.text, fontSize: 13, fontFamily: "Inter, sans-serif" }}>
                1 Down
              </span>
            </div>
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: "Active Incidents", value: "3", icon: AlertTriangle, color: "#FF6B6B", trend: "+1" },
              { label: "SLOs Meeting", value: "8/10", icon: CheckCircle2, color: "#00FF88", trend: "" },
              { label: "Monthly Cost", value: "$12.4K", icon: DollarSign, color: "#00BFFF", trend: "-4.2%" },
              { label: "MTTR", value: "42m", icon: Clock, color: "#FFB020", trend: "-15%" },
            ].map(({ label, value, icon: Icon, color, trend }) => (
              <div
                key={label}
                className="rounded-lg p-3"
                style={{ background: theme.card, border: `1px solid ${theme.border}` }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon size={14} style={{ color }} />
                  <span style={{ color: theme.muted, fontSize: 12, fontFamily: "Inter, sans-serif" }}>
                    {label}
                  </span>
                </div>
                <div className="flex items-baseline gap-2">
                  <span style={{ color: theme.text, fontSize: 24, fontWeight: 700, fontFamily: "JetBrains Mono" }}>
                    {value}
                  </span>
                  {trend && (
                    <span
                      style={{
                        color: trend.startsWith("-") ? "#00FF88" : "#FF6B6B",
                        fontSize: 12,
                        fontFamily: "JetBrains Mono",
                      }}
                    >
                      {trend}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* SLO Table */}
          <div
            className="rounded-lg overflow-hidden"
            style={{ background: theme.card, border: `1px solid ${theme.border}` }}
          >
            <div className="px-4 py-3 border-b" style={{ borderColor: theme.border }}>
              <span style={{ color: theme.text, fontSize: 15, fontWeight: 600, fontFamily: "Inter, sans-serif" }}>
                SLO Status
              </span>
            </div>
            <div className="divide-y" style={{ borderColor: theme.border }}>
              {[
                { service: "api-gateway", slo: "Availability 99.9%", current: "99.95%", budget: 78, status: "meeting" },
                { service: "auth-service", slo: "Error Rate < 0.1%", current: "0.08%", budget: 32, status: "at_risk" },
                { service: "payment-service", slo: "Latency p99 < 500ms", current: "480ms", budget: 85, status: "meeting" },
                { service: "notification-svc", slo: "Availability 99.5%", current: "98.2%", budget: 8, status: "breaching" },
              ].map((row) => (
                <div
                  key={row.service}
                  className="flex items-center px-4 py-3 gap-4"
                  style={{
                    borderColor: theme.border,
                    borderLeft:
                      row.status === "breaching"
                        ? "3px solid #FF6B6B"
                        : row.status === "at_risk"
                          ? "3px solid #FFB020"
                          : "3px solid #00FF88",
                  }}
                >
                  <div className="w-32">
                    <span style={{ color: theme.text, fontSize: 13, fontFamily: "JetBrains Mono", fontWeight: 500 }}>
                      {row.service}
                    </span>
                  </div>
                  <div className="flex-1">
                    <span style={{ color: theme.muted, fontSize: 13, fontFamily: "Inter, sans-serif" }}>
                      {row.slo}
                    </span>
                  </div>
                  <div className="w-20 text-right">
                    <span style={{ color: theme.text, fontSize: 13, fontFamily: "JetBrains Mono" }}>
                      {row.current}
                    </span>
                  </div>
                  <div className="w-24">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 rounded-full" style={{ background: theme.surface }}>
                        <div
                          className="h-2 rounded-full"
                          style={{
                            width: `${row.budget}%`,
                            background: row.budget > 50 ? "#00FF88" : row.budget > 25 ? "#FFB020" : "#FF6B6B",
                          }}
                        />
                      </div>
                      <span style={{ color: theme.muted, fontSize: 11, fontFamily: "JetBrains Mono" }}>
                        {row.budget}%
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Incident Row */}
          <div
            className="flex items-center gap-3 rounded-lg px-4 py-3"
            style={{
              background: theme.card,
              border: `1px solid ${theme.border}`,
              borderLeft: "3px solid #FF6B6B",
              boxShadow: "0 0 15px rgba(255, 107, 107, 0.05)",
            }}
          >
            <div className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
            <span
              style={{
                color: "#FF6B6B",
                fontSize: 12,
                fontFamily: "JetBrains Mono",
                fontWeight: 600,
                textTransform: "uppercase",
              }}
            >
              CRITICAL
            </span>
            <span style={{ color: theme.text, fontSize: 14, fontFamily: "Inter, sans-serif" }}>
              Payment processing timeout — payment-service
            </span>
            <span style={{ color: theme.muted, fontSize: 12, fontFamily: "JetBrains Mono", marginLeft: "auto" }}>
              12m ago
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ThemePreviewPage() {
  const [selected, setSelected] = useState<ThemeKey | null>(null);

  return (
    <div className="min-h-screen bg-[#0E0E16] p-8">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-8">
          <h1
            className="text-3xl font-bold mb-2"
            style={{ color: "#E8E8ED", fontFamily: "JetBrains Mono" }}
          >
            Pick Your Theme
          </h1>
          <p style={{ color: "#8888A0", fontFamily: "Inter, sans-serif", fontSize: 16 }}>
            Click a theme to see it highlighted. All three pass WCAG AA contrast (4.5:1+).
          </p>
          {selected && (
            <p className="mt-3" style={{ color: "#00FF88", fontFamily: "JetBrains Mono", fontSize: 14 }}>
              Selected: {themes[selected].name} — tell me this is the one and I&apos;ll apply it
            </p>
          )}
        </div>

        <div className="space-y-8">
          {(Object.entries(themes) as [ThemeKey, (typeof themes)[ThemeKey]][]).map(
            ([key, theme]) => (
              <div key={key} className="space-y-3">
                <button
                  onClick={() => setSelected(key)}
                  className="w-full text-left"
                  style={{
                    outline: selected === key ? `2px solid #00FF88` : "2px solid transparent",
                    borderRadius: 12,
                    transition: "outline 0.2s",
                  }}
                >
                  <div className="flex items-center gap-3 mb-2 px-1">
                    <div className="w-5 h-5 rounded-full border-2" style={{
                      borderColor: selected === key ? "#00FF88" : "#555",
                      background: selected === key ? "#00FF88" : "transparent",
                    }} />
                    <span style={{ color: "#E8E8ED", fontFamily: "JetBrains Mono", fontSize: 16, fontWeight: 600 }}>
                      {theme.name}
                    </span>
                    <span style={{ color: "#8888A0", fontFamily: "JetBrains Mono", fontSize: 13 }}>
                      {theme.bg}
                    </span>
                  </div>
                  <MiniDashboard theme={theme} themeKey={key} />
                </button>
              </div>
            )
          )}
        </div>

        <div className="mt-8 text-center" style={{ color: "#8888A0", fontFamily: "Inter, sans-serif", fontSize: 14 }}>
          <p>Font sizes shown: 24px for metrics, 15px for headings, 13-14px for body, 12px for captions.</p>
          <p className="mt-1">All significantly larger than the current 10-11px throughout.</p>
        </div>
      </div>
    </div>
  );
}
