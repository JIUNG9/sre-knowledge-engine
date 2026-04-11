"use client"

import * as React from "react"
import { ChevronRight, Copy, ExternalLink, Check } from "lucide-react"
import { cn } from "@/lib/utils"
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

function formatDate(iso: string): string {
  const date = new Date(iso)
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${month}/${day}`
}

function LevelBadge({ level }: { level: LogLevel }) {
  const config = LOG_LEVEL_CONFIG[level]
  return (
    <span
      className="inline-flex h-7 w-16 shrink-0 items-center justify-center rounded-md font-mono text-xs font-bold uppercase tracking-wider"
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
    <span className="inline-flex h-7 shrink-0 items-center truncate rounded-md bg-[#1A1A25] px-2.5 font-mono text-xs font-medium text-muted-foreground/80">
      {service}
    </span>
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
        "group border-b border-border/20 transition-colors",
        isEven ? "bg-[#0B0B10]" : "bg-[#0E0E15]",
        isExpanded && "bg-[#10101A]",
        entry.security && "border-l-2 border-l-[#FF4444]/50",
        !entry.security && "border-l-2 border-l-transparent"
      )}
    >
      {/* Compact row */}
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-4 py-4 text-left outline-none transition-colors hover:bg-white/[0.02]"
      >
        <ChevronRight
          className={cn(
            "size-4 shrink-0 text-muted-foreground/40 transition-transform duration-150",
            isExpanded && "rotate-90 text-muted-foreground/70"
          )}
        />

        {/* Timestamp - monospace, right-aligned feel */}
        <span className="shrink-0 text-right font-mono text-sm tabular-nums text-muted-foreground/50">
          <span className="text-muted-foreground/30">{formatDate(entry.timestamp)}</span>
          {" "}
          {formatTimestamp(entry.timestamp)}
        </span>

        <LevelBadge level={entry.level} />
        <ServiceBadge service={entry.service} />

        {/* Message - truncated, 14px */}
        <span className="min-w-0 flex-1 truncate font-mono text-sm leading-relaxed text-foreground/80">
          {entry.message}
        </span>

        {/* Security indicator */}
        {entry.security && (
          <span className="shrink-0 rounded-md bg-[#FF4444]/10 px-2 py-0.5 font-mono text-xs font-bold uppercase tracking-widest text-[#FF4444]/80">
            sec
          </span>
        )}

        {/* Expand hint on hover */}
        <span className="shrink-0 font-mono text-xs text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/30">
          {isExpanded ? "collapse" : "expand"}
        </span>
      </button>

      {/* Expanded details */}
      {isExpanded && (
        <div className="border-t border-border/20 bg-[#09090E] px-5 py-4 pl-12">
          {/* Action buttons */}
          <div className="mb-4 flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 font-mono text-xs"
              onClick={handleCopy}
            >
              {copied ? (
                <Check className="size-3.5 text-primary" />
              ) : (
                <Copy className="size-3.5" />
              )}
              {copied ? "Copied" : "Copy JSON"}
            </Button>
            {entry.traceId && (
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 font-mono text-xs"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="size-3.5" />
                View Trace
              </Button>
            )}
          </div>

          {/* Full message */}
          <div className="mb-4">
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground/40">
              Full Message
            </span>
            <p className="mt-1.5 rounded-md bg-[#0C0C12] p-3 font-mono text-sm leading-relaxed text-foreground/90">
              {entry.message}
            </p>
          </div>

          {/* Trace info */}
          {(entry.traceId || entry.spanId) && (
            <div className="mb-4 flex flex-wrap gap-x-8 gap-y-2">
              {entry.traceId && (
                <div>
                  <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground/40">
                    Trace ID
                  </span>
                  <p className="mt-1 font-mono text-sm text-primary/80">
                    {entry.traceId}
                  </p>
                </div>
              )}
              {entry.spanId && (
                <div>
                  <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground/40">
                    Span ID
                  </span>
                  <p className="mt-1 font-mono text-sm text-primary/80">
                    {entry.spanId}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Attributes table */}
          {entry.attributes && Object.keys(entry.attributes).length > 0 && (
            <div>
              <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground/40">
                Attributes
              </span>
              <div className="mt-2 grid grid-cols-1 gap-x-8 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
                {Object.entries(entry.attributes).map(([key, value]) => (
                  <div key={key} className="flex items-baseline gap-2 font-mono text-sm">
                    <span className="shrink-0 text-muted-foreground/50">{key}:</span>
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
