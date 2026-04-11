"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ErrorBudgetSparkline } from "@/components/slo/error-budget-chart"
import { SloDetail } from "@/components/slo/slo-detail"
import { SloForm } from "@/components/slo/slo-form"
import { TimeWindowToggle } from "@/components/slo/time-window-toggle"
import { ServiceHealthGrid } from "@/components/slo/service-health-grid"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  MOCK_SLOS,
  type SloDefinition,
  type SloWindow,
  type SliType,
  type SloStatus,
} from "@/lib/mock-data/slo"
import {
  Activity,
  AlertTriangle,
  ArrowUpDown,
  CheckCircle2,
  Filter,
  Gauge,
  XCircle,
} from "lucide-react"

// --- Status helpers ---

function getStatusConfig(status: SloStatus) {
  switch (status) {
    case "meeting":
      return {
        label: "Meeting",
        color: "#00FF88",
        icon: CheckCircle2,
        borderColor: "border-l-[#00FF88]",
      }
    case "at_risk":
      return {
        label: "At Risk",
        color: "#FFB020",
        icon: AlertTriangle,
        borderColor: "border-l-[#FFB020]",
      }
    case "breaching":
      return {
        label: "Breaching",
        color: "#FF4444",
        icon: XCircle,
        borderColor: "border-l-[#FF4444]",
      }
  }
}

function getBurnRateConfig(burnRate: string) {
  switch (burnRate) {
    case "normal":
      return { label: "Normal", color: "#00FF88" }
    case "fast_burn":
      return { label: "Fast Burn", color: "#FFB020" }
    case "exhausted":
      return { label: "Exhausted", color: "#FF4444" }
    default:
      return { label: "Unknown", color: "#888" }
  }
}

function getErrorBudgetColor(remaining: number): string {
  if (remaining > 50) return "#00FF88"
  if (remaining > 25) return "#FFB020"
  return "#FF4444"
}

function formatCurrentValue(slo: SloDefinition): string {
  switch (slo.sliType) {
    case "availability":
      return `${slo.current}%`
    case "latency":
      return `${slo.current}ms`
    case "error_rate":
      return `${slo.current}%`
    case "throughput":
      return `${slo.current} msg/s`
    default:
      return `${slo.current}`
  }
}

function formatTarget(slo: SloDefinition): string {
  switch (slo.sliType) {
    case "availability":
      return `${slo.target}%`
    case "latency":
      return `< ${slo.target}ms`
    case "error_rate":
      return `< ${slo.target}%`
    case "throughput":
      return `> ${slo.target} msg/s`
    default:
      return `${slo.target}`
  }
}

function getSliTypeLabel(type: SliType): string {
  switch (type) {
    case "availability":
      return "Availability"
    case "latency":
      return "Latency"
    case "error_rate":
      return "Error Rate"
    case "throughput":
      return "Throughput"
  }
}

// --- Sort options ---

type SortOption = "error_budget" | "alphabetical" | "service"

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: "error_budget", label: "Worst Budget First" },
  { value: "alphabetical", label: "Alphabetical" },
  { value: "service", label: "By Service" },
]

// --- Filter options ---

type StatusFilter = "all" | "meeting" | "breaching"

// --- SLO Card ---

interface SloCardProps {
  slo: SloDefinition
  onClick: () => void
}

