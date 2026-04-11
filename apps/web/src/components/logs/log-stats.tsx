"use client"

import * as React from "react"
import { Activity, AlertTriangle, AlertOctagon, Clock, Shield, TrendingUp } from "lucide-react"
import { cn } from "@/lib/utils"

interface LogStatsProps {
  totalLogs: number
  errorCount: number
  warningCount: number
  securityCount: number
  logsPerSecond: number
  timeRange: string
  isLiveTail: boolean
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  bgColor,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string | number
  color?: string
  bgColor?: string
}) {
  return (
    <div
      className="flex items-center gap-3 rounded-lg border border-border/30 px-4 py-3"
      style={{ backgroundColor: bgColor || "rgba(11, 11, 16, 0.5)" }}
    >
      <div
        className="flex size-9 items-center justify-center rounded-md"
        style={{ backgroundColor: bgColor || "rgba(255, 255, 255, 0.03)" }}
      >
        <Icon className={cn("size-5", color || "text-muted-foreground/60")} />
      </div>
      <div className="flex flex-col">
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground/50">
          {label}
        </span>
        <span className={cn("font-mono text-xl font-bold leading-tight", color || "text-foreground/90")}>
          {value}
        </span>
      </div>
    </div>
  )
}

export function LogStats({
  totalLogs,
  errorCount,
  warningCount,
  securityCount,
  logsPerSecond,
  timeRange,
  isLiveTail,
}: LogStatsProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-border/40 bg-[#0A0A0F] px-5 py-3.5">
      <StatCard
        icon={Activity}
        label="Total Logs"
        value={totalLogs.toLocaleString()}
      />

      <StatCard
        icon={AlertOctagon}
        label="Errors"
        value={errorCount}
        color="text-[#FF4444]"
        bgColor="rgba(255, 68, 68, 0.06)"
      />

      <StatCard
        icon={AlertTriangle}
        label="Warnings"
        value={warningCount}
        color="text-[#FFB020]"
        bgColor="rgba(255, 176, 32, 0.06)"
      />

      <StatCard
        icon={Shield}
        label="Security"
        value={securityCount}
        color="text-[#FF6B6B]"
        bgColor="rgba(255, 107, 107, 0.06)"
      />

      <StatCard
        icon={TrendingUp}
        label="Rate"
        value={`${logsPerSecond}/s`}
      />

      <div className="flex items-center gap-3 rounded-lg border border-border/30 bg-[#0B0B10]/50 px-4 py-3">
        <div className="flex size-9 items-center justify-center rounded-md bg-white/[0.03]">
          <Clock className="size-5 text-muted-foreground/60" />
        </div>
        <div className="flex flex-col">
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground/50">
            Time Range
          </span>
          <span className="font-mono text-sm font-medium leading-tight text-foreground/80">
            {timeRange}
          </span>
        </div>
      </div>

      {isLiveTail && (
        <div className="flex items-center gap-2.5 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3">
          <span className="relative flex size-3">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-75" />
            <span className="relative inline-flex size-3 rounded-full bg-primary" />
          </span>
          <span className="font-mono text-sm font-bold uppercase tracking-widest text-primary">
            Live
          </span>
        </div>
      )}
    </div>
  )
}
