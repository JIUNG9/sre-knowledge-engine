"use client"

import * as React from "react"
import {
  KeyRound,
  ShieldAlert,
  Activity,
  Grid3X3,
  AlertTriangle,
  Sparkles,
  Clock,
  Filter,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { AccountFilter } from "@/components/account-filter"
import {
  mockIAMRoles,
  mockLeastPrivilegeRecommendations,
  mockCloudTrailEvents,
  mockAccessMatrix,
  type RiskLevel,
  type AccessLevel,
  type CloudTrailEvent,
} from "@/lib/mock-data/iam"

// ── Risk level colors ──────────────────────────────────────────

const riskColors: Record<RiskLevel, string> = {
  critical: "text-red-400 bg-red-400/10 border-red-400/30",
  high: "text-orange-400 bg-orange-400/10 border-orange-400/30",
  medium: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  low: "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
}

const riskDotColors: Record<RiskLevel, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-amber-500",
  low: "bg-emerald-500",
}

// ── Access level cell colors ───────────────────────────────────

const accessCellColors: Record<AccessLevel, string> = {
  full: "bg-emerald-500/20 text-emerald-400",
  read: "bg-emerald-500/10 text-emerald-400/70",
  none: "bg-muted/30 text-muted-foreground/40",
  overprivileged: "bg-red-500/20 text-red-400",
}

const accessLabels: Record<AccessLevel, string> = {
  full: "Full",
  read: "Read",
  none: "--",
  overprivileged: "Over",
}

// ── Role type badges ───────────────────────────────────────────

const roleTypeColors: Record<string, string> = {
  service: "text-blue-400 bg-blue-400/10 border-blue-400/30",
  user: "text-purple-400 bg-purple-400/10 border-purple-400/30",
  "cross-account": "text-cyan-400 bg-cyan-400/10 border-cyan-400/30",
}

// ── Helpers ────────────────────────────────────────────────────

function formatTimestamp(ts: string) {
  const d = new Date(ts)
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })
}

function formatNumber(n: number) {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return n.toString()
}

function timeAgo(ts: string) {
  const now = new Date("2026-04-10T10:00:00Z")
  const d = new Date(ts)
  const diffMs = now.getTime() - d.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return "Today"
  if (diffDays === 1) return "Yesterday"
  if (diffDays < 30) return `${diffDays}d ago`
  return `${Math.floor(diffDays / 30)}mo ago`
}

// ── Roles Overview Tab ─────────────────────────────────────────