function SloCard({ slo, onClick }: SloCardProps) {
  const statusConfig = getStatusConfig(slo.status)
  const burnRateConfig = getBurnRateConfig(slo.burnRate)
  const budgetColor = getErrorBudgetColor(slo.errorBudgetRemaining)
  const StatusIcon = statusConfig.icon

  return (
    <Card
      className={cn(
        "cursor-pointer border-l-4 transition-all hover:bg-surface-hover",
        statusConfig.borderColor
      )}
      onClick={onClick}
    >
      <CardContent className="grid gap-4 p-6">
        {/* Header: service + status */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate font-mono text-base font-medium text-foreground">
              {slo.name}
            </p>
            <p className="font-mono text-sm text-muted-foreground">
              {slo.service}
            </p>
          </div>
          <StatusIcon className="size-6 shrink-0" style={{ color: statusConfig.color }} />
        </div>

        {/* Current vs Target */}
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-4xl font-bold text-foreground">
            {formatCurrentValue(slo)}
          </span>
          <span className="font-mono text-sm text-muted-foreground">
            / {formatTarget(slo)}
          </span>
        </div>

        {/* Error Budget Bar */}
        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <span className="font-mono text-sm text-muted-foreground">
              Error Budget
            </span>
            <span
              className="font-mono text-sm font-medium"
              style={{ color: budgetColor }}
            >
              {slo.errorBudgetRemaining}%
            </span>
          </div>
          <div className="h-4 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.max(slo.errorBudgetRemaining, 1)}%`,
                backgroundColor: budgetColor,
                boxShadow: `0 0 8px ${budgetColor}30`,
              }}
            />
          </div>
        </div>

        {/* Sparkline */}
        <ErrorBudgetSparkline data={slo.errorBudgetData} height={56} />

        {/* Footer: badges */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Burn rate */}
          <Badge
            variant="outline"
            className="gap-1 px-2.5 py-1 font-mono text-xs"
            style={{
              borderColor: `${burnRateConfig.color}30`,
              color: burnRateConfig.color,
            }}
          >
            <Gauge className="size-3" />
            {burnRateConfig.label}
          </Badge>

          {/* Window */}
          <Badge variant="outline" className="px-2.5 py-1 font-mono text-xs">
            {slo.window}
          </Badge>

          {/* SLI type */}
          <Badge variant="outline" className="px-2.5 py-1 font-mono text-xs">
            {getSliTypeLabel(slo.sliType)}
          </Badge>
        </div>
      </CardContent>
    </Card>
  )
}

// --- Main Overview ---

