"use client"

import * as React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import {
  Target,
  Clock,
  FileCheck,
  Flame,
  DollarSign,
  Settings2,
  X,
} from "lucide-react"
import {
  useAccountStore,
  getAccountName,
} from "@/lib/stores/account-store"

// Per-account target configs
interface AccountTargets {
  sloTarget: number
  mttrTarget: number
  slaTarget: number
  errorBudgetTarget: number
  costBudgetTarget: number
}

const DEFAULT_TARGETS: AccountTargets = {
  sloTarget: 99.9,
  mttrTarget: 30,
  slaTarget: 99.5,
  errorBudgetTarget: 43.2,
  costBudgetTarget: 12000,
}

// Mock actual values per account
const ACCOUNT_ACTUALS: Record<string, { slo: number; mttr: number; sla: number; errorBudgetUsed: number; costActual: number }> = {
  nx: { slo: 99.92, mttr: 22, sla: 99.95, errorBudgetUsed: 12.4, costActual: 8450 },
  shared: { slo: 99.85, mttr: 42, sla: 99.91, errorBudgetUsed: 18.5, costActual: 11200 },
  nw: { slo: 99.78, mttr: 55, sla: 99.40, errorBudgetUsed: 31.0, costActual: 6800 },
  dp: { slo: 99.95, mttr: 18, sla: 99.98, errorBudgetUsed: 5.2, costActual: 3200 },
}

const GLOBAL_ACTUALS = { slo: 99.85, mttr: 42, sla: 99.91, errorBudgetUsed: 18.5, costActual: 10400 }

interface TargetCardProps {
  label: string
  icon: React.ComponentType<{ className?: string }>
  actual: string
  target: string
  isMeeting: boolean
  progress: number // 0-100
}

function TargetCard({ label, icon: Icon, actual, target, isMeeting, progress }: TargetCardProps) {
  const accentColor = isMeeting ? "#00FF88" : "#FF4444"

  return (
    <Card className="border-t-2" style={{ borderTopColor: accentColor }}>
      <CardContent className="grid gap-3 p-5">
        {/* Label */}
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-muted-foreground" />
          <span className="font-mono text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            {label}
          </span>
        </div>

        {/* Value */}
        <span
          className="font-mono text-3xl font-bold tracking-tight"
          style={{ color: accentColor }}
        >
          {actual}
        </span>

        {/* Target + Badge */}
        <div className="flex items-center justify-between">
          <span className="font-mono text-sm text-muted-foreground">
            Target: {target}
          </span>
          <span
            className="rounded-sm px-2 py-0.5 font-mono text-xs font-semibold"
            style={{
              backgroundColor: `${accentColor}15`,
              color: accentColor,
            }}
          >
            {isMeeting ? "Meeting" : "Behind"}
          </span>
        </div>

        {/* Progress bar */}
        <div className="h-2.5 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(progress, 100)}%`,
              backgroundColor: accentColor,
              boxShadow: `0 0 8px ${accentColor}30`,
            }}
          />
        </div>
      </CardContent>
    </Card>
  )
}

