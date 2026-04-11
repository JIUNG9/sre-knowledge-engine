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
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Separator } from "@/components/ui/separator"
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

function MultiSelectCheckbox({
  label,
  items,
  selectedItems,
  onToggle,
  renderItem,
}: {
  label: string
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
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 font-mono text-xs"
          />
        }
      >
        {label}
        {selectedCount > 0 && (
          <Badge
            variant="secondary"
            className="h-4 min-w-4 rounded-full px-1 font-mono text-xs"
          >
            {selectedCount}
          </Badge>
        )}
        <ChevronDown className="size-3 text-muted-foreground" />
      </PopoverTrigger>
      <PopoverContent
        className="w-48 p-1"
        align="start"
      >
        <div className="max-h-64 overflow-y-auto">
          {items.map((item) => {
            const selected = selectedItems.includes(item)
            return (
              <button
                key={item}
                onClick={() => onToggle(item)}
                className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm outline-none hover:bg-muted/50"
              >
                <div
                  className={cn(
                    "flex size-3.5 shrink-0 items-center justify-center rounded-sm border",
                    selected
                      ? "border-primary bg-primary"
                      : "border-border"
                  )}
                >
                  {selected && <Check className="size-2.5 text-primary-foreground" />}
                </div>
                {renderItem ? (
                  renderItem(item, selected)
                ) : (
                  <span className="truncate font-mono text-xs">{item}</span>
                )}
              </button>
            )
          })}
        </div>
      </PopoverContent>
    </Popover>
  )
}

