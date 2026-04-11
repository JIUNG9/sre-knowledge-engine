"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { IncidentDetail } from "@/components/incidents/incident-detail"
import { IncidentCreate } from "@/components/incidents/incident-create"
import { IncidentStats } from "@/components/incidents/incident-stats"
import { AlertFeed } from "@/components/incidents/alert-feed"
import {
  MOCK_INCIDENTS,
  SEVERITY_ORDER,
  ASSIGNEES,
  INCIDENT_SERVICES,
  type Incident,
  type IncidentSeverity,
  type IncidentStatus,
} from "@/lib/mock-data/incidents"
import { AccountFilter } from "@/components/account-filter"
import {
  AlertTriangle,
  ArrowUpDown,
  Filter,
  LayoutGrid,
  LayoutList,
  UserCircle,
} from "lucide-react"
import {
  SERVICE_TO_ACCOUNT,
} from "@/lib/stores/account-store"

// ---- Config helpers ----

function getSeverityConfig(severity: IncidentSeverity) {
  switch (severity) {
    case "critical":
      return { label: "CRITICAL", color: "#FF4444" }
    case "high":
      return { label: "HIGH", color: "#FF8C00" }
    case "medium":
      return { label: "MEDIUM", color: "#FFB020" }
    case "low":
      return { label: "LOW", color: "#00B8FF" }
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

function formatDuration(createdAt: string, resolvedAt?: string): string {
  const start = new Date(createdAt).getTime()
  const end = resolvedAt ? new Date(resolvedAt).getTime() : Date.now()
  const diffMs = end - start
  const mins = Math.floor(diffMs / 60000)
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ${mins % 60}m`
  const days = Math.floor(hours / 24)
  return `${days}d ${hours % 24}h`
}

function formatUpdated(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return "just now"
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHours = Math.floor(diffMin / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

// ---- Severity Badge ----

function SeverityBadge({ severity }: { severity: IncidentSeverity }) {
  const config = getSeverityConfig(severity)
  return (
    <span
      className={cn(
        "inline-flex h-8 w-20 items-center justify-center gap-1.5 rounded-sm border px-3 py-1.5 font-mono text-xs font-bold"
      )}
      style={{
        borderColor: `${config.color}30`,
        backgroundColor: `${config.color}10`,
        color: config.color,
      }}
    >
      {severity === "critical" && (
        <span className="inline-block size-3 animate-pulse rounded-full bg-[#FF4444]" />
      )}
      {config.label}
    </span>
  )
}

// ---- Status Chip ----

function StatusChip({ status }: { status: IncidentStatus }) {
  const config = getStatusConfig(status)
  return (
    <span
      className="rounded-sm px-1.5 py-0.5 font-mono text-xs font-medium transition-colors"
      style={{
        backgroundColor: `${config.color}15`,
        color: config.color,
      }}
    >
      {config.label}
    </span>
  )
}

// ---- Sort/Filter types ----

type SortOption = "severity" | "created" | "updated"
type StatusFilterValue = "all" | IncidentStatus
type SeverityFilterValue = "all" | IncidentSeverity
type ViewMode = "table" | "cards"

// ---- Incident Card (for card view) ----

function IncidentCard({
  incident,
  onClick,
}: {
  incident: Incident
  onClick: () => void
}) {
  const isCritical = incident.severity === "critical"

  return (
    <Card
      className={cn(
        "cursor-pointer transition-all hover:bg-surface-hover",
        isCritical && "ring-1 ring-[#FF4444]/30",
        isCritical && "shadow-[0_0_30px_rgba(255,68,68,0.12)]"
      )}
      onClick={onClick}
    >
      <CardContent className="grid gap-3 p-6">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <SeverityBadge severity={incident.severity} />
            <StatusChip status={incident.status} />
          </div>
          <span className="shrink-0 font-mono text-sm text-muted-foreground">
            {incident.id}
          </span>
        </div>
        <p className="truncate font-mono text-sm font-medium text-foreground">
          {incident.title}
        </p>
        <div className="flex flex-wrap items-center gap-2 font-mono text-sm text-muted-foreground">
          <span>{incident.service}</span>
          <span className="text-border">|</span>
          <span className="flex items-center gap-1">
            <UserCircle className="size-3" />
            {incident.assignee}
          </span>
          <span className="text-border">|</span>
          <span>{formatDuration(incident.createdAt, incident.resolvedAt)}</span>
          <span className="ml-auto text-sm">{formatUpdated(incident.updatedAt)}</span>
        </div>
      </CardContent>
    </Card>
  )
}

// ---- Main List ----

export function IncidentList() {
  const [accountFilter, setAccountFilter] = React.useState<string | null>(null)
  const [viewMode, setViewMode] = React.useState<ViewMode>("table")
  const [sortBy, setSortBy] = React.useState<SortOption>("severity")
  const [statusFilter, setStatusFilter] = React.useState<StatusFilterValue>("all")
  const [severityFilter, setSeverityFilter] = React.useState<SeverityFilterValue>("all")
  const [serviceFilter, setServiceFilter] = React.useState<string>("all")
  const [assigneeFilter, setAssigneeFilter] = React.useState<string>("all")
  const [selectedIncident, setSelectedIncident] = React.useState<Incident | null>(null)

  // Filter
  let filtered = MOCK_INCIDENTS.filter((inc) => {
    if (accountFilter && SERVICE_TO_ACCOUNT[inc.service] !== accountFilter) return false
    if (statusFilter !== "all" && inc.status !== statusFilter) return false
    if (severityFilter !== "all" && inc.severity !== severityFilter) return false
    if (serviceFilter !== "all" && inc.service !== serviceFilter) return false
    if (assigneeFilter !== "all" && inc.assignee !== assigneeFilter) return false
    return true
  })

  // Sort
  filtered = [...filtered].sort((a, b) => {
    switch (sortBy) {
      case "severity":
        return SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]
      case "created":
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      case "updated":
        return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    }
  })

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border px-8 py-5">
        <div className="flex items-center gap-3">
          <h1 className="font-heading text-2xl font-semibold text-foreground text-glow">
            Incident Management
          </h1>
        </div>
        <div className="flex items-center gap-3">
          {/* View toggle */}
          <div className="flex items-center rounded-md bg-muted p-1">
            <Button
              variant={viewMode === "table" ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setViewMode("table")}
            >
              <LayoutList className="size-4" />
            </Button>
            <Button
              variant={viewMode === "cards" ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setViewMode("cards")}
            >
              <LayoutGrid className="size-4" />
            </Button>
          </div>
          <IncidentCreate />
        </div>
      </div>

      {/* Content with optional alert feed sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {/* Main content area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <ScrollArea className="flex-1">
            <div className="space-y-6 p-8">
              {/* Stats */}
              <IncidentStats />

              {/* Filter bar */}
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Filter className="size-4" />
                  <span className="font-mono text-sm">Filters:</span>
                </div>

                {/* Service Account */}
                <AccountFilter value={accountFilter} onChange={setAccountFilter} />

                {/* Status */}
                <Select
                  value={statusFilter}
                  onValueChange={(v) => {
                    if (v) setStatusFilter(v as StatusFilterValue)
                  }}
                >
                  <SelectTrigger className="h-10 font-mono text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="open">Open</SelectItem>
                    <SelectItem value="investigating">Investigating</SelectItem>
                    <SelectItem value="identified">Identified</SelectItem>
                    <SelectItem value="monitoring">Monitoring</SelectItem>
                    <SelectItem value="resolved">Resolved</SelectItem>
                  </SelectContent>
                </Select>

                {/* Severity */}
                <Select
                  value={severityFilter}
                  onValueChange={(v) => {
                    if (v) setSeverityFilter(v as SeverityFilterValue)
                  }}
                >
                  <SelectTrigger className="h-10 font-mono text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Severities</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="low">Low</SelectItem>
                  </SelectContent>
                </Select>

                {/* Service */}
                <Select
                  value={serviceFilter}
                  onValueChange={(v) => {
                    if (v) setServiceFilter(v)
                  }}
                >
                  <SelectTrigger className="h-10 font-mono text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Services</SelectItem>
                    {INCIDENT_SERVICES.map((svc) => (
                      <SelectItem key={svc} value={svc}>
                        {svc}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* Assignee */}
                <Select
                  value={assigneeFilter}
                  onValueChange={(v) => {
                    if (v) setAssigneeFilter(v)
                  }}
                >
                  <SelectTrigger className="h-10 font-mono text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Assignees</SelectItem>
                    {ASSIGNEES.map((name) => (
                      <SelectItem key={name} value={name}>
                        {name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {/* Sort */}
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <ArrowUpDown className="size-4" />
                  <span className="font-mono text-sm">Sort:</span>
                </div>
                <Select
                  value={sortBy}
                  onValueChange={(v) => {
                    if (v) setSortBy(v as SortOption)
                  }}
                >
                  <SelectTrigger className="h-10 font-mono text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="severity">Severity</SelectItem>
                    <SelectItem value="created">Created Time</SelectItem>
                    <SelectItem value="updated">Last Updated</SelectItem>
                  </SelectContent>
                </Select>

                <span className="ml-auto font-mono text-sm text-muted-foreground">
                  {filtered.length} incident{filtered.length !== 1 ? "s" : ""}
                </span>
              </div>

              {/* No results */}
              {filtered.length === 0 ? (
                <div className="flex flex-col items-center justify-center gap-2 py-16 text-muted-foreground/50">
                  <AlertTriangle className="size-8" />
                  <span className="font-mono text-sm">
                    No incidents match your filters
                  </span>
                  <Button
                    variant="ghost"
                    size="xs"
                    className="font-mono text-xs"
                    onClick={() => {
                      setAccountFilter(null)
                      setStatusFilter("all")
                      setSeverityFilter("all")
                      setServiceFilter("all")
                      setAssigneeFilter("all")
                    }}
                  >
                    Clear filters
                  </Button>
                </div>
              ) : viewMode === "table" ? (
                /* ---- Table View ---- */
                <div className="rounded-lg border border-border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-20 font-mono text-xs">
                          Severity
                        </TableHead>
                        <TableHead className="font-mono text-xs">
                          Title
                        </TableHead>
                        <TableHead className="font-mono text-xs">
                          Service
                        </TableHead>
                        <TableHead className="font-mono text-xs">
                          Status
                        </TableHead>
                        <TableHead className="font-mono text-xs">
                          Assignee
                        </TableHead>
                        <TableHead className="w-20 font-mono text-xs">
                          Duration
                        </TableHead>
                        <TableHead className="w-20 font-mono text-xs">
                          Updated
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filtered.map((incident) => {
                        const isCritical = incident.severity === "critical"
                        return (
                          <TableRow
                            key={incident.id}
                            className={cn(
                              "h-14 cursor-pointer",
                              isCritical && "bg-[#FF4444]/[0.04] shadow-[inset_0_0_20px_rgba(255,68,68,0.06)]"
                            )}
                            onClick={() => setSelectedIncident(incident)}
                          >
                            <TableCell>
                              <SeverityBadge severity={incident.severity} />
                            </TableCell>
                            <TableCell>
                              <div className="min-w-0">
                                <p className="truncate font-mono text-sm font-medium text-foreground">
                                  {incident.title}
                                </p>
                                <p className="font-mono text-sm text-muted-foreground">
                                  {incident.id}
                                </p>
                              </div>
                            </TableCell>
                            <TableCell className="font-mono text-sm text-muted-foreground">
                              {incident.service}
                            </TableCell>
                            <TableCell>
                              <StatusChip status={incident.status} />
                            </TableCell>
                            <TableCell className="font-mono text-sm text-muted-foreground">
                              {incident.assignee}
                            </TableCell>
                            <TableCell className="font-mono text-sm text-muted-foreground">
                              {formatDuration(
                                incident.createdAt,
                                incident.resolvedAt
                              )}
                            </TableCell>
                            <TableCell className="font-mono text-sm text-muted-foreground">
                              {formatUpdated(incident.updatedAt)}
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                /* ---- Card View ---- */
                <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
                  {filtered.map((incident) => (
                    <IncidentCard
                      key={incident.id}
                      incident={incident}
                      onClick={() => setSelectedIncident(incident)}
                    />
                  ))}
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Alert Feed Sidebar - hidden on small screens */}
        <div className="hidden w-80 shrink-0 border-l border-border lg:flex xl:w-[360px]">
          <AlertFeed className="h-full w-full rounded-none border-0" />
        </div>
      </div>

      {/* Detail Panel */}
      {selectedIncident && (
        <IncidentDetail
          incident={selectedIncident}
          open={!!selectedIncident}
          onOpenChange={(open) => {
            if (!open) setSelectedIncident(null)
          }}
        />
      )}
    </div>
  )
}
