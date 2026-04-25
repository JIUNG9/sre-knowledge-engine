"use client"

import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  ArrowRight,
  Brain,
  CheckCircle2,
  Clock,
  Cpu,
  HardDrive,
  Lightbulb,
  Zap,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { DownloadButton } from "@/components/finops/download-button"

// --- Types ---

type RecType = "rightsize" | "schedule" | "scale"

interface ServiceUtilization {
  id: string
  service: string
  namespace: string
  cpuRequested: number
  cpuUsed: number
  cpuPeak: number
  memRequested: number
  memUsed: number
  memPeak: number
  replicas: number
  costPerMonth: number
}

interface Recommendation {
  id: string
  type: RecType
  service: string
  description: string
  currentSpec: string
  recommendedSpec: string
  estimatedSavings: number
  confidence: number
  trafficPattern: number[] // 24h pattern
}

interface HeatmapCell {
  hour: number
  day: string
  value: number
}

// --- Mock data ---

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

const HEATMAP_DATA: HeatmapCell[] = (() => {
  const cells: HeatmapCell[] = []
  for (const day of DAYS) {
    for (let hour = 0; hour < 24; hour++) {
      let base: number
      const isWeekend = day === "Sat" || day === "Sun"
      // Business hours (9-18 KST) = higher traffic
      if (hour >= 9 && hour <= 18) {
        base = isWeekend ? 30 : 80
      } else if (hour >= 6 && hour <= 21) {
        base = isWeekend ? 20 : 50
      } else {
        base = isWeekend ? 5 : 15
      }
      const jitter = Math.floor(Math.random() * 20) - 10
      cells.push({ hour, day, value: Math.max(0, base + jitter) })
    }
  }
  return cells
})()

const SERVICE_UTILIZATION: ServiceUtilization[] = [
  {
    id: "util-1",
    service: "api-gateway",
    namespace: "production",
    cpuRequested: 4,
    cpuUsed: 2.8,
    cpuPeak: 3.6,
    memRequested: 8,
    memUsed: 5.2,
    memPeak: 6.8,
    replicas: 3,
    costPerMonth: 540,
  },
  {
    id: "util-2",
    service: "auth-service",
    namespace: "production",
    cpuRequested: 2,
    cpuUsed: 0.3,
    cpuPeak: 0.8,
    memRequested: 4,
    memUsed: 1.2,
    memPeak: 2.1,
    replicas: 2,
    costPerMonth: 370,
  },
  {
    id: "util-3",
    service: "user-service",
    namespace: "production",
    cpuRequested: 2,
    cpuUsed: 1.4,
    cpuPeak: 1.9,
    memRequested: 4,
    memUsed: 2.8,
    memPeak: 3.5,
    replicas: 2,
    costPerMonth: 445,
  },
  {
    id: "util-4",
    service: "sse-server",
    namespace: "production",
    cpuRequested: 4,
    cpuUsed: 1.6,
    cpuPeak: 2.3,
    memRequested: 8,
    memUsed: 3.1,
    memPeak: 4.2,
    replicas: 2,
    costPerMonth: 620,
  },
  {
    id: "util-5",
    service: "admin-service",
    namespace: "production",
    cpuRequested: 1,
    cpuUsed: 0.2,
    cpuPeak: 0.4,
    memRequested: 2,
    memUsed: 0.6,
    memPeak: 1.0,
    replicas: 1,
    costPerMonth: 120,
  },
  {
    id: "util-6",
    service: "staging-all",
    namespace: "staging",
    cpuRequested: 12,
    cpuUsed: 2.4,
    cpuPeak: 5.8,
    memRequested: 24,
    memUsed: 6.2,
    memPeak: 12.0,
    replicas: 6,
    costPerMonth: 840,
  },
]

