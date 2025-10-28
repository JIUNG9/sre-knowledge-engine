"use client"

import * as React from "react"
import { ChevronRight, Copy, ExternalLink, Check } from "lucide-react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { LogEntry as LogEntryType, LogLevel } from "@/lib/mock-data/logs"
import { LOG_LEVEL_CONFIG } from "@/lib/mock-data/logs"

interface LogEntryProps {
  entry: LogEntryType
  isExpanded: boolean
  onToggle: () => void
  isEven: boolean
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso)
  const h = String(date.getHours()).padStart(2, "0")
  const m = String(date.getMinutes()).padStart(2, "0")
  const s = String(date.getSeconds()).padStart(2, "0")
  const ms = String(date.getMilliseconds()).padStart(3, "0")
  return `${h}:${m}:${s}.${ms}`
}

function LevelBadge({ level }: { level: LogLevel }) {
  const config = LOG_LEVEL_CONFIG[level]
  return (
    <span
      className="inline-flex h-[18px] w-[34px] shrink-0 items-center justify-center rounded-sm font-mono text-[10px] font-bold uppercase tracking-wider"
      style={{
        color: config.color,
        backgroundColor: config.bgColor,
      }}
    >
      {config.label}
    </span>
  )
}

function ServiceBadge({ service }: { service: string }) {
  return (
    <Badge
      variant="outline"
      className="h-[18px] shrink-0 truncate rounded-sm border-border/50 px-1.5 font-mono text-[10px] text-muted-foreground"
    >
      {service}
    </Badge>
  )
}

export function LogEntryRow({ entry, isExpanded, onToggle, isEven }: LogEntryProps) {
  const [copied, setCopied] = React.useState(false)

  const handleCopy = React.useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      const json = JSON.stringify(entry, null, 2)
      navigator.clipboard.writeText(json).then(() => {
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      })
    },
    [entry]
  )

  return (
    <div
      className={cn(
        "group border-b border-border/30 transition-colors",
        isEven ? "bg-[#0D0D12]" : "bg-[#0B0B10]",
        isExpanded && "bg-[#0F0F16]",
        entry.security && "border-l-2 border-l-[#FF4444]/40",
        !entry.security && "border-l-2 border-l-transparent"
      )}
    >
      {/* Compact row */}
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left outline-none transition-colors hover:bg-white/[0.02]"
      >
        <ChevronRight
          className={cn(
            "size-3 shrink-0 text-muted-foreground/50 transition-transform duration-150",
            isExpanded && "rotate-90"
          )}
        />
        <span className="shrink-0 font-mono text-[11px] text-muted-foreground/60">
          {formatTimestamp(entry.timestamp)}
        </span>
        <LevelBadge level={entry.level} />
        <ServiceBadge service={entry.service} />
        <span className="min-w-0 flex-1 truncate font-mono text-[12px] text-foreground/80">
          {entry.message}
        </span>
        {entry.security && (
          <span className="shrink-0 font-mono text-[9px] font-medium uppercase tracking-widest text-[#FF4444]/70">
            sec
          </span>
        )}
      </button>

      {/* Expanded details */}
      {isExpanded && (
        <div className="border-t border-border/20 bg-[#0A0A10] px-4 py-3 pl-8">
          {/* Action buttons */}
          <div className="mb-3 flex items-center gap-2">
            <Button
              variant="outline"
              size="xs"
              className="gap-1 font-mono text-[10px]"
              onClick={handleCopy}
            >
              {copied ? (
                <Check className="size-3 text-primary" />
              ) : (
                <Copy className="size-3" />
              )}
              {copied ? "Copied" : "Copy JSON"}
            </Button>
            {entry.traceId && (
              <Button
                variant="outline"
                size="xs"
                className="gap-1 font-mono text-[10px]"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="size-3" />
                View Trace
              </Button>
            )}
          </div>

          {/* Full message */}
          <div className="mb-3">
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/50">
              Message
            </span>
            <p className="mt-1 font-mono text-[12px] leading-relaxed text-foreground/90">
              {entry.message}
            </p>
          </div>

          {/* Trace info */}
          {(entry.traceId || entry.spanId) && (
            <div className="mb-3 flex flex-wrap gap-x-6 gap-y-1">
              {entry.traceId && (
                <div>
                  <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/50">
                    Trace ID
                  </span>
                  <p className="mt-0.5 font-mono text-[11px] text-primary/80">
                    {entry.traceId}
                  </p>
                </div>
              )}
              {entry.spanId && (
                <div>
                  <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/50">
                    Span ID
                  </span>
                  <p className="mt-0.5 font-mono text-[11px] text-primary/80">
                    {entry.spanId}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Attributes table */}
          {entry.attributes && Object.keys(entry.attributes).length > 0 && (
            <div>
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/50">
                Attributes
              </span>
              <div className="mt-1 grid grid-cols-1 gap-x-6 gap-y-0.5 sm:grid-cols-2 lg:grid-cols-3">
                {Object.entries(entry.attributes).map(([key, value]) => (
                  <div key={key} className="flex items-baseline gap-1.5 font-mono text-[11px]">
                    <span className="shrink-0 text-muted-foreground/60">{key}:</span>
                    <span className="truncate text-foreground/70">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
