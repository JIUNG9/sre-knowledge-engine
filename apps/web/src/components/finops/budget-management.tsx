"use client"

import * as React from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardAction,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  AlertTriangle,
  Brain,
  Plus,
  TrendingUp,
  Wallet,
} from "lucide-react"
import { cn } from "@/lib/utils"

// --- Types ---

type BudgetScope = "account" | "service" | "team"
type BudgetStatus = "under" | "at_risk" | "exceeded"

interface BudgetItem {
  id: string
  scope: BudgetScope
  scopeId: string
  scopeLabel: string
  monthlyBudget: number
  currentSpend: number
  projectedEOM: number
  burnRate: number // dollars per day
  status: BudgetStatus
  alertThresholds: number[]
}

// --- Mock data ---

const BUDGETS: BudgetItem[] = [
  {
    id: "bgt-1",
    scope: "account",
    scopeId: "prod-main",
    scopeLabel: "prod-main",
    monthlyBudget: 8000,
    currentSpend: 5200,
    projectedEOM: 7800,
    burnRate: 260,
    status: "under",
    alertThresholds: [80, 90, 100],
  },
  {
    id: "bgt-2",
    scope: "account",
    scopeId: "shared",
    scopeLabel: "shared",
    monthlyBudget: 3000,
    currentSpend: 2700,
    projectedEOM: 4050,
    burnRate: 135,
    status: "exceeded",
    alertThresholds: [80, 90, 100],
  },
  {
    id: "bgt-3",
    scope: "service",
    scopeId: "rds",
    scopeLabel: "RDS (Database)",
    monthlyBudget: 3500,
    currentSpend: 2850,
    projectedEOM: 3420,
    burnRate: 142.5,
    status: "at_risk",
    alertThresholds: [80, 90, 100],
  },
  {
    id: "bgt-4",
    scope: "team",
    scopeId: "platform",
    scopeLabel: "Platform Team",
    monthlyBudget: 5000,
    currentSpend: 3100,
    projectedEOM: 4650,
    burnRate: 155,
    status: "under",
    alertThresholds: [80, 90, 100],
  },
  {
    id: "bgt-5",
    scope: "service",
    scopeId: "eks",
    scopeLabel: "EKS (Kubernetes)",
    monthlyBudget: 2500,
    currentSpend: 1950,
    projectedEOM: 2925,
    burnRate: 97.5,
    status: "exceeded",
    alertThresholds: [80, 90, 100],
  },
  {
    id: "bgt-6",
    scope: "team",
    scopeId: "data",
    scopeLabel: "Data Team",
    monthlyBudget: 2000,
    currentSpend: 1640,
    projectedEOM: 1968,
    burnRate: 82,
    status: "at_risk",
    alertThresholds: [80, 90, 100],
  },
]

// --- Helpers ---

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function getStatusColor(status: BudgetStatus): string {
  switch (status) {
    case "under":
      return "#00FF88"
    case "at_risk":
      return "#FFB020"
    case "exceeded":
      return "#FF4444"
  }
}

function getStatusLabel(status: BudgetStatus): string {
  switch (status) {
    case "under":
      return "Under Budget"
    case "at_risk":
      return "At Risk"
    case "exceeded":
      return "Exceeded"
  }
}

function getScopeIcon(scope: BudgetScope): string {
  switch (scope) {
    case "account":
      return "ACC"
    case "service":
      return "SVC"
    case "team":
      return "TEAM"
  }
}

function getProgressColor(percent: number): string {
  if (percent >= 100) return "#FF4444"
  if (percent >= 80) return "#FFB020"
  return "#00FF88"
}

// --- Budget row ---