function RolesOverviewTab({ accountFilter }: { accountFilter: string | null }) {
  const roles = accountFilter
    ? mockIAMRoles.filter(
        (r) =>
          r.account ===
          (accountFilter === "nx"
            ? "nexus"
            : accountFilter === "nw"
              ? "prod-a"
              : accountFilter === "dp"
                ? "prod-b"
                : accountFilter)
      )
    : mockIAMRoles

  const criticalCount = roles.filter((r) => r.riskLevel === "critical").length
  const highCount = roles.filter((r) => r.riskLevel === "high").length
  const overPrivileged = roles.filter(
    (r) => r.permissionsCount > r.usedPermissionsCount * 2
  ).length

  return (
    <div className="space-y-5">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
        <Card className="border-border/50 bg-card p-5">
          <div className="flex items-center gap-2">
            <KeyRound className="size-5 text-muted-foreground" />
            <span className="font-mono text-sm text-muted-foreground">
              Total Roles
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold">{roles.length}</p>
        </Card>
        <Card className="border-border/50 bg-card p-5">
          <div className="flex items-center gap-2">
            <AlertTriangle className="size-5 text-red-400" />
            <span className="font-mono text-sm text-muted-foreground">
              Critical Risk
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-red-400">
            {criticalCount}
          </p>
        </Card>
        <Card className="border-border/50 bg-card p-5">
          <div className="flex items-center gap-2">
            <ShieldAlert className="size-5 text-orange-400" />
            <span className="font-mono text-sm text-muted-foreground">
              High Risk
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-orange-400">
            {highCount}
          </p>
        </Card>
        <Card className="border-border/50 bg-card p-5">
          <div className="flex items-center gap-2">
            <ShieldAlert className="size-5 text-amber-400" />
            <span className="font-mono text-sm text-muted-foreground">
              Over-Privileged
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-amber-400">
            {overPrivileged}
          </p>
        </Card>
      </div>

      {/* Roles table */}
      <Card className="border-border/50 bg-card">
        <Table>
          <TableHeader>
            <TableRow className="border-border/50 hover:bg-transparent">
              <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Account
              </TableHead>
              <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Role Name
              </TableHead>
              <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Type
              </TableHead>
              <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Last Used
              </TableHead>
              <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Usage (30d)
              </TableHead>
              <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Permissions
              </TableHead>
              <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Risk Level
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {roles.map((role) => (
              <TableRow
                key={role.id}
                className="h-12 border-border/30 hover:bg-muted/30"
              >
                <TableCell className="font-mono text-sm">
                  <span className="rounded bg-muted/50 px-2 py-0.5 text-xs">
                    {role.account}
                  </span>
                </TableCell>
                <TableCell className="font-mono text-sm font-medium">
                  {role.roleName}
                </TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={`font-mono text-xs ${roleTypeColors[role.type]}`}
                  >
                    {role.type}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-sm text-muted-foreground">
                  {timeAgo(role.lastUsed)}
                </TableCell>
                <TableCell className="font-mono text-sm">
                  {formatNumber(role.usage30d)}
                </TableCell>
                <TableCell className="font-mono text-sm">
                  <span className="text-muted-foreground">
                    {role.usedPermissionsCount}
                  </span>
                  <span className="text-muted-foreground/40"> / </span>
                  <span
                    className={
                      role.usedPermissionsCount < role.permissionsCount * 0.5
                        ? "text-amber-400"
                        : ""
                    }
                  >
                    {role.permissionsCount}
                  </span>
                </TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={`font-mono text-xs ${riskColors[role.riskLevel]}`}
                  >
                    <span
                      className={`mr-1 inline-block size-1.5 rounded-full ${riskDotColors[role.riskLevel]}`}
                    />
                    {role.riskLevel.toUpperCase()}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}

// ── Least Privilege Tab ────────────────────────────────────────

function LeastPrivilegeTab({
  accountFilter,
}: {
  accountFilter: string | null
}) {
  const recs = accountFilter
    ? mockLeastPrivilegeRecommendations.filter(
        (r) =>
          r.account ===
          (accountFilter === "nx"
            ? "nexus"
            : accountFilter === "nw"
              ? "prod-a"
              : accountFilter === "dp"
                ? "prod-b"
                : accountFilter)
      )
    : mockLeastPrivilegeRecommendations

  const totalUnused = recs.reduce(
    (sum, r) => sum + (r.currentPermissions - r.usedPermissions),
    0
  )

  return (
    <div className="space-y-5">
      {/* Summary */}
      <div className="grid grid-cols-2 gap-5 lg:grid-cols-3">
        <Card className="border-border/50 bg-card p-5">
          <div className="flex items-center gap-2">
            <Sparkles className="size-5 text-primary" />
            <span className="font-mono text-sm text-muted-foreground">
              AI Recommendations
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-primary">
            {recs.length}
          </p>
        </Card>
        <Card className="border-border/50 bg-card p-5">
          <div className="flex items-center gap-2">
            <ShieldAlert className="size-5 text-amber-400" />
            <span className="font-mono text-sm text-muted-foreground">
              Unused Permissions
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-amber-400">
            {totalUnused}
          </p>
        </Card>
        <Card className="border-border/50 bg-card p-5">
          <div className="flex items-center gap-2">
            <AlertTriangle className="size-5 text-red-400" />
            <span className="font-mono text-sm text-muted-foreground">
              Critical Findings
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-red-400">
            {recs.filter((r) => r.severity === "critical").length}
          </p>
        </Card>
      </div>

      {/* Recommendation cards */}
      <div className="space-y-5">
        {recs.map((rec) => (
          <Card key={rec.id} className="border-border/50 bg-card">
            <CardHeader className="border-b border-border/30 pb-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle className="flex items-center gap-2 font-mono text-lg">
                    {rec.roleName}
                    <Badge
                      variant="outline"
                      className={`font-mono text-xs ${riskColors[rec.severity]}`}
                    >
                      {rec.severity.toUpperCase()}
                    </Badge>
                  </CardTitle>
                  <CardDescription className="mt-1 font-mono text-sm">
                    Account: {rec.account}
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm" disabled className="font-mono text-xs">
                  Apply Fix
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              {/* Permission stats */}
              <div className="flex gap-8">
                <div>
                  <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                    Current
                  </span>
                  <p className="font-mono text-2xl font-bold">
                    {rec.currentPermissions}
                  </p>
                </div>
                <div>
                  <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                    Actually Used
                  </span>
                  <p className="font-mono text-2xl font-bold text-emerald-400">
                    {rec.usedPermissions}
                  </p>
                </div>
                <div>
                  <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                    Unused
                  </span>
                  <p className="font-mono text-2xl font-bold text-red-400">
                    {rec.currentPermissions - rec.usedPermissions}
                  </p>
                </div>
              </div>

              {/* Usage bar */}
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted/50">
                <div
                  className="h-full rounded-full bg-emerald-500"
                  style={{
                    width: `${(rec.usedPermissions / rec.currentPermissions) * 100}%`,
                  }}
                />
              </div>

              {/* Unused permissions */}
              <div>
                <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Sample Unused Permissions
                </span>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {rec.unusedPermissions.map((perm, i) => (
                    <span
                      key={i}
                      className="rounded border border-red-400/20 bg-red-400/5 px-2 py-0.5 font-mono text-xs text-red-400"
                    >
                      {perm}
                    </span>
                  ))}
                </div>
              </div>

              {/* AI recommendation */}
              <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
                <div className="flex items-center gap-2">
                  <Sparkles className="size-4 text-primary" />
                  <span className="font-mono text-xs font-medium uppercase tracking-wider text-primary">
                    AI Recommendation
                  </span>
                </div>
                <p className="mt-2 font-mono text-sm leading-relaxed text-foreground/80">
                  {rec.recommendation}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

// ── CloudTrail Tab ─────────────────────────────────────────────

function CloudTrailTab({ accountFilter }: { accountFilter: string | null }) {
  const [readWriteFilter, setReadWriteFilter] = React.useState<
    "all" | "read" | "write"
  >("all")

  let events: CloudTrailEvent[] = accountFilter
    ? mockCloudTrailEvents.filter(
        (e) =>
          e.account ===
          (accountFilter === "nx"
            ? "nexus"
            : accountFilter === "nw"
              ? "prod-a"
              : accountFilter === "dp"
                ? "prod-b"
                : accountFilter)
      )
    : mockCloudTrailEvents

  if (readWriteFilter !== "all") {
    events = events.filter((e) => e.readWrite === readWriteFilter)
  }

  const anomalyCount = events.filter((e) => e.anomaly).length

  return (
    <div className="space-y-5">
      {/* Summary + filters */}
      <div className="flex items-center justify-between">
        <div className="grid grid-cols-2 gap-5 lg:grid-cols-3">
          <Card className="border-border/50 bg-card p-5">
            <div className="flex items-center gap-2">
              <Activity className="size-5 text-muted-foreground" />
              <span className="font-mono text-sm text-muted-foreground">
                Total Events
              </span>
            </div>
            <p className="mt-3 font-mono text-3xl font-bold">
              {events.length}
            </p>
          </Card>
          <Card className="border-border/50 bg-card p-5">
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-5 text-amber-400" />
              <span className="font-mono text-sm text-muted-foreground">
                Anomalies
              </span>
            </div>
            <p className="mt-3 font-mono text-3xl font-bold text-amber-400">
              {anomalyCount}
            </p>
          </Card>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="size-4 text-muted-foreground" />
          <div className="flex gap-1 rounded-lg bg-muted/50 p-0.5">
            {(["all", "read", "write"] as const).map((f) => (
              <Button
                key={f}
                variant={readWriteFilter === f ? "secondary" : "ghost"}
                size="xs"
                className="font-mono text-xs"
                onClick={() => setReadWriteFilter(f)}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Events table */}
      <Card className="border-border/50 bg-card">
        <ScrollArea className="h-[600px]">
          <Table>
            <TableHeader>
              <TableRow className="border-border/50 hover:bg-transparent">
                <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Timestamp
                </TableHead>
                <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Account
                </TableHead>
                <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Role
                </TableHead>
                <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Action
                </TableHead>
                <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Resource
                </TableHead>
                <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Source IP
                </TableHead>
                <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  R/W
                </TableHead>
                <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Anomaly
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {events.map((event) => (
                <TableRow
                  key={event.id}
                  className={`h-12 border-border/30 ${
                    event.anomaly
                      ? "bg-amber-500/5 hover:bg-amber-500/10"
                      : "hover:bg-muted/30"
                  }`}
                >
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    <div className="flex items-center gap-1.5">
                      <Clock className="size-3" />
                      {formatTimestamp(event.timestamp)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="rounded bg-muted/50 px-2 py-0.5 font-mono text-xs">
                      {event.account}
                    </span>
                  </TableCell>
                  <TableCell className="max-w-[160px] truncate font-mono text-sm">
                    {event.role}
                  </TableCell>
                  <TableCell className="font-mono text-sm font-medium">
                    {event.action}
                  </TableCell>
                  <TableCell className="max-w-[280px] truncate font-mono text-xs text-muted-foreground">
                    {event.resource}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {event.sourceIp}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={`font-mono text-[10px] ${
                        event.readWrite === "write"
                          ? "border-orange-400/30 text-orange-400"
                          : "border-blue-400/30 text-blue-400"
                      }`}
                    >
                      {event.readWrite.toUpperCase()}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {event.anomaly ? (
                      <div className="group relative">
                        <Badge
                          variant="outline"
                          className="cursor-help border-amber-400/30 bg-amber-400/10 font-mono text-[10px] text-amber-400"
                        >
                          <AlertTriangle className="mr-1 size-3" />
                          ANOMALY
                        </Badge>
                        <div className="pointer-events-none absolute right-0 bottom-full z-50 mb-2 hidden w-64 rounded-lg border border-border bg-popover p-3 text-xs text-popover-foreground shadow-lg group-hover:block">
                          {event.anomalyReason}
                        </div>
                      </div>
                    ) : (
                      <span className="font-mono text-xs text-muted-foreground/40">
                        --
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ScrollArea>
      </Card>
    </div>
  )
}

// ── Access Matrix Tab ──────────────────────────────────────────

function AccessMatrixTab({
  accountFilter,
}: {
  accountFilter: string | null
}) {
  const matrix = accountFilter
    ? mockAccessMatrix.filter(
        (m) =>
          m.account ===
          (accountFilter === "nx"
            ? "nexus"
            : accountFilter === "nw"
              ? "prod-a"
              : accountFilter === "dp"
                ? "prod-b"
                : accountFilter)
      )
    : mockAccessMatrix

  const resources = [
    "s3",
    "rds",
    "eks",
    "lambda",
    "ec2",
    "secretsManager",
  ] as const
  const resourceLabels: Record<string, string> = {
    s3: "S3",
    rds: "RDS",
    eks: "EKS",
    lambda: "Lambda",
    ec2: "EC2",
    secretsManager: "Secrets Mgr",
  }

  return (
    <div className="space-y-5">
      {/* Legend */}
      <div className="flex items-center gap-5">
        <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          Legend:
        </span>
        <div className="flex gap-3">
          {(
            [
              ["full", "Full Access"],
              ["read", "Read Only"],
              ["none", "No Access"],
              ["overprivileged", "Over-Privileged"],
            ] as const
          ).map(([level, label]) => (
            <div key={level} className="flex items-center gap-1.5">
              <span
                className={`inline-block size-3 rounded ${accessCellColors[level]}`}
              />
              <span className="font-mono text-xs text-muted-foreground">
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Matrix table */}
      <Card className="border-border/50 bg-card">
        <Table>
          <TableHeader>
            <TableRow className="border-border/50 hover:bg-transparent">
              <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Role
              </TableHead>
              <TableHead className="h-12 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Account
              </TableHead>
              {resources.map((r) => (
                <TableHead
                  key={r}
                  className="h-12 text-center font-mono text-xs uppercase tracking-wider text-muted-foreground"
                >
                  {resourceLabels[r]}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {matrix.map((entry, i) => (
              <TableRow
                key={i}
                className="h-12 border-border/30 hover:bg-muted/30"
              >
                <TableCell className="font-mono text-sm font-medium">
                  {entry.roleName}
                </TableCell>
                <TableCell>
                  <span className="rounded bg-muted/50 px-2 py-0.5 font-mono text-xs">
                    {entry.account}
                  </span>
                </TableCell>
                {resources.map((r) => {
                  const level = entry[r]
                  return (
                    <TableCell key={r} className="text-center">
                      <span
                        className={`inline-flex h-7 w-14 items-center justify-center rounded font-mono text-[11px] font-medium ${accessCellColors[level]}`}
                      >
                        {accessLabels[level]}
                      </span>
                    </TableCell>
                  )
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────

export default function IAMAuditPage() {
  const [accountFilter, setAccountFilter] = React.useState<string | null>(null)

  return (
    <ScrollArea className="flex-1">
      <div className="space-y-6 p-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-mono text-2xl font-bold">IAM Audit</h1>
            <p className="mt-1 font-mono text-sm text-muted-foreground">
              Role analysis, least privilege enforcement, access monitoring
            </p>
          </div>
          <Badge variant="outline" className="font-mono text-xs">
            Last scan: 15m ago
          </Badge>
        </div>

        {/* Account filter chips */}
        <AccountFilter value={accountFilter} onChange={setAccountFilter} />

        {/* Tabs */}
        <Tabs defaultValue="roles">
          <TabsList className="bg-card">
            <TabsTrigger value="roles" className="gap-1.5 font-mono text-sm">
              <KeyRound className="size-3.5" />
              Roles Overview
            </TabsTrigger>
            <TabsTrigger
              value="least-privilege"
              className="gap-1.5 font-mono text-sm"
            >
              <Sparkles className="size-3.5" />
              Least Privilege
            </TabsTrigger>
            <TabsTrigger
              value="cloudtrail"
              className="gap-1.5 font-mono text-sm"
            >
              <Activity className="size-3.5" />
              CloudTrail
            </TabsTrigger>
            <TabsTrigger
              value="access-matrix"
              className="gap-1.5 font-mono text-sm"
            >
              <Grid3X3 className="size-3.5" />
              Access Matrix
            </TabsTrigger>
          </TabsList>

          <TabsContent value="roles" className="mt-5">
            <RolesOverviewTab accountFilter={accountFilter} />
          </TabsContent>

          <TabsContent value="least-privilege" className="mt-5">
            <LeastPrivilegeTab accountFilter={accountFilter} />
          </TabsContent>

          <TabsContent value="cloudtrail" className="mt-5">
            <CloudTrailTab accountFilter={accountFilter} />
          </TabsContent>

          <TabsContent value="access-matrix" className="mt-5">
            <AccessMatrixTab accountFilter={accountFilter} />
          </TabsContent>
        </Tabs>
      </div>
    </ScrollArea>
  )
}
