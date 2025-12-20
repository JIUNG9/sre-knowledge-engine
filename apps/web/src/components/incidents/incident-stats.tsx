"use client"

import { cn } from "@/lib/utils"
import {
  MOCK_INCIDENTS,
  type IncidentSeverity,
} from "@/lib/mock-data/incidents"
import { AlertTriangle, Clock, TrendingUp, Activity } from "lucide-react"

interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  icon: React.ElementType
  color?: string
  pulse?: boolean
}

function StatCard({ label, value, sub, icon: Icon, color, pulse }: StatCardProps) {
  return (
    <div className="flex items-center gap-3 rounded-lg bg-card px-3 py-2.5 ring-1 ring-foreground/10">
      <div
        className={cn(
          "flex size-8 items-center justify-center rounded-md",
          pulse && "animate-pulse"
        )}
        style={{ backgroundColor: color ? `${color}15` : undefined }}
      >
        <Icon className="size-4" style={{ color }} />
      </div>
      <div className="min-w-0">
        <p className="font-mono text-[10px] text-muted-foreground">{label}</p>
        <div className="flex items-baseline gap-1.5">
          <span className="font-mono text-lg font-semibold text-foreground">
            {value}
          </span>
          {sub && (
            <span className="font-mono text-[10px] text-muted-foreground">
              {sub}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

function SeverityMiniCount({
  severity,
  count,
  color,
}: {
  severity: string
  count: number
  color: string
}) {
  return (
    <div className="flex items-center gap-1">
      <span
        className={cn("inline-block size-2 rounded-full", count > 0 && severity === "critical" && "animate-pulse")}
        style={{ backgroundColor: color }}
      />
      <span className="font-mono text-[10px] text-muted-foreground">
        {count} {severity}
      </span>
    </div>
  )
}

export function IncidentStats() {
  const active = MOCK_INCIDENTS.filter((i) => i.status !== "resolved")
  const resolved = MOCK_INCIDENTS.filter((i) => i.status === "resolved")

  // Count active by severity
  const severityCounts: Record<IncidentSeverity, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  }
  for (const inc of active) {
    severityCounts[inc.severity]++
  }

  // MTTR: average time to resolve for resolved incidents
  const resolvedWithTime = resolved.filter((i) => i.resolvedAt)
  const totalResolveMs = resolvedWithTime.reduce((sum, i) => {
    const created = new Date(i.createdAt).getTime()
    const resolvedAt = new Date(i.resolvedAt!).getTime()
    return sum + (resolvedAt - created)
  }, 0)
  const mttrMinutes =
    resolvedWithTime.length > 0
      ? Math.round(totalResolveMs / resolvedWithTime.length / 60000)
      : 0
  const mttrDisplay =
    mttrMinutes >= 60
      ? `${Math.round(mttrMinutes / 60)}h ${mttrMinutes % 60}m`
      : `${mttrMinutes}m`

  // Opened today
  const todayStart = new Date()
  todayStart.setHours(0, 0, 0, 0)
  const openedToday = MOCK_INCIDENTS.filter(
    (i) => new Date(i.createdAt) >= todayStart
  ).length

  // Opened this week
  const weekStart = new Date()
  weekStart.setDate(weekStart.getDate() - 7)
  const openedThisWeek = MOCK_INCIDENTS.filter(
    (i) => new Date(i.createdAt) >= weekStart
  ).length

  // Resolution rate
  const resolutionRate =
    MOCK_INCIDENTS.length > 0
      ? Math.round((resolved.length / MOCK_INCIDENTS.length) * 100)
      : 0

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        <StatCard
          label="Active Incidents"
          value={active.length}
          icon={AlertTriangle}
          color="#FF4444"
          pulse={severityCounts.critical > 0}
        />
        <StatCard
          label="MTTR (Current Period)"
          value={mttrDisplay}
          icon={Clock}
          color="#FFB020"
        />
        <StatCard
          label="Opened"
          value={openedToday}
          sub={`today / ${openedThisWeek} this week`}
          icon={Activity}
          color="#00B8FF"
        />
        <StatCard
          label="Resolution Rate"
          value={`${resolutionRate}%`}
          sub={`${resolved.length}/${MOCK_INCIDENTS.length}`}
          icon={TrendingUp}
          color="#00FF88"
        />
      </div>
      {/* Severity breakdown mini row */}
      <div className="flex items-center gap-3 px-1">
        <span className="font-mono text-[10px] text-muted-foreground/60">
          Active by severity:
        </span>
        <SeverityMiniCount severity="critical" count={severityCounts.critical} color="#FF4444" />
        <SeverityMiniCount severity="high" count={severityCounts.high} color="#FF8C00" />
        <SeverityMiniCount severity="medium" count={severityCounts.medium} color="#FFB020" />
        <SeverityMiniCount severity="low" count={severityCounts.low} color="#00B8FF" />
      </div>
    </div>
  )
}
