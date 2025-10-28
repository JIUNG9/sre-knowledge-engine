"use client"

import * as React from "react"
import { Activity, AlertTriangle, AlertOctagon, Clock, Shield } from "lucide-react"
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

function StatItem({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string | number
  color?: string
}) {
  return (
    <div className="flex items-center gap-1.5">
      <Icon className={cn("size-3", color || "text-muted-foreground/50")} />
      <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/60">
        {label}
      </span>
      <span className={cn("font-mono text-[11px] font-medium", color || "text-foreground/80")}>
        {value}
      </span>
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
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-b border-border/50 bg-[#0B0B10] px-4 py-2">
      <StatItem
        icon={Activity}
        label="Total"
        value={totalLogs.toLocaleString()}
      />
      <div className="h-3 w-px bg-border/30" />
      <StatItem
        icon={AlertOctagon}
        label="Errors"
        value={errorCount}
        color="text-[#FF4444]"
      />
      <div className="h-3 w-px bg-border/30" />
      <StatItem
        icon={AlertTriangle}
        label="Warnings"
        value={warningCount}
        color="text-[#FFB020]"
      />
      <div className="h-3 w-px bg-border/30" />
      <StatItem
        icon={Shield}
        label="Security"
        value={securityCount}
        color="text-[#FF4444]/80"
      />
      <div className="h-3 w-px bg-border/30" />
      <StatItem
        icon={Activity}
        label="Rate"
        value={`${logsPerSecond}/s`}
      />
      <div className="h-3 w-px bg-border/30" />
      <div className="flex items-center gap-1.5">
        <Clock className="size-3 text-muted-foreground/50" />
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/60">
          Range
        </span>
        <span className="font-mono text-[11px] font-medium text-foreground/80">
          {timeRange}
        </span>
      </div>

      {isLiveTail && (
        <>
          <div className="h-3 w-px bg-border/30" />
          <div className="flex items-center gap-1.5">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-75" />
              <span className="relative inline-flex size-2 rounded-full bg-primary" />
            </span>
            <span className="font-mono text-[10px] font-medium uppercase tracking-wider text-primary">
              Live
            </span>
          </div>
        </>
      )}
    </div>
  )
}
