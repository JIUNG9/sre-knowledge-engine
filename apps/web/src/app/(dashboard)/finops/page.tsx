"use client"

import * as React from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { CostOverview } from "@/components/finops/cost-overview"
import { CostByService } from "@/components/finops/cost-by-service"
import { CostAnomalyCards } from "@/components/finops/cost-anomaly-card"
import { BudgetTracker } from "@/components/finops/budget-tracker"
import { KubernetesCost } from "@/components/finops/kubernetes-cost"
import { CostTrendChart } from "@/components/finops/cost-trend-chart"
import { BudgetManagement } from "@/components/finops/budget-management"
import { RightsizingRecommendations } from "@/components/finops/rightsizing-recommendations"
import { DollarSign } from "lucide-react"

export default function FinOpsPage() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-border px-8 py-5">
        <DollarSign className="size-6 text-primary" />
        <h1 className="font-heading text-2xl font-semibold text-foreground text-glow">
          FinOps Dashboard
        </h1>
        <span className="font-mono text-sm text-muted-foreground">
          Cloud Cost Management
        </span>
      </div>

      {/* Tabs navigation */}
      <Tabs defaultValue="overview" className="flex flex-1 flex-col overflow-hidden">
        <div className="border-b border-border px-8 pt-2">
          <TabsList variant="line">
            <TabsTrigger value="overview" className="px-5 py-3 font-mono text-base">
              Overview
            </TabsTrigger>
            <TabsTrigger value="budgets" className="px-5 py-3 font-mono text-base">
              Budgets
            </TabsTrigger>
            <TabsTrigger value="rightsizing" className="px-5 py-3 font-mono text-base">
              Right-Sizing
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Scrollable content */}
        <ScrollArea className="flex-1">
          <TabsContent value="overview">
            <div className="space-y-6 p-8">
              {/* Cost Overview Cards + Charts */}
              <CostOverview />

              {/* Anomalies */}
              <CostAnomalyCards />

              {/* Two-column layout: Budget + K8s */}
              <div className="grid gap-6 xl:grid-cols-2">
                <BudgetTracker />
                <KubernetesCost />
              </div>

              {/* Cost Trend Chart */}
              <CostTrendChart />

              {/* Service Breakdown Table */}
              <CostByService />
            </div>
          </TabsContent>

          <TabsContent value="budgets">
            <div className="p-8">
              <BudgetManagement />
            </div>
          </TabsContent>

          <TabsContent value="rightsizing">
            <div className="p-8">
              <RightsizingRecommendations />
            </div>
          </TabsContent>
        </ScrollArea>
      </Tabs>
    </div>
  )
}
