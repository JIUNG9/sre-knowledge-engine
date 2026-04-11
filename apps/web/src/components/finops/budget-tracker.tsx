"use client"

import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, Wallet } from "lucide-react"
import { cn } from "@/lib/utils"
import { TEAM_BUDGETS, type TeamBudget } from "@/lib/mock-data/finops"

// --- Helpers ---

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

function getUsageColor(percent: number): string {
  if (percent >= 90) return "#FF4444"
  if (percent >= 70) return "#FFB020"
  return "#00FF88"
}

function getProjectedColor(percent: number): string {
  if (percent > 100) return "#FF4444"
  if (percent > 85) return "#FFB020"
  return "#00FF88"
}

// --- Budget row ---

function BudgetRow({ budget }: { budget: TeamBudget }) {
  const usageColor = getUsageColor(budget.usagePercent)
  const projectedColor = getProjectedColor(budget.projectedPercent)
  const isOverBudget = budget.projectedPercent > 100

  return (
    <div className="space-y-3 rounded-lg border border-border/50 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-medium text-foreground">
            {budget.team}
          </span>
          {isOverBudget && (
            <Badge
              variant="outline"
              className="gap-1 font-mono text-xs"
              style={{
                borderColor: "rgba(255,68,68,0.3)",
                color: "#FF4444",
                backgroundColor: "rgba(255,68,68,0.1)",
              }}
            >
              <AlertTriangle className="size-3" />
              Over Budget
            </Badge>
          )}
        </div>
        <span className="font-mono text-sm text-muted-foreground">
          {formatCurrency(budget.currentSpend)} / {formatCurrency(budget.budget)}
        </span>
      </div>

      {/* Progress bar with projected overlay */}
      <div className="relative">
        {/* Background track */}
        <div className="h-4 overflow-hidden rounded-full bg-muted">
          {/* Current spend bar */}
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(budget.usagePercent, 100)}%`,
              backgroundColor: usageColor,
              boxShadow: `0 0 8px ${usageColor}30`,
            }}
          />
        </div>

        {/* Projected marker (dotted line) */}
        {budget.projectedPercent <= 150 && (
          <div
            className="absolute top-0 h-4 border-r-2 border-dashed"
            style={{
              left: `${Math.min(budget.projectedPercent, 100)}%`,
              borderColor: projectedColor,
            }}
          >
            <div
              className="absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap font-mono text-[9px]"
              style={{ color: projectedColor }}
            >
              Proj: {budget.projectedPercent.toFixed(0)}%
            </div>
          </div>
        )}

        {/* 100% budget line marker */}
        <div
          className="absolute top-0 h-4 border-r border-dashed border-muted-foreground/30"
          style={{ left: "100%" }}
        />
      </div>

      {/* Footer stats */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-muted-foreground">
            Used:{" "}
            <span style={{ color: usageColor }}>{budget.usagePercent}%</span>
          </span>
          <span className="font-mono text-xs text-muted-foreground">
            Projected:{" "}
            <span style={{ color: projectedColor }}>
              {formatCurrency(budget.projected)}
            </span>
          </span>
        </div>
        <span className="font-mono text-xs text-muted-foreground/60">
          Budget: {formatCurrency(budget.budget)}
        </span>
      </div>
    </div>
  )
}

// --- Main component ---

export function BudgetTracker() {
  const overBudgetCount = TEAM_BUDGETS.filter(
    (b) => b.projectedPercent > 100
  ).length

  return (
    <Card size="sm">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-muted-foreground">
          <Wallet className="size-4 text-primary" />
          Budget Tracker
          {overBudgetCount > 0 && (
            <Badge
              variant="outline"
              className="font-mono text-xs"
              style={{
                borderColor: "rgba(255,68,68,0.3)",
                color: "#FF4444",
              }}
            >
              {overBudgetCount} projected over
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 p-6">
        {TEAM_BUDGETS.map((budget) => (
          <BudgetRow key={budget.id} budget={budget} />
        ))}
      </CardContent>
    </Card>
  )
}
