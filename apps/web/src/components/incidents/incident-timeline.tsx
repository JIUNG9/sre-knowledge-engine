"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { TimelineEvent, TimelineEventType } from "@/lib/mock-data/incidents"
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  Eye,
  MessageSquare,
  ArrowUpCircle,
  RefreshCw,
  Send,
} from "lucide-react"

// ---- Event type config ----

function getEventConfig(type: TimelineEventType) {
  switch (type) {
    case "alert_fired":
      return { icon: Bell, color: "#FF4444", label: "Alert Fired" }
    case "acknowledged":
      return { icon: Eye, color: "#00B8FF", label: "Acknowledged" }
    case "status_change":
      return { icon: RefreshCw, color: "#FFB020", label: "Status Change" }
    case "note_added":
      return { icon: MessageSquare, color: "#888", label: "Note Added" }
    case "escalated":
      return { icon: ArrowUpCircle, color: "#FF8C00", label: "Escalated" }
    case "resolved":
      return { icon: CheckCircle2, color: "#00FF88", label: "Resolved" }
  }
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)

  if (diffMin < 1) return "just now"
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHours = Math.floor(diffMin / 60)
  if (diffHours < 24) return `${diffHours}h ${diffMin % 60}m ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

function formatAbsoluteTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  })
}

// ---- Timeline Node ----

interface TimelineNodeProps {
  event: TimelineEvent
  isLast: boolean
}

function TimelineNode({ event, isLast }: TimelineNodeProps) {
  const config = getEventConfig(event.type)
  const Icon = config.icon

  return (
    <div className="relative flex gap-3">
      {/* Vertical line + node */}
      <div className="flex flex-col items-center">
        <div
          className="flex size-7 shrink-0 items-center justify-center rounded-full ring-2 ring-background"
          style={{ backgroundColor: `${config.color}20` }}
        >
          <Icon className="size-3.5" style={{ color: config.color }} />
        </div>
        {!isLast && (
          <div className="w-px flex-1 bg-border" />
        )}
      </div>

      {/* Content */}
      <div className={cn("min-w-0 pb-5", isLast && "pb-0")}>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-mono text-xs font-medium text-foreground">
            {event.actor}
          </span>
          <span
            className="rounded-sm px-1 py-0.5 font-mono text-[9px] font-medium"
            style={{
              backgroundColor: `${config.color}15`,
              color: config.color,
            }}
          >
            {config.label}
          </span>
          <span
            className="font-mono text-[10px] text-muted-foreground"
            title={formatAbsoluteTime(event.timestamp)}
          >
            {formatTimestamp(event.timestamp)}
          </span>
        </div>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
          {event.message}
        </p>
        {event.metadata && (
          <div className="mt-1 flex flex-wrap gap-1">
            {Object.entries(event.metadata).map(([k, v]) => (
              <span
                key={k}
                className="rounded-sm bg-muted px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground"
              >
                {k}: {v}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ---- Main Timeline ----

interface IncidentTimelineProps {
  events: TimelineEvent[]
  className?: string
  showAddNote?: boolean
}

export function IncidentTimeline({
  events,
  className,
  showAddNote = false,
}: IncidentTimelineProps) {
  const [noteText, setNoteText] = React.useState("")

  return (
    <div className={cn("space-y-0", className)}>
      {events.map((event, i) => (
        <TimelineNode
          key={event.id}
          event={event}
          isLast={i === events.length - 1 && !showAddNote}
        />
      ))}
      {showAddNote && (
        <div className="relative flex gap-3">
          {/* Node */}
          <div className="flex flex-col items-center">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted ring-2 ring-background">
              <MessageSquare className="size-3.5 text-muted-foreground" />
            </div>
          </div>
          {/* Input */}
          <div className="flex flex-1 items-center gap-2">
            <Input
              placeholder="Add a note..."
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              className="h-7 font-mono text-xs"
              onKeyDown={(e) => {
                if (e.key === "Enter" && noteText.trim()) {
                  setNoteText("")
                }
              }}
            />
            <Button
              size="icon-sm"
              variant="ghost"
              className="shrink-0 text-muted-foreground hover:text-primary"
              onClick={() => {
                if (noteText.trim()) setNoteText("")
              }}
            >
              <Send className="size-3.5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
