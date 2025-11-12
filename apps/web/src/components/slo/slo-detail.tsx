"use client"

import * as React from "react"
import {
  Line,
  LineChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { ErrorBudgetChart } from "@/components/slo/error-budget-chart"
import type { SloDefinition } from "@/lib/mock-data/slo"
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Gauge,
} from "lucide-react"

interface SloDetailProps {
  slo: SloDefinition
  open: boolean
  onOpenChange: (open: boolean) => void
}

function getStatusConfig(status: string) {
  switch (status) {
    case "meeting":
      return {
        label: "Meeting SLO",
        color: "#00FF88",
        icon: CheckCircle2,
        bgClass: "bg-[#00FF88]/10",
        textClass: "text-[#00FF88]",
      }
    case "at_risk":
      return {
        label: "At Risk",
        color: "#FFB020",
        icon: AlertTriangle,
        bgClass: "bg-[#FFB020]/10",
        textClass: "text-[#FFB020]",
      }
    case "breaching":
      return {
        label: "Breaching",
        color: "#FF4444",
        icon: XCircle,
        bgClass: "bg-[#FF4444]/10",
        textClass: "text-[#FF4444]",
      }
    default:
      return {
        label: "Unknown",
        color: "#888",
        icon: Activity,
        bgClass: "bg-muted",
        textClass: "text-muted-foreground",
      }
  }
}

