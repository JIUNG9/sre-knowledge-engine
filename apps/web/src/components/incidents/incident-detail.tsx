"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { IncidentTimeline } from "@/components/incidents/incident-timeline"
import type { Incident, IncidentSeverity, IncidentStatus, AlertSource } from "@/lib/mock-data/incidents"
import {
  AlertTriangle,
  ArrowUpCircle,
  Clock,
  Edit,
  ExternalLink,
  Server,
  UserCircle,
} from "lucide-react"

// ---- Severity config ----

function getSeverityConfig(severity: IncidentSeverity) {
  switch (severity) {
    case "critical":
      return { label: "CRITICAL", color: "#FF4444", bg: "bg-[#FF4444]/10", border: "border-[#FF4444]/30" }
    case "high":
      return { label: "HIGH", color: "#FF8C00", bg: "bg-[#FF8C00]/10", border: "border-[#FF8C00]/30" }
    case "medium":
      return { label: "MEDIUM", color: "#FFB020", bg: "bg-[#FFB020]/10", border: "border-[#FFB020]/30" }
    case "low":
      return { label: "LOW", color: "#00B8FF", bg: "bg-[#00B8FF]/10", border: "border-[#00B8FF]/30" }
  }
}

function getStatusConfig(status: IncidentStatus) {
  switch (status) {
    case "open":
      return { label: "Open", color: "#FF4444" }
    case "investigating":
      return { label: "Investigating", color: "#FF8C00" }
    case "identified":
      return { label: "Identified", color: "#FFB020" }
    case "monitoring":
      return { label: "Monitoring", color: "#00B8FF" }
    case "resolved":
      return { label: "Resolved", color: "#00FF88" }
  }
}

function getSourceConfig(source: AlertSource) {
  switch (source) {
    case "signoz":
      return { label: "SigNoz", color: "#E5484D" }
    case "datadog":
      return { label: "Datadog", color: "#632CA6" }
    case "prometheus":
      return { label: "Prometheus", color: "#E6522C" }
  }
}

function formatDuration(iso: string): string {
  const created = new Date(iso).getTime()
  const now = Date.now()
  const diffMs = now - created
  const mins = Math.floor(diffMs / 60000)
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ${mins % 60}m`
  const days = Math.floor(hours / 24)
  return `${days}d ${hours % 24}h`
}

// ---- Detail Panel ----

interface IncidentDetailProps {
  incident: Incident
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function IncidentDetail({
  incident,
  open,
  onOpenChange,
}: IncidentDetailProps) {
  const sevConfig = getSeverityConfig(incident.severity)
  const statusConfig = getStatusConfig(incident.status)
  const isResolved = incident.status === "resolved"

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-lg md:max-w-xl lg:max-w-2xl"
      >
        <SheetHeader className="pr-8">
          <div className="flex flex-wrap items-center gap-2">
            {/* Severity badge */}
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 font-mono text-[10px] font-bold",
                sevConfig.bg,
                sevConfig.border
              )}
              style={{ color: sevConfig.color }}
            >
              {incident.severity === "critical" && (
                <span className="inline-block size-1.5 animate-pulse rounded-full bg-[#FF4444]" />
              )}
              {sevConfig.label}
            </span>
            {/* Status chip */}
            <span
              className="rounded-sm px-1.5 py-0.5 font-mono text-[10px] font-medium"
              style={{
                backgroundColor: `${statusConfig.color}15`,
                color: statusConfig.color,
              }}
            >
              {statusConfig.label}
            </span>
            {/* ID */}
            <span className="font-mono text-[10px] text-muted-foreground">
              {incident.id}
            </span>
          </div>
          <SheetTitle className="text-left">{incident.title}</SheetTitle>
          <SheetDescription className="text-left">
            {incident.description}
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="flex-1 px-4">
          <div className="space-y-5 pb-4">
            {/* Meta row */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div>
                <p className="font-mono text-[10px] text-muted-foreground">
                  Service
                </p>
                <p className="font-mono text-xs font-medium text-foreground">
                  {incident.service}
                </p>
              </div>
              <div>
                <p className="font-mono text-[10px] text-muted-foreground">
                  Assignee
                </p>
                <p className="font-mono text-xs font-medium text-foreground">
                  {incident.assignee}
                </p>
              </div>
              <div>
                <p className="font-mono text-[10px] text-muted-foreground">
                  Duration
                </p>
                <p className="font-mono text-xs font-medium text-foreground">
                  {isResolved && incident.resolvedAt
                    ? formatDuration(incident.createdAt)
                    : formatDuration(incident.createdAt)}
                </p>
              </div>
              <div>
                <p className="font-mono text-[10px] text-muted-foreground">
                  Updated
                </p>
                <p className="font-mono text-xs font-medium text-foreground">
                  {formatDuration(incident.updatedAt)} ago
                </p>
              </div>
            </div>

            {/* Action buttons */}
            {!isResolved && (
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" className="font-mono text-[11px]">
                  <Edit className="size-3" />
                  Change Status
                </Button>
                <Button variant="outline" size="sm" className="font-mono text-[11px]">
                  <UserCircle className="size-3" />
                  Assign
                </Button>
                <Button variant="outline" size="sm" className="font-mono text-[11px]">
                  <Clock className="size-3" />
                  Add Note
                </Button>
                <Button variant="destructive" size="sm" className="font-mono text-[11px]">
                  <ArrowUpCircle className="size-3" />
                  Escalate
                </Button>
              </div>
            )}

            <Separator />

            {/* Affected services */}
            {incident.affectedServices.length > 0 && (
              <div>
                <h3 className="mb-2 flex items-center gap-1.5 font-mono text-xs font-medium text-foreground">
                  <Server className="size-3" />
                  Affected Services
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {incident.affectedServices.map((svc) => (
                    <Badge
                      key={svc}
                      variant="outline"
                      className="font-mono text-[10px]"
                    >
                      {svc}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Related alerts */}
            {incident.relatedAlerts.length > 0 && (
              <div>
                <h3 className="mb-2 flex items-center gap-1.5 font-mono text-xs font-medium text-foreground">
                  <AlertTriangle className="size-3" />
                  Related Alerts ({incident.relatedAlerts.length})
                </h3>
                <div className="space-y-1.5">
                  {incident.relatedAlerts.map((alert) => {
                    const srcConfig = getSourceConfig(alert.source)
                    const alertSevConfig = getSeverityConfig(alert.severity)
                    return (
                      <div
                        key={alert.id}
                        className="flex items-center gap-2 rounded-md bg-muted/50 px-2.5 py-1.5"
                      >
                        <span
                          className="inline-block size-1.5 rounded-full"
                          style={{ backgroundColor: alertSevConfig.color }}
                        />
                        <span
                          className="rounded-sm px-1 py-0.5 font-mono text-[9px] font-medium"
                          style={{
                            backgroundColor: `${srcConfig.color}15`,
                            color: srcConfig.color,
                          }}
                        >
                          {srcConfig.label}
                        </span>
                        <span className="flex-1 truncate font-mono text-[11px] text-foreground">
                          {alert.title}
                        </span>
                        <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
                          {alert.service}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            <Separator />

            {/* Timeline */}
            <div>
              <h3 className="mb-3 flex items-center gap-1.5 font-mono text-xs font-medium text-foreground">
                <Clock className="size-3" />
                Timeline
              </h3>
              <IncidentTimeline
                events={incident.timeline}
                showAddNote={!isResolved}
              />
            </div>
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