function BudgetRow({ budget }: { budget: BudgetItem }) {
  const spendPercent = (budget.currentSpend / budget.monthlyBudget) * 100
  const projectedPercent = (budget.projectedEOM / budget.monthlyBudget) * 100
  const barColor = getProgressColor(spendPercent)
  const statusColor = getStatusColor(budget.status)

  return (
    <div className="space-y-3 rounded-lg border border-border/50 p-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center justify-center rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] font-medium text-muted-foreground">
            {getScopeIcon(budget.scope)}
          </span>
          <span className="font-mono text-sm font-medium text-foreground">
            {budget.scopeLabel}
          </span>
          <Badge
            variant="outline"
            className="gap-1 font-mono text-xs"
            style={{
              borderColor: `${statusColor}40`,
              color: statusColor,
              backgroundColor: `${statusColor}10`,
            }}
          >
            {budget.status === "exceeded" && (
              <AlertTriangle className="size-2.5" />
            )}
            {getStatusLabel(budget.status)}
          </Badge>
        </div>
        <span className="font-mono text-sm text-muted-foreground">
          {formatCurrency(budget.currentSpend)}{" "}
          <span className="text-muted-foreground/50">/</span>{" "}
          {formatCurrency(budget.monthlyBudget)}
        </span>
      </div>

      {/* Progress bar */}
      <div className="relative">
        <div className="h-3 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(spendPercent, 100)}%`,
              backgroundColor: barColor,
              boxShadow: `0 0 10px ${barColor}30`,
            }}
          />
        </div>
        {/* Threshold markers */}
        {budget.alertThresholds.map((t) => (
          <div
            key={t}
            className="absolute top-0 h-3 border-r border-dashed border-muted-foreground/30"
            style={{ left: `${Math.min(t, 100)}%` }}
          />
        ))}
        {/* Projected line */}
        {projectedPercent <= 150 && (
          <div
            className="absolute top-0 h-3 border-r-2 border-dashed"
            style={{
              left: `${Math.min(projectedPercent, 100)}%`,
              borderColor: getProgressColor(projectedPercent),
            }}
          >
            <div
              className="absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap font-mono text-[9px]"
              style={{ color: getProgressColor(projectedPercent) }}
            >
              EOM: {projectedPercent.toFixed(0)}%
            </div>
          </div>
        )}
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="font-mono text-xs text-muted-foreground">
            Spend:{" "}
            <span style={{ color: barColor }}>{spendPercent.toFixed(0)}%</span>
          </span>
          <span className="font-mono text-xs text-muted-foreground">
            Projected:{" "}
            <span style={{ color: getProgressColor(projectedPercent) }}>
              {formatCurrency(budget.projectedEOM)}
            </span>
          </span>
          <span className="font-mono text-xs text-muted-foreground">
            Burn rate:{" "}
            <span className="text-foreground/80">
              {formatCurrency(budget.burnRate)}/day
            </span>
          </span>
        </div>
      </div>
    </div>
  )
}

// --- Add Budget Dialog ---

