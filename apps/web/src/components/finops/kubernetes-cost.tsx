"use client"

import * as React from "react"
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  AlertTriangle,
  ArrowDownRight,
  Clock,
  Server,
  Trash2,
  Zap,
} from "lucide-react"
import { cn } from "@/lib/utils"
import {
  K8S_NAMESPACE_COSTS,
  K8S_POD_COSTS,
  K8S_RECOMMENDATIONS,
  type K8sNamespaceCost,
  type K8sRecommendation,
} from "@/lib/mock-data/finops"

// --- Helpers ---

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function getWasteColor(waste: number): string {
  if (waste >= 60) return "#FF4444"
  if (waste >= 40) return "#FFB020"
  return "#00FF88"
}

function getRecommendationIcon(type: K8sRecommendation["type"]) {
  switch (type) {
    case "downsize":
      return ArrowDownRight
    case "terminate":
      return Trash2
    case "right-size":
      return Zap
    case "schedule":
      return Clock
  }
}

function getRecommendationColor(type: K8sRecommendation["type"]): string {
  switch (type) {
    case "downsize":
      return "#00BFFF"
    case "terminate":
      return "#FF4444"
    case "right-size":
      return "#00FF88"
    case "schedule":
      return "#A855F7"
  }
}

// --- Custom tooltip ---

interface NamespaceTooltipProps {
  active?: boolean
  payload?: Array<{ value: number; payload: K8sNamespaceCost }>
}

function NamespaceTooltip({ active, payload }: NamespaceTooltipProps) {
  if (!active || !payload || !payload.length) return null
  const ns = payload[0].payload
  const cpuUtil = ((ns.cpuUsed / ns.cpuRequested) * 100).toFixed(0)
  const memUtil = ((ns.memUsed / ns.memRequested) * 100).toFixed(0)

  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-mono font-medium text-foreground">
        {ns.namespace}: {formatCurrency(ns.cost)}/mo
      </p>
      <p className="font-mono text-[10px] text-muted-foreground">
        CPU: {ns.cpuUsed}/{ns.cpuRequested} cores ({cpuUtil}% utilized)
      </p>
      <p className="font-mono text-[10px] text-muted-foreground">
        Mem: {ns.memUsed}/{ns.memRequested} GB ({memUtil}% utilized)
      </p>
    </div>
  )
}

// --- Idle resource waste indicator ---

function IdleWasteIndicator() {
  const totalCpuRequested = K8S_NAMESPACE_COSTS.reduce(
    (sum, ns) => sum + ns.cpuRequested,
    0
  )
  const totalCpuUsed = K8S_NAMESPACE_COSTS.reduce(
    (sum, ns) => sum + ns.cpuUsed,
    0
  )
  const totalMemRequested = K8S_NAMESPACE_COSTS.reduce(
    (sum, ns) => sum + ns.memRequested,
    0
  )
  const totalMemUsed = K8S_NAMESPACE_COSTS.reduce(
    (sum, ns) => sum + ns.memUsed,
    0
  )

  const cpuWaste = (
    ((totalCpuRequested - totalCpuUsed) / totalCpuRequested) *
    100
  ).toFixed(0)
  const memWaste = (
    ((totalMemRequested - totalMemUsed) / totalMemRequested) *
    100
  ).toFixed(0)

  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="rounded-lg border border-border/50 p-3 text-center">
        <p className="font-mono text-[10px] text-muted-foreground">
          CPU Waste
        </p>
        <p
          className="font-mono text-xl font-bold"
          style={{ color: getWasteColor(Number(cpuWaste)) }}
        >
          {cpuWaste}%
        </p>
        <p className="font-mono text-[9px] text-muted-foreground">
          {totalCpuUsed}/{totalCpuRequested} cores used
        </p>
      </div>
      <div className="rounded-lg border border-border/50 p-3 text-center">
        <p className="font-mono text-[10px] text-muted-foreground">
          Memory Waste
        </p>
        <p
          className="font-mono text-xl font-bold"
          style={{ color: getWasteColor(Number(memWaste)) }}
        >
          {memWaste}%
        </p>
        <p className="font-mono text-[9px] text-muted-foreground">
          {totalMemUsed}/{totalMemRequested} GB used
        </p>
      </div>
    </div>
  )
}

// --- Main component ---

