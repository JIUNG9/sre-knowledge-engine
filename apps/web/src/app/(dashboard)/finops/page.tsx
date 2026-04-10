"use client"

import * as React from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { CostOverview } from "@/components/finops/cost-overview"
import { CostByService } from "@/components/finops/cost-by-service"
import { CostAnomalyCards } from "@/components/finops/cost-anomaly-card"
import { BudgetTracker } from "@/components/finops/budget-tracker"
import { KubernetesCost } from "@/components/finops/kubernetes-cost"
import { CostTrendChart } from "@/components/finops/cost-trend-chart"
import { DollarSign } from "lucide-react"

export default function FinOpsPage() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-border px-4 py-3">
        <DollarSign className="size-4 text-primary" />
        <h1 className="font-heading text-sm font-semibold text-foreground text-glow">
          FinOps Dashboard
        </h1>
        <span className="font-mono text-xs text-muted-foreground">
          Cloud Cost Management
        </span>
      </div>

      {/* Scrollable content */}
      <ScrollArea className="flex-1">
        <div className="space-y-6 p-4">
          {/* Cost Overview Cards + Charts */}
          <CostOverview />

          {/* Anomalies */}
          <CostAnomalyCards />

          {/* Two-column layout: Budget + K8s */}
          <div className="grid gap-4 xl:grid-cols-2">
            <BudgetTracker />
            <KubernetesCost />
          </div>

          {/* Cost Trend Chart */}
          <CostTrendChart />

          {/* Service Breakdown Table */}
          <CostByService />
        </div>
      </ScrollArea>
    </div>
  )
}
