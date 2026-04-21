"use client";

import { useState } from "react";
import {
  Zap, Brain, Sparkles, ChevronDown, ChevronRight, Check,
  Shield, Settings2, MessageSquare, Globe, Save, RotateCcw,
  Play, Pause, Bell, Lock, Unlock, Eye, EyeOff, Database,
  Clock, Gauge, AlertTriangle, DollarSign, Layers, Terminal,
  GitBranch, Workflow, Bot, Cpu, BarChart3, Wrench,
} from "lucide-react";

const t = {
  bg: "#1E1E2A", card: "#252535", sidebar: "#1A1A26", surface: "#2A2A3A",
  text: "#E8E8ED", muted: "#9090A0", accent: "#00FF88", border: "rgba(255,255,255,0.10)",
};

function CollapsibleSection({ title, icon: Icon, color, defaultOpen, children }: {
  title: string; icon: React.ComponentType<{ size?: number; style?: React.CSSProperties }>; color: string; defaultOpen?: boolean; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  return (
    <div className="rounded-xl" style={{ background: t.card, border: `1px solid ${t.border}` }}>
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-3 px-5 py-4">
        <Icon size={20} style={{ color }} />
        <span style={{ color: t.text, fontSize: 16, fontWeight: 700, flex: 1, textAlign: "left" }}>{title}</span>
        {open ? <ChevronDown size={18} style={{ color: t.muted }} /> : <ChevronRight size={18} style={{ color: t.muted }} />}
      </button>
      {open && <div className="border-t px-5 pb-5 pt-4 space-y-4" style={{ borderColor: t.border }}>{children}</div>}
    </div>
  );
}

function ToggleRow({ label, desc, defaultOn }: { label: string; desc: string; defaultOn?: boolean }) {
  const [on, setOn] = useState(defaultOn ?? false);
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <div style={{ color: t.text, fontSize: 14 }}>{label}</div>
        <div style={{ color: t.muted, fontSize: 12 }}>{desc}</div>
      </div>
      <button onClick={() => setOn(!on)} className="rounded-full w-11 h-6 transition-colors" style={{ background: on ? t.accent : t.surface }}>
        <div className="h-5 w-5 rounded-full bg-white transition-transform" style={{ transform: on ? "translateX(22px)" : "translateX(2px)" }} />
      </button>
    </div>
  );
}

function SelectRow({ label, desc, options, defaultValue }: { label: string; desc: string; options: string[]; defaultValue: string }) {
  const [value, setValue] = useState(defaultValue);
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <div style={{ color: t.text, fontSize: 14 }}>{label}</div>
        <div style={{ color: t.muted, fontSize: 12 }}>{desc}</div>
      </div>
      <div className="flex gap-1">
        {options.map(o => (
          <button key={o} onClick={() => setValue(o)} className="rounded-lg px-3 py-1.5 text-sm transition-all" style={{
            background: value === o ? t.accent : t.surface,
            color: value === o ? t.sidebar : t.text,
            fontWeight: value === o ? 700 : 400,
            border: `1px solid ${value === o ? t.accent : t.border}`,
          }}>{o}</button>
        ))}
      </div>
    </div>
  );
}

