"use client"

import * as React from "react"
import {
  Shield,
  KeyRound,
  UserX,
  Network,
  Eye,
  Bug,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import type { LogEntry } from "@/lib/mock-data/logs"

interface SecurityCategory {
  id: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  color: string
  bgColor: string
  filterKey: string
}

const SECURITY_CATEGORIES: SecurityCategory[] = [
  {
    id: "auth_failure",
    label: "Auth Failures",
    icon: KeyRound,
    color: "#FF4444",
    bgColor: "rgba(255, 68, 68, 0.1)",
    filterKey: "auth_failure",
  },
  {
    id: "privilege_escalation",
    label: "Privilege Escalation",
    icon: UserX,
    color: "#FF0040",
    bgColor: "rgba(255, 0, 64, 0.1)",
    filterKey: "privilege_escalation",
  },
  {
    id: "network_anomaly",
    label: "Network Anomalies",
    icon: Network,
    color: "#FFB020",
    bgColor: "rgba(255, 176, 32, 0.1)",
    filterKey: "network_anomaly",
  },
  {
    id: "secret_exposure",
    label: "Secret Exposure",
    icon: Eye,
    color: "#FF6B6B",
    bgColor: "rgba(255, 107, 107, 0.1)",
    filterKey: "secret_exposure",
  },
  {
    id: "cve_alert",
    label: "CVE Alerts",
    icon: Bug,
    color: "#FF8C00",
    bgColor: "rgba(255, 140, 0, 0.1)",
    filterKey: "cve_alert",
  },
]

interface SecurityLogViewProps {
  logs: LogEntry[]
  activeCategory: string | null
  onCategorySelect: (category: string | null) => void
}

export function SecurityLogView({
  logs,
  activeCategory,
  onCategorySelect,
}: SecurityLogViewProps) {
  const securityLogs = logs.filter((l) => l.security)

  const categoryCounts = React.useMemo(() => {
    const counts: Record<string, number> = {}
    for (const cat of SECURITY_CATEGORIES) {
      counts[cat.id] = securityLogs.filter(
        (l) => l.securityCategory === cat.id
      ).length
    }
    return counts
  }, [securityLogs])

  return (
    <div className="border-b border-border/50 bg-[#0B0B10] px-4 py-2">
      <div className="mb-2 flex items-center gap-2">
        <Shield className="size-3.5 text-[#FF4444]" />
        <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-[#FF4444]/80">
          Security Events
        </span>
        <Badge
          variant="secondary"
          className="h-4 min-w-4 rounded-full bg-[#FF4444]/15 px-1 font-mono text-[9px] text-[#FF4444]"
        >
          {securityLogs.length}
        </Badge>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {SECURITY_CATEGORIES.map((cat) => {
          const count = categoryCounts[cat.id] || 0
          const isActive = activeCategory === cat.id
          const Icon = cat.icon

          return (
            <button
              key={cat.id}
              onClick={() => onCategorySelect(isActive ? null : cat.id)}
              className={cn(
                "flex items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-[11px] outline-none transition-all",
                isActive
                  ? "border-current"
                  : "border-border/50 hover:border-border"
              )}
              style={{
                color: isActive ? cat.color : undefined,
                backgroundColor: isActive ? cat.bgColor : undefined,
              }}
            >
              <Icon className={cn("size-3", !isActive && "text-muted-foreground/60")} />
              <span className={cn(!isActive && "text-muted-foreground/80")}>
                {cat.label}
              </span>
              <Badge
                variant="secondary"
                className={cn(
                  "h-4 min-w-4 rounded-full px-1 font-mono text-[9px]",
                  count > 0
                    ? isActive
                      ? "bg-white/15"
                      : "bg-muted"
                    : "bg-muted/50 text-muted-foreground/40"
                )}
                style={isActive && count > 0 ? { color: cat.color } : undefined}
              >
                {count}
              </Badge>
            </button>
          )
        })}
      </div>
    </div>
  )
}
