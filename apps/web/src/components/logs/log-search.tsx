"use client"

import * as React from "react"
import {
  Search,
  X,
  Clock,
  Shield,
  Radio,
  ChevronDown,
  Check,
  Bookmark,
  Zap,
  AlertTriangle,
  KeyRound,
  Database,
  Filter,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import type { LogLevel } from "@/lib/mock-data/logs"
import { SERVICE_LIST, LOG_LEVEL_CONFIG } from "@/lib/mock-data/logs"
import { SAVED_QUERIES, type SavedQuery } from "@/lib/mock-data/saved-queries"

const ALL_LEVELS: LogLevel[] = ["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"]

const TIME_RANGES = [
  { label: "Last 15m", value: "15m" },
  { label: "Last 1h", value: "1h" },
  { label: "Last 6h", value: "6h" },
  { label: "Last 24h", value: "24h" },
  { label: "Last 7d", value: "7d" },
  { label: "Custom", value: "custom" },
] as const

interface QuickPreset {
  id: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  filters: LogFilters
}

const QUICK_PRESETS: QuickPreset[] = [
  {
    id: "prod-errors",
    label: "Production Errors",
    icon: AlertTriangle,
    filters: {
      search: "",
      levels: ["ERROR", "FATAL"],
      services: [],
      timeRange: "1h",
      liveTail: false,
      security: false,
    },
  },
  {
    id: "auth-failures",
    label: "Auth Failures",
    icon: KeyRound,
    filters: {
      search: "failed login|auth|login failed|account locked|brute force",
      levels: [],
      services: ["auth-service"],
      timeRange: "24h",
      liveTail: false,
      security: true,
    },
  },
  {
    id: "slow-queries",
    label: "Slow Queries",
    icon: Database,
    filters: {
      search: "slow query|Slow query",
      levels: ["WARN", "ERROR"],
      services: [],
      timeRange: "24h",
      liveTail: false,
      security: false,
    },
  },
  {
    id: "security-events",
    label: "Security Events",
    icon: Shield,
    filters: {
      search: "",
      levels: [],
      services: [],
      timeRange: "24h",
      liveTail: false,
      security: true,
    },
  },
]

export interface LogFilters {
  search: string
  levels: LogLevel[]
  services: string[]
  timeRange: string
  liveTail: boolean
  security: boolean
}

interface LogSearchProps {
  filters: LogFilters
  onFiltersChange: (filters: LogFilters) => void
}

/* ---------- Multi-select dropdown (bigger, Datadog style) ---------- */
function MultiSelectDropdown({
  label,
  icon: Icon,
  items,
  selectedItems,
  onToggle,
  renderItem,
}: {
  label: string
  icon?: React.ComponentType<{ className?: string }>
  items: string[]
  selectedItems: string[]
  onToggle: (item: string) => void
  renderItem?: (item: string, selected: boolean) => React.ReactNode
}) {
  const [open, setOpen] = React.useState(false)
  const selectedCount = selectedItems.length

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <button
            className={cn(
              "inline-flex h-10 items-center gap-2 rounded-lg border px-3.5 text-sm font-medium transition-all outline-none",
              selectedCount > 0
                ? "border-primary/40 bg-primary/5 text-primary hover:bg-primary/10"
                : "border-border/60 bg-[#0D0D14] text-muted-foreground hover:border-border hover:bg-[#111118] hover:text-foreground"
            )}
          />
        }
      >
        {Icon && <Icon className="size-4 shrink-0 opacity-70" />}
        <span className="font-mono text-sm">{label}</span>
        {selectedCount > 0 && (
          <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary/20 px-1.5 font-mono text-xs font-bold text-primary">
            {selectedCount}
          </span>
        )}
        <ChevronDown className={cn("size-3.5 opacity-50 transition-transform", open && "rotate-180")} />
      </PopoverTrigger>
      <PopoverContent
        className="w-56 p-1.5"
        align="start"
        sideOffset={6}
      >
        <div className="mb-1.5 px-2 py-1">
          <span className="font-mono text-xs font-medium uppercase tracking-widest text-muted-foreground/50">
            {label}
          </span>
        </div>
        <div className="max-h-72 overflow-y-auto">
          {items.map((item) => {
            const selected = selectedItems.includes(item)
            return (
              <button
                key={item}
                onClick={() => onToggle(item)}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-sm outline-none transition-colors",
                  selected
                    ? "bg-primary/10 text-foreground"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                )}
              >
                <div
                  className={cn(
                    "flex size-4 shrink-0 items-center justify-center rounded border transition-colors",
                    selected
                      ? "border-primary bg-primary"
                      : "border-border/80 bg-transparent"
                  )}
                >
                  {selected && <Check className="size-3 text-primary-foreground" />}
                </div>
                {renderItem ? (
                  renderItem(item, selected)
                ) : (
                  <span className="truncate font-mono text-sm">{item}</span>
                )}
              </button>
            )
          })}
        </div>
        {selectedCount > 0 && (
          <div className="mt-1.5 border-t border-border/30 pt-1.5">
            <button
              onClick={() => {
                for (const item of selectedItems) {
                  onToggle(item)
                }
              }}
              className="w-full rounded-md px-2.5 py-1.5 text-left font-mono text-xs text-muted-foreground/60 transition-colors hover:text-foreground"
            >
              Clear selection
            </button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}

/* ---------- Main LogSearch component ---------- */
export function LogSearch({ filters, onFiltersChange }: LogSearchProps) {
  const [savedQueriesOpen, setSavedQueriesOpen] = React.useState(false)
  const [activePreset, setActivePreset] = React.useState<string | null>(null)

  const updateFilter = <K extends keyof LogFilters>(key: K, value: LogFilters[K]) => {
    setActivePreset(null)
    onFiltersChange({ ...filters, [key]: value })
  }

  const toggleLevel = (level: string) => {
    const current = filters.levels
    const next = current.includes(level as LogLevel)
      ? current.filter((l) => l !== level)
      : [...current, level as LogLevel]
    setActivePreset(null)
    onFiltersChange({ ...filters, levels: next })
  }

  const toggleService = (service: string) => {
    const current = filters.services
    const next = current.includes(service)
      ? current.filter((s) => s !== service)
      : [...current, service]
    setActivePreset(null)
    onFiltersChange({ ...filters, services: next })
  }

  const applySavedQuery = (query: SavedQuery) => {
    setActivePreset(null)
    onFiltersChange({
      search: query.filters.search || "",
      levels: (query.filters.levels as LogLevel[]) || [],
      services: query.filters.services || [],
      timeRange: query.filters.timeRange || "24h",
      liveTail: false,
      security: query.filters.security || false,
    })
    setSavedQueriesOpen(false)
  }

  const applyPreset = (preset: QuickPreset) => {
    if (activePreset === preset.id) {
      clearFilters()
      return
    }
    setActivePreset(preset.id)
    onFiltersChange({ ...preset.filters })
  }

  const clearFilters = () => {
    setActivePreset(null)
    onFiltersChange({
      search: "",
      levels: [],
      services: [],
      timeRange: "24h",
      liveTail: false,
      security: false,
    })
  }

  const hasActiveFilters =
    filters.search !== "" ||
    filters.levels.length > 0 ||
    filters.services.length > 0 ||
    filters.timeRange !== "24h" ||
    filters.security

  const activeFilterChips: { key: string; label: string; color?: string; onRemove: () => void }[] = []

  for (const level of filters.levels) {
    const config = LOG_LEVEL_CONFIG[level]
    activeFilterChips.push({
      key: `level-${level}`,
      label: `Level: ${level}`,
      color: config.color,
      onRemove: () => toggleLevel(level),
    })
  }
  for (const service of filters.services) {
    activeFilterChips.push({
      key: `service-${service}`,
      label: `Service: ${service}`,
      onRemove: () => toggleService(service),
    })
  }
  if (filters.timeRange !== "24h") {
    const rangeLabel = TIME_RANGES.find((t) => t.value === filters.timeRange)?.label || filters.timeRange
    activeFilterChips.push({
      key: "time",
      label: `Time: ${rangeLabel}`,
      onRemove: () => updateFilter("timeRange", "24h"),
    })
  }
  if (filters.security) {
    activeFilterChips.push({
      key: "security",
      label: "Security Only",
      color: "#FF4444",
      onRemove: () => updateFilter("security", false),
    })
  }
  if (filters.search) {
    activeFilterChips.push({
      key: "search",
      label: `Search: "${filters.search.length > 24 ? filters.search.slice(0, 24) + "..." : filters.search}"`,
      onRemove: () => updateFilter("search", ""),
    })
  }

  return (
    <div className="sticky top-0 z-20 border-b border-border/40 bg-[#0A0A0F]/95 backdrop-blur-sm">
      {/* Row 1: Search input */}
      <div className="px-5 pt-4 pb-3">
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-muted-foreground/40" />
          <Input
            type="text"
            placeholder="Search logs... (full-text, regex, or KQL)"
            value={filters.search}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateFilter("search", e.target.value)}
            className="h-12 rounded-lg border-border/50 bg-[#0D0D14] pl-12 pr-20 font-mono text-sm placeholder:text-muted-foreground/30 focus-visible:border-primary/40 focus-visible:ring-primary/20 focus-visible:shadow-[0_0_20px_rgba(0,255,136,0.08)]"
          />
          <kbd className="pointer-events-none absolute top-1/2 right-3 flex h-6 -translate-y-1/2 items-center gap-0.5 rounded-md border border-border/40 bg-muted/50 px-2 font-mono text-xs text-muted-foreground/40">
            <span className="text-xs">&#8984;</span>K
          </kbd>
        </div>
      </div>

      {/* Row 2: Filter dropdowns */}
      <div className="flex flex-wrap items-center gap-2.5 px-5 pb-3">
        <Filter className="size-4 text-muted-foreground/40" />

        {/* Level multi-select */}
        <MultiSelectDropdown
          label="Level"
          items={ALL_LEVELS}
          selectedItems={filters.levels}
          onToggle={toggleLevel}
          renderItem={(item) => {
            const config = LOG_LEVEL_CONFIG[item as LogLevel]
            return (
              <span className="flex items-center gap-2 font-mono text-sm">
                <span
                  className="inline-block size-2.5 rounded-full"
                  style={{ backgroundColor: config.color }}
                />
                {item}
              </span>
            )
          }}
        />

        {/* Service multi-select */}
        <MultiSelectDropdown
          label="Service"
          items={SERVICE_LIST}
          selectedItems={filters.services}
          onToggle={toggleService}
        />

        {/* Time range */}
        <Popover>
          <PopoverTrigger
            render={
              <button
                className={cn(
                  "inline-flex h-10 items-center gap-2 rounded-lg border px-3.5 text-sm font-medium transition-all outline-none",
                  filters.timeRange !== "24h"
                    ? "border-primary/40 bg-primary/5 text-primary hover:bg-primary/10"
                    : "border-border/60 bg-[#0D0D14] text-muted-foreground hover:border-border hover:bg-[#111118] hover:text-foreground"
                )}
              />
            }
          >
            <Clock className="size-4 opacity-70" />
            <span className="font-mono text-sm">
              {TIME_RANGES.find((t) => t.value === filters.timeRange)?.label || "Last 24h"}
            </span>
            <ChevronDown className="size-3.5 opacity-50" />
          </PopoverTrigger>
          <PopoverContent className="w-44 p-1.5" align="start" sideOffset={6}>
            <div className="mb-1.5 px-2 py-1">
              <span className="font-mono text-xs font-medium uppercase tracking-widest text-muted-foreground/50">
                Time Range
              </span>
            </div>
            {TIME_RANGES.map((range) => (
              <button
                key={range.value}
                onClick={() => updateFilter("timeRange", range.value)}
                className={cn(
                  "flex w-full items-center justify-between rounded-md px-2.5 py-2 text-sm outline-none transition-colors",
                  filters.timeRange === range.value
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                )}
              >
                <span className="font-mono text-sm">{range.label}</span>
                {filters.timeRange === range.value && (
                  <Check className="size-3.5 text-primary" />
                )}
              </button>
            ))}
          </PopoverContent>
        </Popover>

        {/* Divider */}
        <div className="h-6 w-px bg-border/30" />

        {/* Live Tail toggle */}
        <button
          onClick={() => updateFilter("liveTail", !filters.liveTail)}
          className={cn(
            "inline-flex h-10 items-center gap-2.5 rounded-lg border px-4 text-sm font-medium transition-all outline-none",
            filters.liveTail
              ? "border-primary/40 bg-primary/10 text-primary"
              : "border-border/60 bg-[#0D0D14] text-muted-foreground hover:border-border hover:bg-[#111118] hover:text-foreground"
          )}
        >
          <span className="relative flex size-2.5">
            {filters.liveTail && (
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-75" />
            )}
            <span
              className={cn(
                "relative inline-flex size-2.5 rounded-full",
                filters.liveTail ? "bg-primary" : "bg-muted-foreground/40"
              )}
            />
          </span>
          <span className="font-mono text-sm">Live Tail</span>
        </button>

        {/* Security filter */}
        <button
          onClick={() => updateFilter("security", !filters.security)}
          className={cn(
            "inline-flex h-10 items-center gap-2 rounded-lg border px-3.5 text-sm font-medium transition-all outline-none",
            filters.security
              ? "border-[#FF4444]/40 bg-[#FF4444]/10 text-[#FF4444]"
              : "border-border/60 bg-[#0D0D14] text-muted-foreground hover:border-border hover:bg-[#111118] hover:text-foreground"
          )}
        >
          <Shield className="size-4" />
          <span className="font-mono text-sm">Security</span>
        </button>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Saved queries */}
        <Popover open={savedQueriesOpen} onOpenChange={setSavedQueriesOpen}>
          <PopoverTrigger
            render={
              <button className="inline-flex h-10 items-center gap-2 rounded-lg border border-border/60 bg-[#0D0D14] px-3.5 text-sm font-medium text-muted-foreground transition-all outline-none hover:border-border hover:bg-[#111118] hover:text-foreground" />
            }
          >
            <Bookmark className="size-4 opacity-70" />
            <span className="font-mono text-sm">Saved</span>
            <ChevronDown className="size-3.5 opacity-50" />
          </PopoverTrigger>
          <PopoverContent className="w-72 p-1.5" align="end" sideOffset={6}>
            <div className="mb-1.5 px-2.5 py-1.5">
              <span className="font-mono text-xs font-medium uppercase tracking-widest text-muted-foreground/50">
                Saved Queries
              </span>
            </div>
            {SAVED_QUERIES.map((query) => (
              <button
                key={query.id}
                onClick={() => applySavedQuery(query)}
                className="flex w-full flex-col gap-1 rounded-md px-2.5 py-2.5 text-left outline-none transition-colors hover:bg-muted/50"
              >
                <span className="font-mono text-sm font-medium text-foreground/90">
                  {query.name}
                </span>
                <span className="font-mono text-xs text-muted-foreground/50">
                  {query.description}
                </span>
              </button>
            ))}
          </PopoverContent>
        </Popover>
      </div>

      {/* Row 3: Quick filter presets */}
      <div className="flex items-center gap-2 border-t border-border/20 px-5 py-2.5">
        <Zap className="size-3.5 text-muted-foreground/30" />
        <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground/30">
          Quick
        </span>
        {QUICK_PRESETS.map((preset) => {
          const PresetIcon = preset.icon
          const isActive = activePreset === preset.id
          return (
            <button
              key={preset.id}
              onClick={() => applyPreset(preset)}
              className={cn(
                "inline-flex h-8 items-center gap-1.5 rounded-md border px-3 font-mono text-xs font-medium transition-all outline-none",
                isActive
                  ? "border-primary/50 bg-primary/15 text-primary shadow-[0_0_8px_rgba(0,255,136,0.1)]"
                  : "border-border/40 bg-[#0D0D14] text-muted-foreground/70 hover:border-border/60 hover:bg-[#111118] hover:text-foreground"
              )}
            >
              <PresetIcon className="size-3.5" />
              {preset.label}
            </button>
          )
        })}
      </div>

      {/* Row 4: Active filter chips */}
      <div className="flex items-center gap-2 border-t border-border/20 px-5 py-2.5">
        {activeFilterChips.length === 0 ? (
          <span className="font-mono text-xs text-muted-foreground/30">
            No filters applied
          </span>
        ) : (
          <>
            {activeFilterChips.map((chip) => (
              <span
                key={chip.key}
                className="inline-flex h-7 items-center gap-1.5 rounded-md border border-border/40 bg-[#111118] px-2.5 font-mono text-xs text-foreground/80"
              >
                {chip.color && (
                  <span
                    className="inline-block size-2 rounded-full"
                    style={{ backgroundColor: chip.color }}
                  />
                )}
                {chip.label}
                <button
                  onClick={chip.onRemove}
                  className="ml-0.5 rounded-sm p-0.5 text-muted-foreground/50 transition-colors outline-none hover:bg-muted/50 hover:text-foreground"
                >
                  <X className="size-3" />
                </button>
              </span>
            ))}
            <button
              onClick={clearFilters}
              className="ml-1 inline-flex h-7 items-center gap-1 rounded-md px-2 font-mono text-xs text-muted-foreground/50 transition-colors hover:text-foreground"
            >
              <X className="size-3" />
              Clear All
            </button>
          </>
        )}
      </div>
    </div>
  )
}