export default function AISettingsPreviewPage() {
  const [mode, setMode] = useState<"eco" | "standard" | "deep">("standard");

  const modes = [
    { key: "eco" as const, label: "Eco", icon: Zap, color: "#00BFFF", model: "Haiku 4.5", cost: "$1/$5" },
    { key: "standard" as const, label: "Standard", icon: Brain, color: "#00FF88", model: "Sonnet 4.6", cost: "$3/$15" },
    { key: "deep" as const, label: "Deep", icon: Sparkles, color: "#A855F7", model: "Opus 4.6", cost: "$5/$25" },
  ];

  return (
    <div className="min-h-screen p-8" style={{ background: "#0E0E16" }}>
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center mb-8">
          <h1 style={{ color: t.text, fontFamily: "JetBrains Mono", fontSize: 28, fontWeight: 700 }}>
            AI & Token Settings — Full Preview
          </h1>
          <p style={{ color: t.muted, fontSize: 15, marginTop: 6 }}>
            Tier 1 + Tier 2 + Tier 4 combined. Collapsible sections for advanced options.
          </p>
        </div>

        {/* ═══ MODE SELECTION ═══ */}
        <div className="rounded-xl p-5" style={{ background: t.card, border: `1px solid ${t.border}` }}>
          <h2 style={{ color: t.text, fontSize: 18, fontWeight: 700, marginBottom: 16 }}>Intelligence Mode</h2>
          <div className="grid grid-cols-3 gap-3">
            {modes.map(m => (
              <button key={m.key} onClick={() => setMode(m.key)} className="rounded-xl p-4 text-left transition-all" style={{
                background: mode === m.key ? `${m.color}10` : t.surface,
                border: mode === m.key ? `2px solid ${m.color}40` : `1px solid ${t.border}`,
                boxShadow: mode === m.key ? `0 0 16px ${m.color}15` : "none",
              }}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <m.icon size={20} style={{ color: m.color }} />
                    <span style={{ color: m.color, fontSize: 16, fontWeight: 700 }}>{m.label}</span>
                  </div>
                  {mode === m.key && <Check size={16} style={{ color: m.color }} />}
                </div>
                <div style={{ color: t.text, fontSize: 13, fontFamily: "JetBrains Mono" }}>{m.model}</div>
                <div style={{ color: t.muted, fontSize: 12 }}>{m.cost} per 1M tokens</div>
              </button>
            ))}
          </div>
        </div>

        {/* ═══ BUDGET GUARDRAILS ═══ */}
        <div className="rounded-xl p-5" style={{ background: t.card, border: `1px solid ${t.border}` }}>
          <h2 style={{ color: t.text, fontSize: 18, fontWeight: 700, marginBottom: 16 }}>Budget & Guardrails</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div><div style={{ color: t.text, fontSize: 14 }}>Monthly budget</div><div style={{ color: t.muted, fontSize: 12 }}>Hard stop when exhausted</div></div>
              <div className="flex items-center gap-1 rounded-lg px-3 py-2" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
                <DollarSign size={14} style={{ color: t.accent }} />
                <span style={{ color: t.text, fontSize: 16, fontWeight: 700, fontFamily: "JetBrains Mono" }}>10.00</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div><div style={{ color: t.text, fontSize: 14 }}>Auto-downgrade to Eco at</div><div style={{ color: t.muted, fontSize: 12 }}>Preserves budget with cheaper model</div></div>
              <div className="flex items-center gap-1 rounded-lg px-3 py-2" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
                <Gauge size={14} style={{ color: "#FFB020" }} />
                <span style={{ color: t.text, fontSize: 16, fontWeight: 700, fontFamily: "JetBrains Mono" }}>80%</span>
              </div>
            </div>
            <div className="h-3 rounded-full overflow-hidden mt-3" style={{ background: t.surface }}>
              <div className="h-full rounded-full" style={{ width: "32%", background: t.accent }} />
            </div>
            <div className="flex justify-between" style={{ color: t.muted, fontSize: 12 }}>
              <span>$3.20 used (32%)</span><span>$6.80 remaining</span>
            </div>
          </div>
        </div>

        {/* ═══ TIER 1: RESPONSE PREFERENCES ═══ */}
        <CollapsibleSection title="Response Preferences" icon={MessageSquare} color="#00BFFF" defaultOpen={true}>
          <SelectRow label="Response style" desc="How detailed should AI responses be?" options={["Brief", "Balanced", "Detailed"]} defaultValue="Balanced" />
          <SelectRow label="Output language" desc="Language for AI responses" options={["English", "Korean", "Auto"]} defaultValue="English" />
          <ToggleRow label="Auto-save findings" desc="Save AI analysis to incident/SLO history automatically" defaultOn={true} />
          <ToggleRow label="Show token cost in responses" desc="Display tokens used + cost after every AI reply" defaultOn={true} />
          <ToggleRow label="Pre-operation confirmation" desc="Ask before running AI operations that cost > $0.05" defaultOn={true} />
        </CollapsibleSection>

        {/* ═══ TIER 2: AGENT BEHAVIOR (HARNESS) ═══ */}
        <CollapsibleSection title="Agent Behavior (Harness)" icon={Workflow} color="#A855F7">
          {/* Tool Permissions */}
          <div>
            <h4 style={{ color: t.text, fontSize: 14, fontWeight: 600, marginBottom: 8 }}>MCP Tool Permissions</h4>
            <div className="space-y-2">
              {[
                { tool: "query_logs", cat: "READ", status: "allowed" },
                { tool: "query_metrics", cat: "READ", status: "allowed" },
                { tool: "kubectl_read", cat: "READ", status: "allowed" },
                { tool: "kubectl_action", cat: "WRITE", status: "approval" },
                { tool: "terraform_apply", cat: "WRITE", status: "approval" },
                { tool: "terraform_destroy", cat: "BLOCKED", status: "blocked" },
                { tool: "aws_iam_modify", cat: "BLOCKED", status: "blocked" },
              ].map(t2 => (
                <div key={t2.tool} className="flex items-center justify-between rounded-lg px-4 py-2.5" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
                  <div className="flex items-center gap-3">
                    <Terminal size={14} style={{ color: t.muted }} />
                    <span style={{ color: t.text, fontSize: 13, fontFamily: "JetBrains Mono" }}>{t2.tool}</span>
                    <span className="rounded px-2 py-0.5 text-[10px] font-bold" style={{
                      background: t2.cat === "READ" ? `${t.accent}15` : t2.cat === "WRITE" ? "#FFB02015" : "#FF444415",
                      color: t2.cat === "READ" ? t.accent : t2.cat === "WRITE" ? "#FFB020" : "#FF4444",
                    }}>{t2.cat}</span>
                  </div>
                  <div className="flex gap-1">
                    {["allowed", "approval", "blocked"].map(s => (
                      <button key={s} className="rounded px-2.5 py-1 text-xs font-medium transition-all" style={{
                        background: t2.status === s ? (s === "allowed" ? `${t.accent}20` : s === "approval" ? "#FFB02020" : "#FF444420") : "transparent",
                        color: t2.status === s ? (s === "allowed" ? t.accent : s === "approval" ? "#FFB020" : "#FF4444") : t.muted,
                        border: `1px solid ${t2.status === s ? "transparent" : t.border}`,
                      }}>{s === "allowed" ? "✓ Allow" : s === "approval" ? "⚠ Approve" : "✕ Block"}</button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Hooks */}
          <div>
            <h4 style={{ color: t.text, fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Pre/Post Operation Hooks</h4>
            <div className="space-y-2">
              <div className="rounded-lg px-4 py-3" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
                <div className="flex items-center gap-2 mb-1">
                  <Play size={12} style={{ color: t.accent }} />
                  <span style={{ color: t.accent, fontSize: 12, fontWeight: 600 }}>PRE-HOOK</span>
                </div>
                <div style={{ color: t.text, fontSize: 13 }}>Before incident investigation → auto-pull last 1h logs and metrics</div>
              </div>
              <div className="rounded-lg px-4 py-3" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
                <div className="flex items-center gap-2 mb-1">
                  <Pause size={12} style={{ color: "#00BFFF" }} />
                  <span style={{ color: "#00BFFF", fontSize: 12, fontWeight: 600 }}>POST-HOOK</span>
                </div>
                <div style={{ color: t.text, fontSize: 13 }}>After investigation completes → create JIRA ticket + notify Slack #incidents</div>
              </div>
              <button className="flex items-center gap-2 rounded-lg px-4 py-2 w-full justify-center" style={{ border: `1px dashed ${t.border}`, color: t.muted, fontSize: 13 }}>
                + Add Hook
              </button>
            </div>
          </div>

          {/* Automated Triggers */}
          <div>
            <h4 style={{ color: t.text, fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Automated Triggers</h4>
            <div className="space-y-2">
              {[
                { trigger: "Error budget < 10%", action: "Auto-investigate top error source", enabled: true },
                { trigger: "Critical incident opened", action: "Start AI investigation in Standard mode", enabled: true },
                { trigger: "Cost anomaly detected", action: "Analyze and notify Slack", enabled: false },
              ].map((tr, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg px-4 py-3" style={{ background: t.surface, border: `1px solid ${t.border}` }}>
                  <div>
                    <div style={{ color: t.text, fontSize: 13 }}><span style={{ color: "#FFB020" }}>When:</span> {tr.trigger}</div>
                    <div style={{ color: t.muted, fontSize: 12 }}><span style={{ color: t.accent }}>Then:</span> {tr.action}</div>
                  </div>
                  <button className="rounded-full w-10 h-5" style={{ background: tr.enabled ? t.accent : t.surface }}>
                    <div className="h-4 w-4 rounded-full bg-white" style={{ transform: tr.enabled ? "translateX(22px)" : "translateX(2px)", transition: "0.2s" }} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Fallback Chain */}
          <SelectRow label="Fallback chain" desc="Auto-downgrade model on failure or rate limit" options={["Opus→Sonnet→Haiku", "Sonnet→Haiku", "No fallback"]} defaultValue="Opus→Sonnet→Haiku" />
        </CollapsibleSection>

        {/* ═══ TIER 2: CONTEXT MANAGEMENT ═══ */}
        <CollapsibleSection title="Context Management" icon={Database} color="#FFB020">
          <SelectRow label="Context window" desc="How many previous messages to include" options={["5 msgs", "10 msgs", "20 msgs", "Unlimited"]} defaultValue="10 msgs" />
          <SelectRow label="Prompt caching" desc="Aggressive saves tokens, conservative is fresher" options={["Aggressive", "Balanced", "Conservative"]} defaultValue="Aggressive" />
          <SelectRow label="Service scope" desc="What data to include in AI context" options={["Current account", "All accounts", "Custom"]} defaultValue="Current account" />
          <SelectRow label="History retention" desc="How long to keep AI conversation history" options={["7 days", "30 days", "90 days", "Forever"]} defaultValue="30 days" />
          <ToggleRow label="Include system status" desc="Auto-include live health summary in every query" defaultOn={true} />
          <ToggleRow label="Include recent incidents" desc="Add last 5 incidents as context for all queries" defaultOn={true} />
        </CollapsibleSection>

        {/* ═══ TIER 4: OUTPUT & QUALITY ═══ */}
        <CollapsibleSection title="Output & Quality" icon={Wrench} color="#FF6B6B">
          <SelectRow label="Temperature" desc="Lower = more deterministic, higher = more creative" options={["Low (0.1)", "Medium (0.5)", "High (0.8)"]} defaultValue="Low (0.1)" />
          <SelectRow label="Max retries" desc="Retry failed tool calls before giving up" options={["1", "3", "5"]} defaultValue="3" />
          <SelectRow label="Max output tokens" desc="Limit AI response length" options={["2K", "4K", "8K", "16K"]} defaultValue="8K" />
          <ToggleRow label="Structured output" desc="AI returns JSON-structured results (not just prose)" defaultOn={false} />
          <ToggleRow label="Citation mode" desc="AI cites specific log lines and metric values in responses" defaultOn={true} />
          <ToggleRow label="Confidence scores" desc="Show confidence percentage with every analysis" defaultOn={true} />
        </CollapsibleSection>

        {/* ═══ SUGGESTED ADDITIONAL TABS ═══ */}
        <div className="rounded-xl p-6 mt-10" style={{ background: `${t.accent}08`, border: `1px solid ${t.accent}20` }}>
          <h2 style={{ color: t.accent, fontSize: 20, fontWeight: 700, marginBottom: 12 }}>
            Suggested Additional Dashboard Tabs
          </h2>
          <p style={{ color: t.muted, fontSize: 14, marginBottom: 16 }}>
            Beyond the current 9 modules, these tabs would complete the control tower:
          </p>
          <div className="grid grid-cols-2 gap-4">
            {[
              { icon: Layers, name: "Control Tower", desc: "Multi-account governance, cross-account compliance, resource inventory, policy enforcement, cost guardrails", color: "#A855F7" },
              { icon: Wrench, name: "Integrations Hub", desc: "Manage all connected tools with health status, sync history, error logs. Visual pipeline showing data flow between tools", color: "#00BFFF" },
              { icon: Eye, name: "Audit Trail", desc: "Who did what, when — all system actions, config changes, AI operations, approvals. Tamper-proof activity log", color: "#FFB020" },
              { icon: Bell, name: "Alerts & Rules", desc: "Define alerting rules, thresholds, notification routing per account/service. Silence rules, escalation overrides", color: "#FF6B6B" },
              { icon: BarChart3, name: "Reports", desc: "Scheduled weekly/monthly reports — SLO compliance, cost summary, security posture, DORA metrics. PDF/email export", color: "#00FF88" },
              { icon: GitBranch, name: "Change Management", desc: "Track all infrastructure changes (Terraform, K8s, config), correlate with incidents, approval workflow", color: "#FF44FF" },
            ].map(tab => (
              <div key={tab.name} className="rounded-xl p-5" style={{ background: t.card, border: `1px solid ${t.border}` }}>
                <div className="flex items-center gap-3 mb-2">
                  <tab.icon size={22} style={{ color: tab.color }} />
                  <span style={{ color: t.text, fontSize: 16, fontWeight: 700 }}>{tab.name}</span>
                </div>
                <p style={{ color: t.muted, fontSize: 13, lineHeight: 1.5 }}>{tab.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
