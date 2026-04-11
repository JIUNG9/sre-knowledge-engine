"use client"

import * as React from "react"
import { ArrowDown } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { LogEntryRow } from "@/components/logs/log-entry"
import { LogSearch, type LogFilters } from "@/components/logs/log-search"
import { LogStats } from "@/components/logs/log-stats"
import { SecurityLogView } from "@/components/logs/security-log-view"
import {
  MOCK_LOGS,
  getLogStats,
  type LogEntry,
  type LogLevel,
} from "@/lib/mock-data/logs"

const MAX_VISIBLE_ENTRIES = 500

const TIME_RANGE_LABELS: Record<string, string> = {
  "15m": "Last 15 minutes",
  "1h": "Last 1 hour",
  "6h": "Last 6 hours",
  "24h": "Last 24 hours",
  "7d": "Last 7 days",
  custom: "Custom",
}

function filterLogs(logs: LogEntry[], filters: LogFilters): LogEntry[] {
  let result = logs

  // Text search
  if (filters.search) {
    const searchLower = filters.search.toLowerCase()
    result = result.filter(
      (log) =>
        log.message.toLowerCase().includes(searchLower) ||
        log.service.toLowerCase().includes(searchLower) ||
        (log.traceId && log.traceId.includes(searchLower)) ||
        Object.values(log.attributes || {}).some((v) =>
          v.toLowerCase().includes(searchLower)
        )
    )
  }

  // Level filter
  if (filters.levels.length > 0) {
    result = result.filter((log) => filters.levels.includes(log.level))
  }

  // Service filter
  if (filters.services.length > 0) {
    result = result.filter((log) => filters.services.includes(log.service))
  }

  // Time range filter
  if (filters.timeRange !== "custom") {
    const now = new Date()
    const rangeMs: Record<string, number> = {
      "15m": 15 * 60 * 1000,
      "1h": 60 * 60 * 1000,
      "6h": 6 * 60 * 60 * 1000,
      "24h": 24 * 60 * 60 * 1000,
      "7d": 7 * 24 * 60 * 60 * 1000,
    }
    const ms = rangeMs[filters.timeRange]
    if (ms) {
      const cutoff = new Date(now.getTime() - ms)
      result = result.filter((log) => new Date(log.timestamp) >= cutoff)
    }
  }

  // Security filter
  if (filters.security) {
    result = result.filter((log) => log.security)
  }

  return result
}

export function LogViewer() {
  const [filters, setFilters] = React.useState<LogFilters>({
    search: "",
    levels: [],
    services: [],
    timeRange: "24h",
    liveTail: false,
    security: false,
  })

  const [expandedId, setExpandedId] = React.useState<string | null>(null)
  const [isAtBottom, setIsAtBottom] = React.useState(true)
  const [securityCategory, setSecurityCategory] = React.useState<string | null>(null)

  const scrollContainerRef = React.useRef<HTMLDivElement>(null)

  // Apply filters
  let filteredLogs = filterLogs(MOCK_LOGS, filters)

  // Apply security category sub-filter
  if (securityCategory) {
    filteredLogs = filteredLogs.filter(
      (log) => log.security && log.securityCategory === securityCategory
    )
  }

  // Limit to last N entries
  const visibleLogs = filteredLogs.slice(-MAX_VISIBLE_ENTRIES)

  const stats = getLogStats(filteredLogs)

  // Scroll tracking
  const handleScroll = React.useCallback(() => {
    const container = scrollContainerRef.current
    if (!container) return
    const { scrollTop, scrollHeight, clientHeight } = container
    setIsAtBottom(scrollHeight - scrollTop - clientHeight < 40)
  }, [])

  const scrollToBottom = React.useCallback(() => {
    const container = scrollContainerRef.current
    if (!container) return
    container.scrollTop = container.scrollHeight
    setIsAtBottom(true)
  }, [])

  // Auto-scroll when live tail is active
  React.useEffect(() => {
    if (filters.liveTail && isAtBottom) {
      scrollToBottom()
    }
  }, [visibleLogs.length, filters.liveTail, isAtBottom, scrollToBottom])

  const handleToggleEntry = React.useCallback((id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }, [])

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Sticky filter area: search + filters + presets + chips */}
      <LogSearch filters={filters} onFiltersChange={setFilters} />

      {/* Security view (visible when security filter is active) */}
      {filters.security && (
        <SecurityLogView
          logs={MOCK_LOGS}
          activeCategory={securityCategory}
          onCategorySelect={setSecurityCategory}
        />
      )}

      {/* Stats bar */}
      <LogStats
        totalLogs={stats.total}
        errorCount={stats.errors}
        warningCount={stats.warnings}
        securityCount={stats.securityEvents}
        logsPerSecond={42}
        timeRange={TIME_RANGE_LABELS[filters.timeRange] || filters.timeRange}
        isLiveTail={filters.liveTail}
      />

      {/* Column headers */}
      <div className="flex items-center gap-3 border-b border-border/30 bg-[#08080D] px-4 py-2">
        <span className="w-4 shrink-0" /> {/* Chevron spacer */}
        <span className="w-[120px] shrink-0 font-mono text-xs uppercase tracking-widest text-muted-foreground/30">
          Timestamp
        </span>
        <span className="w-16 shrink-0 font-mono text-xs uppercase tracking-widest text-muted-foreground/30">
          Level
        </span>
        <span className="w-[140px] shrink-0 font-mono text-xs uppercase tracking-widest text-muted-foreground/30">
          Service
        </span>
        <span className="min-w-0 flex-1 font-mono text-xs uppercase tracking-widest text-muted-foreground/30">
          Message
        </span>
      </div>

      {/* Log entries */}
      <div className="relative flex-1 overflow-hidden">
        {/* Live tail scanning animation */}
        {filters.liveTail && (
          <div className="pointer-events-none absolute inset-x-0 top-0 z-10 h-px">
            <div className="animate-scan h-px w-full bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
          </div>
        )}

        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="h-full overflow-y-auto"
        >
          {visibleLogs.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground/40">
              <span className="font-mono text-sm">No logs match your filters</span>
              <span className="font-mono text-xs">
                Try adjusting your search or filter criteria
              </span>
            </div>
          ) : (
            <div className="min-w-0">
              {visibleLogs.map((entry, index) => (
                <LogEntryRow
                  key={entry.id}
                  entry={entry}
                  isExpanded={expandedId === entry.id}
                  onToggle={() => handleToggleEntry(entry.id)}
                  isEven={index % 2 === 0}
                />
              ))}
            </div>
          )}
        </div>

        {/* Jump to bottom button */}
        {!isAtBottom && (
          <div className="absolute inset-x-0 bottom-4 flex justify-center">
            <Button
              variant="default"
              size="default"
              className="gap-2 font-mono text-sm shadow-lg glow-matrix"
              onClick={scrollToBottom}
            >
              <ArrowDown className="size-4" />
              Jump to latest
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