export function SloOverview() {
  const [windowFilter, setWindowFilter] = React.useState<SloWindow | "all">(
    "all"
  )
  const [sliTypeFilter, setSliTypeFilter] = React.useState<SliType | "all">(
    "all"
  )
  const [statusFilter, setStatusFilter] = React.useState<StatusFilter>("all")
  const [sortBy, setSortBy] = React.useState<SortOption>("error_budget")
  const [selectedService, setSelectedService] = React.useState<string | null>(
    null
  )
  const [selectedSlo, setSelectedSlo] = React.useState<SloDefinition | null>(
    null
  )

  // Apply filters
  let filtered = MOCK_SLOS.filter((slo) => {
    if (windowFilter !== "all" && slo.window !== windowFilter) return false
    if (sliTypeFilter !== "all" && slo.sliType !== sliTypeFilter) return false
    if (statusFilter === "meeting" && slo.status !== "meeting") return false
    if (
      statusFilter === "breaching" &&
      slo.status !== "breaching" &&
      slo.status !== "at_risk"
    )
      return false
    if (selectedService && slo.service !== selectedService) return false
    return true
  })

  // Apply sort
  filtered = [...filtered].sort((a, b) => {
    switch (sortBy) {
      case "error_budget":
        return a.errorBudgetRemaining - b.errorBudgetRemaining
      case "alphabetical":
        return a.name.localeCompare(b.name)
      case "service":
        return a.service.localeCompare(b.service) || a.name.localeCompare(b.name)
    }
  })

  // Summary counts
  const meetingCount = MOCK_SLOS.filter((s) => s.status === "meeting").length
  const atRiskCount = MOCK_SLOS.filter((s) => s.status === "at_risk").length
  const breachingCount = MOCK_SLOS.filter((s) => s.status === "breaching").length

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border px-8 py-5">
        <div className="flex items-center gap-4">
          <h1 className="font-heading text-2xl font-semibold text-foreground text-glow">
            SLO Dashboard
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <TimeWindowToggle value={windowFilter} onChange={setWindowFilter} />
          <SloForm />
        </div>
      </div>

      {/* Top Stats Row */}
      <div className="grid grid-cols-3 gap-6 border-b border-border px-8 py-6">
        <div className="flex items-center gap-4 rounded-lg bg-card px-6 py-5 ring-1 ring-foreground/10">
          <div className="flex size-12 items-center justify-center rounded-md bg-[#00FF88]/15">
            <CheckCircle2 className="size-6 text-[#00FF88]" />
          </div>
          <div>
            <p className="font-mono text-sm text-muted-foreground">Meeting SLO</p>
            <span className="font-mono text-4xl font-bold text-[#00FF88]">
              {meetingCount}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 rounded-lg bg-card px-6 py-5 ring-1 ring-foreground/10">
          <div className="flex size-12 items-center justify-center rounded-md bg-[#FFB020]/15">
            <AlertTriangle className="size-6 text-[#FFB020]" />
          </div>
          <div>
            <p className="font-mono text-sm text-muted-foreground">At Risk</p>
            <span className="font-mono text-4xl font-bold text-[#FFB020]">
              {atRiskCount}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 rounded-lg bg-card px-6 py-5 ring-1 ring-foreground/10">
          <div className="flex size-12 items-center justify-center rounded-md bg-[#FF4444]/15">
            <XCircle className="size-6 text-[#FF4444]" />
          </div>
          <div>
            <p className="font-mono text-sm text-muted-foreground">Breaching</p>
            <span className="font-mono text-4xl font-bold text-[#FF4444]">
              {breachingCount}
            </span>
          </div>
        </div>
      </div>

      {/* Scrollable content */}
      <ScrollArea className="flex-1">
        <div className="space-y-6 p-8">
          {/* Service Health Grid */}
          <ServiceHealthGrid
            selectedService={selectedService}
            onServiceSelect={setSelectedService}
          />

          {/* Filter bar */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Filter className="size-4" />
              <span className="font-mono text-sm">Filters:</span>
            </div>

            {/* SLI Type filter */}
            <Select
              value={sliTypeFilter}
              onValueChange={(v) => { if (v) setSliTypeFilter(v as SliType | "all") }}
            >
              <SelectTrigger className="h-10 font-mono text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="availability">Availability</SelectItem>
                <SelectItem value="latency">Latency</SelectItem>
                <SelectItem value="error_rate">Error Rate</SelectItem>
                <SelectItem value="throughput">Throughput</SelectItem>
              </SelectContent>
            </Select>

            {/* Status filter */}
            <Select
              value={statusFilter}
              onValueChange={(v) => { if (v) setStatusFilter(v as StatusFilter) }}
            >
              <SelectTrigger className="h-10 font-mono text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="meeting">Meeting</SelectItem>
                <SelectItem value="breaching">Breaching / At Risk</SelectItem>
              </SelectContent>
            </Select>

            {/* Sort */}
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <ArrowUpDown className="size-4" />
              <span className="font-mono text-sm">Sort:</span>
            </div>
            <Select
              value={sortBy}
              onValueChange={(v) => { if (v) setSortBy(v as SortOption) }}
            >
              <SelectTrigger className="h-10 font-mono text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Result count */}
            <span className="ml-auto font-mono text-sm text-muted-foreground">
              {filtered.length} SLO{filtered.length !== 1 ? "s" : ""}
            </span>
          </div>

          {/* SLO Cards Grid */}
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-16 text-muted-foreground/50">
              <Activity className="size-8" />
              <span className="font-mono text-sm">
                No SLOs match your filters
              </span>
              <Button
                variant="ghost"
                size="xs"
                className="font-mono text-xs"
                onClick={() => {
                  setWindowFilter("all")
                  setSliTypeFilter("all")
                  setStatusFilter("all")
                  setSelectedService(null)
                }}
              >
                Clear filters
              </Button>
            </div>
          ) : (
            <div className="grid gap-6 sm:grid-cols-1 lg:grid-cols-2">
              {filtered.map((slo) => (
                <SloCard
                  key={slo.id}
                  slo={slo}
                  onClick={() => setSelectedSlo(slo)}
                />
              ))}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Detail dialog */}
      {selectedSlo && (
        <SloDetail
          slo={selectedSlo}
          open={!!selectedSlo}
          onOpenChange={(open) => {
            if (!open) setSelectedSlo(null)
          }}
        />
      )}
    </div>
  )
}