const RECOMMENDATIONS: Recommendation[] = [
  {
    id: "rec-1",
    type: "scale",
    service: "auth-service",
    description:
      "Scale to 1 replica 22:00-06:00 KST (15% CPU avg during off-hours). Traffic drops to <5 req/s overnight.",
    currentSpec: "2 replicas, 2 CPU / 4GB each",
    recommendedSpec: "1 replica overnight, 2 during business hours",
    estimatedSavings: 180,
    confidence: 94,
    trafficPattern: [
      5, 3, 2, 2, 3, 8, 25, 55, 78, 85, 90, 88, 82, 85, 88, 80, 72, 55, 35,
      22, 15, 10, 8, 6,
    ],
  },
  {
    id: "rec-2",
    type: "rightsize",
    service: "sse-server",
    description:
      "Right-size from 4 CPU to 2.5 CPU (peak utilization 2.3 CPU). Memory can be reduced from 8GB to 5GB (peak 4.2GB).",
    currentSpec: "4 CPU / 8GB memory, 2 replicas",
    recommendedSpec: "2.5 CPU / 5GB memory, 2 replicas",
    estimatedSavings: 280,
    confidence: 91,
    trafficPattern: [
      15, 12, 10, 8, 10, 18, 35, 52, 65, 72, 75, 70, 68, 72, 74, 68, 58, 42,
      30, 22, 18, 16, 15, 14,
    ],
  },
  {
    id: "rec-3",
    type: "schedule",
    service: "staging-all",
    description:
      "Schedule full shutdown 20:00-08:00 KST. Staging sees zero traffic outside business hours. Weekend shutdown saves additional $120/mo.",
    currentSpec: "6 pods running 24/7, 12 CPU / 24GB total",
    recommendedSpec: "6 pods 08:00-20:00 weekdays only",
    estimatedSavings: 420,
    confidence: 98,
    trafficPattern: [
      0, 0, 0, 0, 0, 0, 2, 8, 35, 52, 60, 58, 48, 55, 58, 50, 38, 22, 8, 2,
      0, 0, 0, 0,
    ],
  },
  {
    id: "rec-4",
    type: "rightsize",
    service: "api-gateway",
    description:
      "Reduce memory from 8GB to 6GB per replica. Peak memory usage is 6.8GB with healthy headroom at 6GB allocation.",
    currentSpec: "4 CPU / 8GB memory, 3 replicas",
    recommendedSpec: "4 CPU / 6GB memory, 3 replicas",
    estimatedSavings: 90,
    confidence: 87,
    trafficPattern: [
      20, 15, 12, 10, 12, 22, 45, 68, 82, 88, 92, 90, 85, 88, 90, 85, 75, 58,
      40, 30, 25, 22, 20, 18,
    ],
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

function getHeatColor(value: number): string {
  if (value >= 80) return "rgba(0, 255, 136, 0.8)"
  if (value >= 60) return "rgba(0, 255, 136, 0.55)"
  if (value >= 40) return "rgba(0, 255, 136, 0.35)"
  if (value >= 20) return "rgba(0, 255, 136, 0.18)"
  if (value >= 5) return "rgba(0, 255, 136, 0.08)"
  return "rgba(255, 255, 255, 0.03)"
}

function getUtilColor(percent: number): string {
  if (percent >= 70) return "#00FF88"
  if (percent >= 40) return "#FFB020"
  return "#FF4444"
}

const REC_ICONS: Record<RecType, React.ComponentType<{ className?: string; style?: React.CSSProperties }>> = {
  rightsize: Cpu,
  schedule: Clock,
  scale: Zap,
}

function getRecColor(type: RecType): string {
  switch (type) {
    case "rightsize":
      return "#00BFFF"
    case "schedule":
      return "#A855F7"
    case "scale":
      return "#FFB020"
  }
}

// --- Heatmap component ---

function TrafficHeatmap() {
  return (
    <Card size="sm">
      <CardHeader className="border-b">
        <CardTitle className="text-muted-foreground">
          Traffic Pattern Heatmap (24h x 7d)
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="overflow-x-auto">
          <div className="min-w-[600px]">
            {/* Hour labels */}
            <div className="mb-1 flex">
              <div className="w-10 shrink-0" />
              {Array.from({ length: 24 }, (_, i) => (
                <div
                  key={i}
                  className="flex-1 text-center font-mono text-[9px] text-muted-foreground/50"
                >
                  {i.toString().padStart(2, "0")}
                </div>
              ))}
            </div>
            {/* Grid rows */}
            {DAYS.map((day) => (
              <div key={day} className="flex items-center gap-0">
                <div className="w-10 shrink-0 font-mono text-[10px] text-muted-foreground">
                  {day}
                </div>
                <div className="flex flex-1 gap-px">
                  {HEATMAP_DATA.filter((c) => c.day === day).map((cell) => (
                    <div
                      key={`${cell.day}-${cell.hour}`}
                      className="flex-1 rounded-[2px]"
                      style={{
                        backgroundColor: getHeatColor(cell.value),
                        height: "20px",
                      }}
                      title={`${cell.day} ${cell.hour}:00 - ${cell.value}% traffic`}
                    />
                  ))}
                </div>
              </div>
            ))}
            {/* Legend */}
            <div className="mt-3 flex items-center justify-end gap-2">
              <span className="font-mono text-[9px] text-muted-foreground/50">
                Low
              </span>
              {[5, 20, 40, 60, 80].map((v) => (
                <div
                  key={v}
                  className="size-3 rounded-[2px]"
                  style={{ backgroundColor: getHeatColor(v) }}
                />
              ))}
              <span className="font-mono text-[9px] text-muted-foreground/50">
                High
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// --- Utilization table ---

function UtilizationSummary() {
  return (
    <Card size="sm">
      <CardHeader className="border-b">
        <CardTitle className="text-muted-foreground">
          CPU / Memory Utilization by Service
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="space-y-3">
          {SERVICE_UTILIZATION.map((svc) => {
            const cpuPercent = (svc.cpuUsed / svc.cpuRequested) * 100
            const memPercent = (svc.memUsed / svc.memRequested) * 100

            return (
              <div
                key={svc.id}
                className="rounded-lg border border-border/50 p-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium text-foreground">
                      {svc.service}
                    </span>
                    <span className="font-mono text-[10px] text-muted-foreground/50">
                      {svc.namespace}
                    </span>
                    <Badge
                      variant="outline"
                      className="font-mono text-[10px]"
                    >
                      {svc.replicas}x replicas
                    </Badge>
                  </div>
                  <span className="font-mono text-xs text-muted-foreground">
                    {formatCurrency(svc.costPerMonth)}/mo
                  </span>
                </div>
                <div className="mt-2.5 grid grid-cols-2 gap-4">
                  {/* CPU bar */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1 font-mono text-[10px] text-muted-foreground">
                        <Cpu className="size-2.5" />
                        CPU
                      </span>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {svc.cpuUsed}/{svc.cpuRequested} cores (peak{" "}
                        {svc.cpuPeak})
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.min(cpuPercent, 100)}%`,
                          backgroundColor: getUtilColor(cpuPercent),
                        }}
                      />
                    </div>
                  </div>
                  {/* Memory bar */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1 font-mono text-[10px] text-muted-foreground">
                        <HardDrive className="size-2.5" />
                        Memory
                      </span>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {svc.memUsed}/{svc.memRequested}GB (peak {svc.memPeak}
                        GB)
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.min(memPercent, 100)}%`,
                          backgroundColor: getUtilColor(memPercent),
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

// --- Recommendation Card ---

interface TrafficTooltipProps {
  active?: boolean
  payload?: Array<{ value: number; payload: { hour: string; traffic: number } }>
}

function TrafficTooltip({ active, payload }: TrafficTooltipProps) {
  if (!active || !payload || !payload.length) return null
  const item = payload[0].payload
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="font-mono text-muted-foreground">{item.hour}:00</p>
      <p className="font-mono font-medium text-foreground">
        {item.traffic}% traffic
      </p>
    </div>
  )
}

function RecommendationCard({ rec }: { rec: Recommendation }) {
  const Icon = REC_ICONS[rec.type]
  const color = getRecColor(rec.type)
  const chartData = rec.trafficPattern.map((v, i) => ({
    hour: i.toString().padStart(2, "0"),
    traffic: v,
  }))

  return (
    <Card size="sm" className="overflow-hidden">
      <CardContent className="pt-4">
        <div className="flex items-start gap-3">
          <div
            className="flex size-8 shrink-0 items-center justify-center rounded-lg"
            style={{ backgroundColor: `${color}20` }}
          >
            <Icon className="size-4" style={{ color }} />
          </div>
          <div className="flex-1 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-medium text-foreground">
                  {rec.service}
                </span>
                <Badge
                  variant="outline"
                  className="font-mono text-[10px]"
                  style={{ borderColor: `${color}40`, color }}
                >
                  {rec.type}
                </Badge>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="font-mono text-lg font-bold text-[#00FF88]">
                  {formatCurrency(rec.estimatedSavings)}
                </span>
                <span className="font-mono text-xs text-muted-foreground">
                  /mo
                </span>
              </div>
            </div>

            <p className="font-mono text-xs leading-relaxed text-muted-foreground">
              {rec.description}
            </p>

            {/* Current vs Recommended */}
            <div className="flex items-center gap-3">
              <div className="flex-1 rounded-md bg-muted/50 p-2">
                <span className="font-mono text-[10px] text-muted-foreground/50">
                  Current
                </span>
                <p className="mt-0.5 font-mono text-xs text-foreground/80">
                  {rec.currentSpec}
                </p>
              </div>
              <ArrowRight className="size-3.5 shrink-0 text-muted-foreground/30" />
              <div className="flex-1 rounded-md bg-[#00FF88]/5 p-2">
                <span className="font-mono text-[10px] text-[#00FF88]/60">
                  Recommended
                </span>
                <p className="mt-0.5 font-mono text-xs text-foreground/80">
                  {rec.recommendedSpec}
                </p>
              </div>
            </div>

            {/* Traffic pattern mini chart */}
            <div className="h-[80px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  margin={{ top: 0, right: 0, left: 0, bottom: 0 }}
                >
                  <XAxis
                    dataKey="hour"
                    tick={{ fontSize: 8, fill: "rgba(255,255,255,0.3)" }}
                    tickLine={false}
                    axisLine={false}
                    interval={5}
                  />
                  <RechartsTooltip content={<TrafficTooltip />} />
                  <Bar dataKey="traffic" radius={[2, 2, 0, 0]} barSize={8}>
                    {chartData.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={
                          entry.traffic > 50
                            ? `${color}CC`
                            : `${color}44`
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] text-muted-foreground/50">
                Confidence: {rec.confidence}%
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="xs"
                  className="font-mono text-xs text-muted-foreground"
                >
                  Dismiss
                </Button>
                <Button
                  variant="outline"
                  size="xs"
                  className="gap-1 font-mono text-xs"
                >
                  <CheckCircle2 className="size-3" />
                  Apply
                </Button>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// --- Main component ---

export function RightsizingRecommendations() {
  const totalSavings = RECOMMENDATIONS.reduce(
    (sum, r) => sum + r.estimatedSavings,
    0
  )

  return (
    <div className="space-y-6">
      {/* Total savings highlight */}
      <Card
        size="sm"
        className="border-[#00FF88]/20 bg-[#00FF88]/5"
      >
        <CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-lg bg-[#00FF88]/20">
                <Lightbulb className="size-5 text-[#00FF88]" />
              </div>
              <div>
                <p className="font-mono text-sm text-muted-foreground">
                  Total Potential Savings
                </p>
                <p className="font-mono text-3xl font-bold tracking-tight text-[#00FF88]">
                  {formatCurrency(totalSavings)}
                  <span className="ml-1 text-sm font-normal text-muted-foreground">
                    /month
                  </span>
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className="gap-1 font-mono text-xs"
                style={{
                  borderColor: "rgba(0,255,136,0.3)",
                  color: "#00FF88",
                }}
              >
                {RECOMMENDATIONS.length} recommendations
              </Badge>
              <DownloadButton
                view="k8s"
                params={{ aggregate: "namespace", window: "7d" }}
                label="Export"
              />
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 font-mono text-xs"
              >
                <CheckCircle2 className="size-3" />
                Apply All
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Heatmap */}
      <TrafficHeatmap />

      {/* Utilization summary */}
      <UtilizationSummary />

      {/* AI Recommendations */}
      <div className="flex items-center gap-2">
        <Brain className="size-4 text-[#A855F7]" />
        <h2 className="font-heading text-lg font-semibold text-foreground">
          AI-Generated Recommendations
        </h2>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {RECOMMENDATIONS.map((rec) => (
          <RecommendationCard key={rec.id} rec={rec} />
        ))}
      </div>
    </div>
  )
}