export function LogSearch({ filters, onFiltersChange }: LogSearchProps) {
  const [savedQueriesOpen, setSavedQueriesOpen] = React.useState(false)

  const updateFilter = <K extends keyof LogFilters>(key: K, value: LogFilters[K]) => {
    onFiltersChange({ ...filters, [key]: value })
  }

  const toggleLevel = (level: string) => {
    const current = filters.levels
    const next = current.includes(level as LogLevel)
      ? current.filter((l) => l !== level)
      : [...current, level as LogLevel]
    updateFilter("levels", next)
  }

  const toggleService = (service: string) => {
    const current = filters.services
    const next = current.includes(service)
      ? current.filter((s) => s !== service)
      : [...current, service]
    updateFilter("services", next)
  }

  const applySavedQuery = (query: SavedQuery) => {
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

  const clearFilters = () => {
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

  return (
    <div className="space-y-2 border-b border-border/50 bg-[#0B0B10] px-4 py-3">
      {/* Search bar */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground/50" />
          <Input
            type="text"
            placeholder="Search logs... (full-text, regex, or KQL)"
            value={filters.search}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => updateFilter("search", e.target.value)}
            className="h-11 bg-[#0A0A0F] pl-9 pr-16 font-mono text-sm placeholder:text-muted-foreground/40 focus-visible:border-primary/40 focus-visible:ring-primary/20 focus-visible:shadow-[0_0_12px_rgba(0,255,136,0.1)]"
          />
          <kbd className="pointer-events-none absolute top-1/2 right-2 flex h-5 -translate-y-1/2 items-center gap-0.5 rounded border border-border bg-muted px-1.5 font-mono text-xs text-muted-foreground/50">
            <span className="text-xs">&#8984;</span>K
          </kbd>
        </div>
      </div>

      {/* Filter controls */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Level filter */}
        <MultiSelectCheckbox
          label="Level"
          items={ALL_LEVELS}
          selectedItems={filters.levels}
          onToggle={toggleLevel}
          renderItem={(item) => {
            const config = LOG_LEVEL_CONFIG[item as LogLevel]
            return (
              <span className="flex items-center gap-1.5 font-mono text-xs">
                <span
                  className="inline-block size-2 rounded-full"
                  style={{ backgroundColor: config.color }}
                />
                {item}
              </span>
            )
          }}
        />

        {/* Service filter */}
        <MultiSelectCheckbox
          label="Service"
          items={SERVICE_LIST}
          selectedItems={filters.services}
          onToggle={toggleService}
        />

        {/* Time range */}
        <Popover>
          <PopoverTrigger
            render={
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 font-mono text-xs"
              />
            }
          >
            <Clock className="size-3" />
            {TIME_RANGES.find((t) => t.value === filters.timeRange)?.label || "Last 24h"}
            <ChevronDown className="size-3 text-muted-foreground" />
          </PopoverTrigger>
          <PopoverContent className="w-36 p-1" align="start">
            {TIME_RANGES.map((range) => (
              <button
                key={range.value}
                onClick={() => updateFilter("timeRange", range.value)}
                className={cn(
                  "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm outline-none hover:bg-muted/50",
                  filters.timeRange === range.value && "bg-primary/10 text-primary"
                )}
              >
                <span className="font-mono text-xs">{range.label}</span>
                {filters.timeRange === range.value && (
                  <Check className="ml-auto size-3 text-primary" />
                )}
              </button>
            ))}
          </PopoverContent>
        </Popover>

        <Separator orientation="vertical" className="h-5" />

        {/* Live tail toggle */}
        <Button
          variant={filters.liveTail ? "default" : "outline"}
          size="sm"
          className={cn(
            "gap-1.5 font-mono text-xs",
            filters.liveTail && "bg-primary/15 text-primary hover:bg-primary/20"
          )}
          onClick={() => updateFilter("liveTail", !filters.liveTail)}
        >
          <span className="relative flex size-2">
            {filters.liveTail && (
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-75" />
            )}
            <Radio
              className={cn(
                "relative size-2",
                filters.liveTail ? "text-primary" : "text-muted-foreground"
              )}
            />
          </span>
          Live Tail
        </Button>

        {/* Security filter */}
        <Button
          variant={filters.security ? "default" : "outline"}
          size="sm"
          className={cn(
            "gap-1.5 font-mono text-xs",
            filters.security && "bg-[#FF4444]/15 text-[#FF4444] hover:bg-[#FF4444]/20"
          )}
          onClick={() => updateFilter("security", !filters.security)}
        >
          <Shield className="size-3" />
          Security
        </Button>

        {/* Saved queries */}
        <Popover open={savedQueriesOpen} onOpenChange={setSavedQueriesOpen}>
          <PopoverTrigger
            render={
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 font-mono text-xs"
              />
            }
          >
            <Bookmark className="size-3" />
            Saved
            <ChevronDown className="size-3 text-muted-foreground" />
          </PopoverTrigger>
          <PopoverContent className="w-64 p-1" align="start">
            <div className="mb-1 px-2 py-1">
              <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground/60">
                Saved Queries
              </span>
            </div>
            {SAVED_QUERIES.map((query) => (
              <button
                key={query.id}
                onClick={() => applySavedQuery(query)}
                className="flex w-full flex-col gap-0.5 rounded-md px-2 py-1.5 text-left outline-none hover:bg-muted/50"
              >
                <span className="font-mono text-xs font-medium text-foreground/90">
                  {query.name}
                </span>
                <span className="font-mono text-xs text-muted-foreground/60">
                  {query.description}
                </span>
              </button>
            ))}
          </PopoverContent>
        </Popover>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Clear filters */}
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            className="gap-1 font-mono text-xs text-muted-foreground hover:text-foreground"
            onClick={clearFilters}
          >
            <X className="size-3" />
            Clear
          </Button>
        )}
      </div>

      {/* Active filter badges */}
      {hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-1.5">
          {filters.levels.map((level) => (
            <Badge
              key={level}
              variant="secondary"
              className="h-5 gap-1 rounded-sm px-1.5 font-mono text-xs"
            >
              <span
                className="inline-block size-1.5 rounded-full"
                style={{ backgroundColor: LOG_LEVEL_CONFIG[level].color }}
              />
              {level}
              <button
                onClick={() => toggleLevel(level)}
                className="ml-0.5 outline-none hover:text-foreground"
              >
                <X className="size-2.5" />
              </button>
            </Badge>
          ))}
          {filters.services.map((service) => (
            <Badge
              key={service}
              variant="secondary"
              className="h-5 gap-1 rounded-sm px-1.5 font-mono text-xs"
            >
              {service}
              <button
                onClick={() => toggleService(service)}
                className="ml-0.5 outline-none hover:text-foreground"
              >
                <X className="size-2.5" />
              </button>
            </Badge>
          ))}
          {filters.security && (
            <Badge
              variant="secondary"
              className="h-5 gap-1 rounded-sm bg-[#FF4444]/10 px-1.5 font-mono text-xs text-[#FF4444]"
            >
              <Shield className="size-2.5" />
              Security
            </Badge>
          )}
        </div>
      )}
    </div>
  )
}