function AddBudgetDialog() {
  const [open, setOpen] = React.useState(false)
  const [scope, setScope] = React.useState<string>("account")

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm" className="gap-1.5 font-mono text-xs">
            <Plus className="size-3" />
            Add Budget
          </Button>
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create Budget Target</DialogTitle>
          <DialogDescription>
            Set a monthly budget target with alert thresholds.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label className="font-mono text-xs">Scope</Label>
            <Select value={scope} onValueChange={(v) => v && setScope(v)}>
              <SelectTrigger className="w-full font-mono text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="account">Account</SelectItem>
                <SelectItem value="service">Service</SelectItem>
                <SelectItem value="team">Team</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="font-mono text-xs">
              {scope === "account"
                ? "Account"
                : scope === "service"
                  ? "Service"
                  : "Team"}
            </Label>
            <Select defaultValue="">
              <SelectTrigger className="w-full font-mono text-xs">
                <SelectValue placeholder="Select..." />
              </SelectTrigger>
              <SelectContent>
                {scope === "account" && (
                  <>
                    <SelectItem value="prod-main">prod-main</SelectItem>
                    <SelectItem value="prod-k8s">prod-k8s</SelectItem>
                    <SelectItem value="staging">staging</SelectItem>
                    <SelectItem value="shared">shared</SelectItem>
                    <SelectItem value="security">security</SelectItem>
                  </>
                )}
                {scope === "service" && (
                  <>
                    <SelectItem value="ec2">EC2 (Compute)</SelectItem>
                    <SelectItem value="rds">RDS (Database)</SelectItem>
                    <SelectItem value="eks">EKS (Kubernetes)</SelectItem>
                    <SelectItem value="s3">S3 (Storage)</SelectItem>
                    <SelectItem value="lambda">Lambda</SelectItem>
                  </>
                )}
                {scope === "team" && (
                  <>
                    <SelectItem value="engineering">Engineering</SelectItem>
                    <SelectItem value="platform">Platform</SelectItem>
                    <SelectItem value="data">Data</SelectItem>
                    <SelectItem value="security">Security</SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="font-mono text-xs">Monthly Budget (USD)</Label>
            <Input
              type="number"
              placeholder="5000"
              className="font-mono text-sm"
            />
          </div>
          <div className="space-y-2">
            <Label className="font-mono text-xs">Alert Thresholds (%)</Label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                defaultValue="80"
                className="w-20 font-mono text-sm"
              />
              <Input
                type="number"
                defaultValue="90"
                className="w-20 font-mono text-sm"
              />
              <Input
                type="number"
                defaultValue="100"
                className="w-20 font-mono text-sm"
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setOpen(false)}
            className="font-mono text-xs"
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={() => setOpen(false)}
            className="font-mono text-xs"
          >
            Create Budget
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// --- Main component ---

export function BudgetManagement() {
  const exceededCount = BUDGETS.filter((b) => b.status === "exceeded").length
  const atRiskCount = BUDGETS.filter((b) => b.status === "at_risk").length
  const totalBudget = BUDGETS.reduce((sum, b) => sum + b.monthlyBudget, 0)
  const totalSpend = BUDGETS.reduce((sum, b) => sum + b.currentSpend, 0)
  const totalProjected = BUDGETS.reduce((sum, b) => sum + b.projectedEOM, 0)

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card size="sm">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Wallet className="size-4 text-primary" />
              <span className="font-mono text-xs text-muted-foreground">
                Total Budget
              </span>
            </div>
            <p className="mt-2 font-mono text-3xl font-bold tracking-tight text-foreground">
              {formatCurrency(totalBudget)}
            </p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              {BUDGETS.length} active budgets
            </p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="size-4 text-[#00BFFF]" />
              <span className="font-mono text-xs text-muted-foreground">
                Current Spend
              </span>
            </div>
            <p className="mt-2 font-mono text-3xl font-bold tracking-tight text-foreground">
              {formatCurrency(totalSpend)}
            </p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              {((totalSpend / totalBudget) * 100).toFixed(0)}% of total budget
            </p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="size-4 text-[#A855F7]" />
              <span className="font-mono text-xs text-muted-foreground">
                Projected EOM
              </span>
            </div>
            <p className="mt-2 font-mono text-3xl font-bold tracking-tight text-foreground">
              {formatCurrency(totalProjected)}
            </p>
            <p
              className="mt-1 font-mono text-xs"
              style={{
                color:
                  totalProjected > totalBudget ? "#FF4444" : "#00FF88",
              }}
            >
              {totalProjected > totalBudget
                ? `${formatCurrency(totalProjected - totalBudget)} over budget`
                : `${formatCurrency(totalBudget - totalProjected)} under budget`}
            </p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-4 text-[#FFB020]" />
              <span className="font-mono text-xs text-muted-foreground">
                Alerts
              </span>
            </div>
            <p className="mt-2 font-mono text-3xl font-bold tracking-tight text-foreground">
              {exceededCount + atRiskCount}
            </p>
            <div className="mt-1 flex items-center gap-2">
              {exceededCount > 0 && (
                <span className="font-mono text-xs text-[#FF4444]">
                  {exceededCount} exceeded
                </span>
              )}
              {atRiskCount > 0 && (
                <span className="font-mono text-xs text-[#FFB020]">
                  {atRiskCount} at risk
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* AI Recommendation */}
      <Card
        size="sm"
        className="border-[#A855F7]/20 bg-[#A855F7]/5"
      >
        <CardContent className="pt-4">
          <div className="flex items-start gap-3">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-[#A855F7]/20">
              <Brain className="size-4 text-[#A855F7]" />
            </div>
            <div className="space-y-1">
              <p className="font-mono text-sm font-medium text-foreground">
                AI Budget Insight
              </p>
              <p className="font-mono text-xs leading-relaxed text-muted-foreground">
                Based on current burn rate, the{" "}
                <span className="font-medium text-[#FF4444]">shared</span>{" "}
                account will exceed its $3,000 budget by{" "}
                <span className="font-medium text-foreground">April 25th</span>.
                Current daily spend is $135/day vs $100/day budget pace.
                Consider migrating the CI/CD runner fleet to spot instances to
                reduce costs by ~35%.
              </p>
              <p className="font-mono text-xs leading-relaxed text-muted-foreground">
                The{" "}
                <span className="font-medium text-[#FFB020]">
                  RDS (Database)
                </span>{" "}
                service budget is tracking at 97.7% projected utilization.
                Enabling Aurora I/O-Optimized could save ~$200/mo on the
                highest-traffic instances.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Budget list */}
      <Card size="sm">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-muted-foreground">
            <Wallet className="size-4 text-primary" />
            Budget Targets
            {exceededCount > 0 && (
              <Badge
                variant="outline"
                className="font-mono text-xs"
                style={{
                  borderColor: "rgba(255,68,68,0.3)",
                  color: "#FF4444",
                }}
              >
                {exceededCount} projected over
              </Badge>
            )}
          </CardTitle>
          <CardAction>
            <AddBudgetDialog />
          </CardAction>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          {BUDGETS.map((budget) => (
            <BudgetRow key={budget.id} budget={budget} />
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