export function KubernetesCost() {
  const totalSavings = K8S_RECOMMENDATIONS.reduce(
    (sum, r) => sum + r.estimatedSavings,
    0
  )

  return (
    <Card size="sm">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-muted-foreground">
          <Server className="size-4 text-primary" />
          Kubernetes Cost Allocation
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-3">
        <Tabs defaultValue="namespaces">
          <TabsList variant="line" className="mb-3">
            <TabsTrigger value="namespaces" className="font-mono text-[11px]">
              Namespaces
            </TabsTrigger>
            <TabsTrigger value="pods" className="font-mono text-[11px]">
              Pods
            </TabsTrigger>
            <TabsTrigger
              value="recommendations"
              className="font-mono text-[11px]"
            >
              Optimize
            </TabsTrigger>
          </TabsList>

          {/* Namespaces tab */}
          <TabsContent value="namespaces">
            <div className="space-y-4">
              {/* Namespace bar chart */}
              <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={K8S_NAMESPACE_COSTS}
                    margin={{ top: 4, right: 4, left: -10, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(255,255,255,0.05)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="namespace"
                      tick={{ fontSize: 10, fill: "rgba(255,255,255,0.6)" }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val: number) => `$${val}`}
                    />
                    <RechartsTooltip content={<NamespaceTooltip />} />
                    <Bar dataKey="cost" radius={[4, 4, 0, 0]} barSize={40}>
                      {K8S_NAMESPACE_COSTS.map((entry) => (
                        <Cell key={entry.namespace} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Idle waste indicator */}
              <IdleWasteIndicator />
            </div>
          </TabsContent>

          {/* Pods tab */}
          <TabsContent value="pods">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="font-mono text-[10px]">Pod</TableHead>
                  <TableHead className="font-mono text-[10px]">
                    Namespace
                  </TableHead>
                  <TableHead className="font-mono text-[10px]">
                    Deployment
                  </TableHead>
                  <TableHead className="text-right font-mono text-[10px]">
                    $/day
                  </TableHead>
                  <TableHead className="text-right font-mono text-[10px]">
                    CPU Waste
                  </TableHead>
                  <TableHead className="text-right font-mono text-[10px]">
                    Mem Waste
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {K8S_POD_COSTS.map((pod) => (
                  <TableRow key={pod.id}>
                    <TableCell className="font-mono text-[11px] text-foreground">
                      {pod.pod}
                    </TableCell>
                    <TableCell className="font-mono text-[11px] text-muted-foreground">
                      {pod.namespace}
                    </TableCell>
                    <TableCell className="font-mono text-[11px] text-muted-foreground">
                      {pod.deployment}
                    </TableCell>
                    <TableCell className="text-right font-mono text-[11px] font-medium text-foreground">
                      ${pod.costPerDay.toFixed(2)}
                    </TableCell>
                    <TableCell className="text-right">
                      <span
                        className="font-mono text-[11px] font-medium"
                        style={{ color: getWasteColor(pod.cpuWaste) }}
                      >
                        {pod.cpuWaste}%
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <span
                        className="font-mono text-[11px] font-medium"
                        style={{ color: getWasteColor(pod.memWaste) }}
                      >
                        {pod.memWaste}%
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TabsContent>

          {/* Recommendations tab */}
          <TabsContent value="recommendations">
            <div className="space-y-3">
              {/* Total savings summary */}
              <div className="rounded-lg border border-[#00FF8830] bg-[#00FF8808] p-3 text-center">
                <p className="font-mono text-[10px] text-muted-foreground">
                  Total Potential Savings
                </p>
                <p className="font-mono text-2xl font-bold text-[#00FF88]">
                  {formatCurrency(totalSavings)}/mo
                </p>
              </div>

              {/* Recommendation cards */}
              {K8S_RECOMMENDATIONS.map((rec) => {
                const Icon = getRecommendationIcon(rec.type)
                const color = getRecommendationColor(rec.type)

                return (
                  <div
                    key={rec.id}
                    className="flex items-start gap-3 rounded-lg border border-border/50 p-3"
                  >
                    <div
                      className="flex size-7 shrink-0 items-center justify-center rounded-md"
                      style={{ backgroundColor: `${color}15` }}
                    >
                      <Icon className="size-3.5" style={{ color }} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-medium text-foreground">
                          {rec.resource}
                        </span>
                        <Badge
                          variant="outline"
                          className="font-mono text-[8px]"
                          style={{ borderColor: `${color}40`, color }}
                        >
                          {rec.type}
                        </Badge>
                        <span className="font-mono text-[10px] text-muted-foreground">
                          {rec.namespace}
                        </span>
                      </div>
                      <p className="mt-1 font-mono text-[10px] leading-relaxed text-muted-foreground">
                        {rec.description}
                      </p>
                      <p className="mt-1 font-mono text-[10px] font-medium text-[#00FF88]">
                        Est. savings: {formatCurrency(rec.estimatedSavings)}/mo
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