export function SloTargets() {
  const { accounts } = useAccountStore()
  const [configOpen, setConfigOpen] = React.useState(false)
  const [configAccount, setConfigAccount] = React.useState<string>("nx")
  const [allTargets, setAllTargets] = React.useState<Record<string, AccountTargets>>({
    nx: { ...DEFAULT_TARGETS },
    shared: { ...DEFAULT_TARGETS, sloTarget: 99.9, mttrTarget: 35, costBudgetTarget: 15000 },
    nw: { ...DEFAULT_TARGETS, sloTarget: 99.5, mttrTarget: 45, costBudgetTarget: 8000 },
    dp: { ...DEFAULT_TARGETS, sloTarget: 99.9, mttrTarget: 25, costBudgetTarget: 5000 },
  })

  // Draft state for config panel
  const [draft, setDraft] = React.useState<AccountTargets>(allTargets[configAccount] ?? DEFAULT_TARGETS)

  React.useEffect(() => {
    setDraft(allTargets[configAccount] ?? DEFAULT_TARGETS)
  }, [configAccount, allTargets])

  function handleSave() {
    setAllTargets((prev) => ({ ...prev, [configAccount]: { ...draft } }))
    setConfigOpen(false)
  }

  // Compute aggregated actuals (weighted average across all accounts)
  const actuals = GLOBAL_ACTUALS
  const targets = DEFAULT_TARGETS

  // SLO
  const sloMeeting = actuals.slo >= targets.sloTarget
  const sloProgress = Math.min((actuals.slo / targets.sloTarget) * 100, 100)

  // MTTR
  const mttrMeeting = actuals.mttr <= targets.mttrTarget
  const mttrProgress = mttrMeeting
    ? 100
    : Math.max(0, ((targets.mttrTarget * 2 - actuals.mttr) / (targets.mttrTarget * 2)) * 100)

  // SLA
  const slaMeeting = actuals.sla >= targets.slaTarget
  const slaProgress = Math.min((actuals.sla / targets.slaTarget) * 100, 100)

  // Error Budget
  const budgetUsedPct = (actuals.errorBudgetUsed / targets.errorBudgetTarget) * 100
  const budgetMeeting = budgetUsedPct < 80
  const budgetProgress = budgetUsedPct

  // Cost Budget
  const costPct = (actuals.costActual / targets.costBudgetTarget) * 100
  const costMeeting = costPct <= 100
  const costProgress = costPct

  return (
    <div className="relative">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-mono text-sm font-medium uppercase tracking-widest text-muted-foreground/50">
          Team Targets
        </h2>
        <Button
          variant="outline"
          size="sm"
          className="gap-2 font-mono text-xs"
          onClick={() => setConfigOpen(!configOpen)}
        >
          <Settings2 className="size-4" />
          Configure Targets
        </Button>
      </div>

      <div className="flex gap-4">
        {/* Target cards grid */}
        <div className={cn("grid flex-1 gap-4", configOpen ? "grid-cols-3" : "grid-cols-5")}>
          <TargetCard
            label="SLO"
            icon={Target}
            actual={`${actuals.slo}%`}
            target={`${targets.sloTarget}%`}
            isMeeting={sloMeeting}
            progress={sloProgress}
          />
          <TargetCard
            label="MTTR"
            icon={Clock}
            actual={`${actuals.mttr}min`}
            target={`${targets.mttrTarget}min`}
            isMeeting={mttrMeeting}
            progress={mttrProgress}
          />
          <TargetCard
            label="SLA"
            icon={FileCheck}
            actual={`${actuals.sla}%`}
            target={`${targets.slaTarget}%`}
            isMeeting={slaMeeting}
            progress={slaProgress}
          />
          <TargetCard
            label="Error Budget"
            icon={Flame}
            actual={`${actuals.errorBudgetUsed}min`}
            target={`${targets.errorBudgetTarget}min/mo`}
            isMeeting={budgetMeeting}
            progress={budgetProgress}
          />
          <TargetCard
            label="Cost Budget"
            icon={DollarSign}
            actual={`$${actuals.costActual.toLocaleString()}`}
            target={`$${targets.costBudgetTarget.toLocaleString()}/mo`}
            isMeeting={costMeeting}
            progress={costProgress}
          />
        </div>

        {/* Config side panel */}
        {configOpen && (
          <div className="w-80 shrink-0 rounded-lg border border-border bg-card p-5">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-mono text-sm font-semibold uppercase tracking-widest text-foreground">
                Configure Targets
              </h3>
              <Button
                variant="ghost"
                size="icon"
                className="size-7"
                onClick={() => setConfigOpen(false)}
              >
                <X className="size-4" />
              </Button>
            </div>

            <p className="mb-4 font-mono text-xs text-muted-foreground">
              Targets are per-account. Select an account to configure its thresholds.
            </p>

            {/* Account dropdown */}
            <div className="mb-5">
              <label className="mb-1.5 block font-mono text-xs font-medium text-muted-foreground">
                Account
              </label>
              <Select value={configAccount} onValueChange={(v) => { if (v) setConfigAccount(v) }}>
                <SelectTrigger className="h-10 font-mono text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {accounts.map((acct) => (
                    <SelectItem key={acct.id} value={acct.id}>
                      <span className="flex items-center gap-2">
                        {acct.name}
                        <span className="rounded bg-muted/50 px-1.5 py-0.5 font-mono text-xs uppercase text-muted-foreground/60">
                          {acct.provider}
                        </span>
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Input fields */}
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block font-mono text-xs font-medium text-muted-foreground">
                  SLO Target (%)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  className="h-10 font-mono text-sm"
                  value={draft.sloTarget}
                  onChange={(e) => setDraft((d) => ({ ...d, sloTarget: parseFloat(e.target.value) || 0 }))}
                />
              </div>
              <div>
                <label className="mb-1.5 block font-mono text-xs font-medium text-muted-foreground">
                  MTTR Target (min)
                </label>
                <Input
                  type="number"
                  className="h-10 font-mono text-sm"
                  value={draft.mttrTarget}
                  onChange={(e) => setDraft((d) => ({ ...d, mttrTarget: parseInt(e.target.value) || 0 }))}
                />
              </div>
              <div>
                <label className="mb-1.5 block font-mono text-xs font-medium text-muted-foreground">
                  SLA Target (%)
                </label>
                <Input
                  type="number"
                  step="0.01"
                  className="h-10 font-mono text-sm"
                  value={draft.slaTarget}
                  onChange={(e) => setDraft((d) => ({ ...d, slaTarget: parseFloat(e.target.value) || 0 }))}
                />
              </div>
              <div>
                <label className="mb-1.5 block font-mono text-xs font-medium text-muted-foreground">
                  Error Budget (min/mo)
                </label>
                <Input
                  type="number"
                  step="0.1"
                  className="h-10 font-mono text-sm"
                  value={draft.errorBudgetTarget}
                  onChange={(e) => setDraft((d) => ({ ...d, errorBudgetTarget: parseFloat(e.target.value) || 0 }))}
                />
              </div>
              <div>
                <label className="mb-1.5 block font-mono text-xs font-medium text-muted-foreground">
                  Cost Budget ($/mo)
                </label>
                <Input
                  type="number"
                  className="h-10 font-mono text-sm"
                  value={draft.costBudgetTarget}
                  onChange={(e) => setDraft((d) => ({ ...d, costBudgetTarget: parseInt(e.target.value) || 0 }))}
                />
              </div>
            </div>

            {/* Save button */}
            <Button
              className="mt-6 w-full font-mono text-sm"
              onClick={handleSave}
            >
              Save Targets
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
