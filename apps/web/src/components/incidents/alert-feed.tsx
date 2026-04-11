"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import {
  MOCK_ALERT_FEED,
  type AlertFeedItem,
  type AlertSource,
  type IncidentSeverity,
} from "@/lib/mock-data/incidents"
import {
  AlertTriangle,
  Bell,
  ExternalLink,
  Link as LinkIcon,
  Plus,
  Radio,
} from "lucide-react"

// ---- Config helpers ----

function getSourceConfig(source: AlertSource) {
  switch (source) {
    case "signoz":
      return { label: "SigNoz", color: "#E5484D", abbr: "SZ" }
    case "datadog":
      return { label: "Datadog", color: "#632CA6", abbr: "DD" }
    case "prometheus":
      return { label: "Prom", color: "#E6522C", abbr: "PM" }
  }
}

function getSeverityColor(severity: IncidentSeverity): string {
  switch (severity) {
    case "critical":
      return "#FF4444"
    case "high":
      return "#FF8C00"
    case "medium":
      return "#FFB020"
    case "low":
      return "#00B8FF"
  }
}

function formatTimeAgo(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)

  if (diffMin < 1) return "now"
  if (diffMin < 60) return `${diffMin}m`
  const diffHours = Math.floor(diffMin / 60)
  if (diffHours < 24) return `${diffHours}h`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d`
}

// ---- Alert Item ----

interface AlertItemProps {
  alert: AlertFeedItem
  onCreateIncident?: (alert: AlertFeedItem) => void
}

function AlertItem({ alert, onCreateIncident }: AlertItemProps) {
  const srcConfig = getSourceConfig(alert.source)
  const sevColor = getSeverityColor(alert.severity)
  const isLinked = !!alert.incidentId

  return (
    <div
      className={cn(
        "group relative rounded-md px-4 py-3 transition-colors hover:bg-surface-hover",
        alert.severity === "critical" && "bg-[#FF4444]/[0.03]"
      )}
    >
      <div className="flex items-start gap-3">
        {/* Severity dot */}
        <span
          className={cn(
            "mt-1.5 inline-block size-3 shrink-0 rounded-full",
            alert.severity === "critical" && "animate-pulse"
          )}
          style={{ backgroundColor: sevColor }}
        />

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {/* Source badge */}
            <span
              className="rounded-sm px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase"
              style={{
                backgroundColor: `${srcConfig.color}15`,
                color: srcConfig.color,
              }}
            >
              {srcConfig.abbr}
            </span>
            {/* Time */}
            <span className="font-mono text-xs text-muted-foreground">
              {formatTimeAgo(alert.firedAt)}
            </span>
            {/* Linked indicator */}
            {isLinked && (
              <span className="font-mono text-xs text-primary">
                <LinkIcon className="inline size-3" /> {alert.incidentId}
              </span>
            )}
          </div>
          <p className="mt-1 truncate font-mono text-sm text-foreground">
            {alert.title}
          </p>
          <p className="font-mono text-xs text-muted-foreground">
            {alert.service}
          </p>
        </div>

        {/* Create incident button - shown on hover when not linked */}
        {!isLinked && (
          <Button
            variant="ghost"
            size="icon-xs"
            className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
            onClick={() => onCreateIncident?.(alert)}
            title="Create incident from alert"
          >
            <Plus className="size-3" />
          </Button>
        )}
      </div>
    </div>
  )
}

// ---- Main Feed ----

interface AlertFeedProps {
  className?: string
}

export function AlertFeed({ className }: AlertFeedProps) {
  // Group by dedupKey, keep only latest per group
  const dedupedMap = new Map<string, AlertFeedItem>()
  for (const alert of MOCK_ALERT_FEED) {
    const existing = dedupedMap.get(alert.dedupKey)
    if (!existing || new Date(alert.firedAt) > new Date(existing.firedAt)) {
      dedupedMap.set(alert.dedupKey, alert)
    }
  }
  const alerts = Array.from(dedupedMap.values()).sort(
    (a, b) => new Date(b.firedAt).getTime() - new Date(a.firedAt).getTime()
  )

  const unlinkedCount = alerts.filter((a) => !a.incidentId).length

  return (
    <div
      className={cn(
        "flex flex-col rounded-lg border border-border bg-card",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Radio className="size-4 text-primary" />
            <span className="absolute -top-0.5 -right-0.5 size-2 animate-pulse rounded-full bg-primary" />
          </div>
          <span className="font-mono text-sm font-medium text-foreground">
            Alert Feed
          </span>
        </div>
        {unlinkedCount > 0 && (
          <Badge variant="outline" className="px-2 py-0.5 font-mono text-xs">
            {unlinkedCount} unlinked
          </Badge>
        )}
      </div>

      {/* Scanning animation bar */}
      <div className="relative h-px w-full overflow-hidden bg-border">
        <div className="absolute inset-y-0 left-0 w-1/3 animate-scan bg-gradient-to-r from-transparent via-primary/60 to-transparent" />
      </div>

      {/* Alert list */}
      <ScrollArea className="flex-1">
        <div className="divide-y divide-border/50">
          {alerts.map((alert) => (
            <AlertItem key={alert.id} alert={alert} />
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
