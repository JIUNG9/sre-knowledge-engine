"use client"

import * as React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  AlertTriangle,
  ExternalLink,
  TrendingUp,
} from "lucide-react"
import { cn } from "@/lib/utils"
import {
  COST_ANOMALIES,
  type CostAnomaly,
  type AnomalySeverity,
} from "@/lib/mock-data/finops"

// --- Helpers ---

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value)
}

function getSeverityConfig(severity: AnomalySeverity) {
  switch (severity) {
    case "high":
      return {
        label: "High",
        color: "#FF4444",
        bgColor: "rgba(255,68,68,0.1)",
        borderColor: "rgba(255,68,68,0.3)",
        glowColor: "rgba(255,68,68,0.15)",
      }
    case "medium":
      return {
        label: "Medium",
        color: "#FFB020",
        bgColor: "rgba(255,176,32,0.1)",
        borderColor: "rgba(255,176,32,0.3)",
        glowColor: "rgba(255,176,32,0.1)",
      }
    case "low":
      return {
        label: "Low",
        color: "#FFD93D",
        bgColor: "rgba(255,217,61,0.1)",
        borderColor: "rgba(255,217,61,0.3)",
        glowColor: "rgba(255,217,61,0.08)",
      }
  }
}

function formatDetectedTime(iso: string): string {
  const d = new Date(iso)
  const month = d.toLocaleString("en-US", { month: "short" })
  const day = d.getDate()
  const hours = d.getHours().toString().padStart(2, "0")
  const mins = d.getMinutes().toString().padStart(2, "0")
  return `${month} ${day}, ${hours}:${mins} UTC`
}

// --- Single anomaly card ---

function AnomalyCard({ anomaly }: { anomaly: CostAnomaly }) {
  const severity = getSeverityConfig(anomaly.severity)

  return (
    <Card
      size="sm"
      className="relative overflow-hidden transition-all"
      style={{
        boxShadow: `0 0 20px ${severity.glowColor}, 0 0 6px ${severity.glowColor}`,
        borderColor: severity.borderColor,
      }}
    >
      <CardContent className="space-y-3 pt-0">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertTriangle
              className="size-4 shrink-0"
              style={{ color: severity.color }}
            />
            <span className="font-mono text-sm font-medium text-foreground">
              {anomaly.service}
            </span>
          </div>
          <Badge
            variant="outline"
            className="font-mono text-xs"
            style={{
              borderColor: severity.borderColor,
              color: severity.color,
              backgroundColor: severity.bgColor,
            }}
          >
            {severity.label}
          </Badge>
        </div>

        {/* Cost comparison */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <p className="font-mono text-xs text-muted-foreground">
              Expected
            </p>
            <p className="font-mono text-lg font-medium text-foreground">
              {formatCurrency(anomaly.expected)}
            </p>
          </div>
          <div>
            <p className="font-mono text-xs text-muted-foreground">
              Actual
            </p>
            <p
              className="font-mono text-lg font-bold"
              style={{ color: severity.color }}
            >
              {formatCurrency(anomaly.actual)}
            </p>
          </div>
          <div>
            <p className="font-mono text-xs text-muted-foreground">
              Deviation
            </p>
            <p className="flex items-center gap-1 font-mono text-lg font-bold text-[#FF4444]">
              <TrendingUp className="size-3" />
              +{anomaly.deviation.toFixed(1)}%
            </p>
          </div>
        </div>

        {/* Description */}
        <p className="font-mono text-xs leading-relaxed text-muted-foreground">
          {anomaly.description}
        </p>

        {/* Footer */}
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs text-muted-foreground/60">
            Detected: {formatDetectedTime(anomaly.detectedAt)}
          </span>
          <Button
            variant="ghost"
            size="xs"
            className="gap-1 font-mono text-xs"
            style={{ color: severity.color }}
          >
            <ExternalLink className="size-3" />
            Investigate
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// --- Main component ---

export function CostAnomalyCards() {
  if (COST_ANOMALIES.length === 0) {
    return (
      <Card size="sm">
        <CardContent className="flex flex-col items-center justify-center gap-2 py-8 text-muted-foreground/50">
          <AlertTriangle className="size-6" />
          <span className="font-mono text-xs">No anomalies detected</span>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      <h2 className="flex items-center gap-2 font-mono text-lg font-medium text-muted-foreground">
        <AlertTriangle className="size-5 text-[#FFB020]" />
        Cost Anomalies
        <Badge
          variant="outline"
          className="font-mono text-xs"
          style={{
            borderColor: "rgba(255,176,32,0.3)",
            color: "#FFB020",
          }}
        >
          {COST_ANOMALIES.length}
        </Badge>
      </h2>
      <div className="grid gap-5 md:grid-cols-2">
        {COST_ANOMALIES.map((anomaly) => (
          <AnomalyCard key={anomaly.id} anomaly={anomaly} />
        ))}
      </div>
    </div>
  )
}