function getBurnRateLabel(burnRate: string) {
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

function formatSliValue(slo: SloDefinition): string {
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

interface SliTooltipProps {
  active?: boolean
  payload?: Array<{ value: number }>
  label?: string
  sliType: string
}

function SliTooltip({ active, payload, label, sliType }: SliTooltipProps) {
  if (!active || !payload || !payload.length) return null
  const value = payload[0].value
  const unit =
    sliType === "latency"
      ? "ms"
      : sliType === "throughput"
        ? " msg/s"
        : "%"
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-mono text-muted-foreground">{label}</p>
      <p className="font-mono font-medium text-primary">
        {value.toFixed(sliType === "availability" || sliType === "error_rate" ? 3 : 0)}
        {unit}
      </p>
    </div>
  )
}

export function SloDetail({ slo, open, onOpenChange }: SloDetailProps) {
  const statusConfig = getStatusConfig(slo.status)
  const burnRateConfig = getBurnRateLabel(slo.burnRate)
  const budgetColor = getErrorBudgetColor(slo.errorBudgetRemaining)
  const StatusIcon = statusConfig.icon

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => onOpenChange(false)}
            >
              <ArrowLeft className="size-3.5" />
            </Button>
            <DialogTitle className="flex items-center gap-2">
              <span>{slo.name}</span>
            </DialogTitle>
          </div>
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Badge variant="outline" className="font-mono text-[10px]">
              {slo.service}
            </Badge>
            <Badge variant="outline" className="font-mono text-[10px]">
              {slo.sliType}
            </Badge>
            <Badge variant="outline" className="font-mono text-[10px]">
              {slo.window}
            </Badge>
            <Badge
              className={cn(
                "font-mono text-[10px]",
                statusConfig.bgClass,
                statusConfig.textClass,
                "border-0"
              )}
            >
              <StatusIcon className="mr-0.5 size-3" />
              {statusConfig.label}
            </Badge>
          </div>
        </DialogHeader>

        <div className="grid gap-6">
          {/* Key metrics row */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {/* Current Value */}
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <p className="font-mono text-[10px] text-muted-foreground">
                Current
              </p>
              <p className="font-mono text-lg font-semibold text-foreground">
                {formatSliValue(slo)}
              </p>
            </div>
            {/* Target */}
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <p className="font-mono text-[10px] text-muted-foreground">
                Target
              </p>
              <p className="font-mono text-lg font-semibold text-foreground">
                {formatTarget(slo)}
              </p>
            </div>
            {/* Error Budget */}
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <p className="font-mono text-[10px] text-muted-foreground">
                Error Budget
              </p>
              <p
                className="font-mono text-lg font-semibold"
                style={{ color: budgetColor }}
              >
                {slo.errorBudgetRemaining}%
              </p>
            </div>
            {/* Burn Rate */}
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <p className="font-mono text-[10px] text-muted-foreground">
                Burn Rate
              </p>
              <div className="flex items-center gap-1.5">
                <Gauge
                  className="size-4"
                  style={{ color: burnRateConfig.color }}
                />
                <p
                  className="font-mono text-sm font-medium"
                  style={{ color: burnRateConfig.color }}
                >
                  {burnRateConfig.label}
                </p>
              </div>
            </div>
          </div>

          {/* Error Budget Gauge */}
          <div>
            <h3 className="mb-2 font-mono text-xs font-medium text-muted-foreground">
              Error Budget Remaining
            </h3>
            <div className="relative h-6 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.max(slo.errorBudgetRemaining, 1)}%`,
                  backgroundColor: budgetColor,
                  boxShadow: `0 0 12px ${budgetColor}40`,
                }}
              />
              <div className="absolute inset-0 flex items-center justify-center font-mono text-[10px] font-bold text-foreground">
                {slo.errorBudgetRemaining}% remaining
              </div>
            </div>
          </div>

          {/* Error Budget Burn-Down Chart */}
          <div>
            <h3 className="mb-2 font-mono text-xs font-medium text-muted-foreground">
              Error Budget Burn-Down ({slo.window} window)
            </h3>
            <ErrorBudgetChart
              data={slo.errorBudgetData}
              events={slo.events}
              height={220}
            />
          </div>

          {/* SLI Measurement History */}
          <div>
            <h3 className="mb-2 font-mono text-xs font-medium text-muted-foreground">
              SLI Measurement History
            </h3>
            <div style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={slo.sliHistory}
                  margin={{ top: 8, right: 8, left: -20, bottom: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(255,255,255,0.05)"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="date"
                    tick={{
                      fontSize: 10,
                      fill: "rgba(255,255,255,0.4)",
                    }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val: string) => {
                      const d = new Date(val)
                      return `${d.getMonth() + 1}/${d.getDate()}`
                    }}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    tick={{
                      fontSize: 10,
                      fill: "rgba(255,255,255,0.4)",
                    }}
                    tickLine={false}
                    axisLine={false}
                    domain={["dataMin - 0.1", "dataMax + 0.1"]}
                  />
                  <RechartsTooltip
                    content={<SliTooltip sliType={slo.sliType} />}
                  />
                  {/* Target reference line for availability/error_rate */}
                  {(slo.sliType === "availability" ||
                    slo.sliType === "error_rate") && (
                    <ReferenceLine
                      y={slo.target}
                      stroke="#FFB020"
                      strokeDasharray="4 4"
                      strokeOpacity={0.6}
                      label={{
                        value: `Target: ${slo.target}%`,
                        position: "insideTopRight",
                        fontSize: 9,
                        fill: "#FFB020",
                      }}
                    />
                  )}
                  {/* Event annotations */}
                  {slo.events.map((event, i) => (
                    <ReferenceLine
                      key={`sli-event-${i}`}
                      x={event.date}
                      stroke={
                        event.type === "incident"
                          ? "rgba(255,68,68,0.5)"
                          : "rgba(0,255,136,0.3)"
                      }
                      strokeDasharray="2 2"
                    />
                  ))}
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#00FF88"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{
                      r: 4,
                      fill: "#00FF88",
                      stroke: "rgba(10,10,15,0.8)",
                      strokeWidth: 2,
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Events Timeline */}
          {slo.events.length > 0 && (
            <div>
              <h3 className="mb-2 font-mono text-xs font-medium text-muted-foreground">
                Events
              </h3>
              <div className="space-y-1.5">
                {slo.events.map((event, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 rounded-md bg-muted/30 px-3 py-1.5"
                  >
                    <div
                      className="size-1.5 rounded-full"
                      style={{
                        backgroundColor:
                          event.type === "incident" ? "#FF4444" : "#00FF88",
                      }}
                    />
                    <span className="font-mono text-[10px] text-muted-foreground">
                      {event.date}
                    </span>
                    <Badge
                      variant="outline"
                      className={cn(
                        "font-mono text-[9px]",
                        event.type === "incident"
                          ? "border-[#FF4444]/30 text-[#FF4444]"
                          : "border-[#00FF88]/30 text-[#00FF88]"
                      )}
                    >
                      {event.type}
                    </Badge>
                    <span className="truncate font-mono text-xs text-foreground">
                      {event.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Description */}
          <div>
            <h3 className="mb-1 font-mono text-xs font-medium text-muted-foreground">
              Description
            </h3>
            <p className="font-mono text-xs text-muted-foreground/80">
              {slo.description}
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
