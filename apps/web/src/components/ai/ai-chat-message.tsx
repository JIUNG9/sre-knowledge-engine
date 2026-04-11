"use client"

import * as React from "react"
import {
  Bot,
  User,
  ChevronDown,
  ChevronRight,
  Wrench,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { type ChatMessage, type ToolCall, type ToolCallStatus } from "@/lib/mock-data/ai-chat"

// ---- Relative time helper ----

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return "just now"
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

// ---- Tool call status icon ----

const statusConfig: Record<
  ToolCallStatus,
  { icon: React.ElementType; className: string; label: string }
> = {
  running: {
    icon: Loader2,
    className: "text-amber-400 animate-spin",
    label: "Running",
  },
  success: {
    icon: CheckCircle2,
    className: "text-emerald-400",
    label: "Success",
  },
  failed: {
    icon: XCircle,
    className: "text-red-400",
    label: "Failed",
  },
}

// ---- Tool call block ----

function ToolCallBlock({ toolCall }: { toolCall: ToolCall }) {
  const [expanded, setExpanded] = React.useState(false)
  const config = statusConfig[toolCall.status]
  const StatusIcon = config.icon

  const previewLines = toolCall.result
    ? toolCall.result.split("\n").slice(0, 3).join("\n")
    : ""
  const hasMore = toolCall.result
    ? toolCall.result.split("\n").length > 3
    : false

  return (
    <div className="my-1.5 overflow-hidden rounded-md bg-muted/70 text-xs">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left transition-colors hover:bg-muted"
      >
        <Wrench className="size-3 shrink-0 text-muted-foreground" />
        <span className="font-mono text-muted-foreground">{toolCall.toolName}</span>
        <StatusIcon className={cn("ml-auto size-3 shrink-0", config.className)} />
        <span className={cn("text-[11px]", config.className)}>{config.label}</span>
        <span className="text-[11px] text-muted-foreground">
          {toolCall.durationMs}ms
        </span>
        {toolCall.result && (
          expanded ? (
            <ChevronDown className="size-3 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-3 shrink-0 text-muted-foreground" />
          )
        )}
      </button>
      {toolCall.result && (
        <div className="border-t border-border/50 px-2.5 py-1.5">
          <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-muted-foreground">
            {expanded ? toolCall.result : previewLines}
            {!expanded && hasMore && (
              <span className="text-primary/60">...</span>
            )}
          </pre>
        </div>
      )}
    </div>
  )
}

// ---- Markdown-lite renderer (bold, code, lists) ----

function renderContent(content: string) {
  const lines = content.split("\n")
  const elements: React.ReactNode[] = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    // Process inline formatting
    const processInline = (text: string): React.ReactNode[] => {
      const parts: React.ReactNode[] = []
      // Match **bold**, `code`, or plain text
      const regex = /(\*\*(.+?)\*\*|`([^`]+)`)/g
      let lastIndex = 0
      let match: RegExpExecArray | null

      while ((match = regex.exec(text)) !== null) {
        // Push text before match
        if (match.index > lastIndex) {
          parts.push(text.slice(lastIndex, match.index))
        }
        if (match[2]) {
          // Bold
          parts.push(
            <strong key={`b-${i}-${match.index}`} className="font-semibold text-foreground">
              {match[2]}
            </strong>
          )
        } else if (match[3]) {
          // Inline code
          parts.push(
            <code
              key={`c-${i}-${match.index}`}
              className="rounded bg-muted px-1 py-0.5 font-mono text-[12px] text-primary/80"
            >
              {match[3]}
            </code>
          )
        }
        lastIndex = match.index + match[0].length
      }
      if (lastIndex < text.length) {
        parts.push(text.slice(lastIndex))
      }
      return parts.length > 0 ? parts : [text]
    }

    if (line.startsWith("- ") || line.startsWith("* ")) {
      elements.push(
        <div key={i} className="flex gap-1.5 pl-1">
          <span className="shrink-0 text-muted-foreground">-</span>
          <span>{processInline(line.slice(2))}</span>
        </div>
      )
    } else if (/^\d+\.\s/.test(line)) {
      const numMatch = line.match(/^(\d+)\.\s(.*)/)
      if (numMatch) {
        elements.push(
          <div key={i} className="flex gap-1.5 pl-1">
            <span className="shrink-0 text-muted-foreground">{numMatch[1]}.</span>
            <span>{processInline(numMatch[2])}</span>
          </div>
        )
      }
    } else if (line === "") {
      elements.push(<div key={i} className="h-2" />)
    } else {
      elements.push(
        <div key={i}>{processInline(line)}</div>
      )
    }
  }

  return elements
}

// ---- Main message component ----

export function AIChatMessage({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user"

  return (
    <div
      className={cn(
        "flex gap-2.5 px-4 py-2",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {/* AI avatar */}
      {!isUser && (
        <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/15 mt-0.5">
          <Bot className="size-4 text-primary" />
        </div>
      )}

      <div
        className={cn(
          "flex max-w-[340px] flex-col gap-1",
          isUser ? "items-end" : "items-start"
        )}
      >
        {/* Message bubble */}
        <div
          className={cn(
            "rounded-lg px-3 py-2 text-[14px] leading-relaxed",
            isUser
              ? "bg-primary/10 text-foreground"
              : "bg-background text-foreground"
          )}
        >
          {isUser ? (
            <span>{message.content}</span>
          ) : (
            <div className="space-y-0.5">{renderContent(message.content)}</div>
          )}

          {/* Tool calls */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <div className="mt-2 space-y-1">
              {message.toolCalls.map((tc) => (
                <ToolCallBlock key={tc.id} toolCall={tc} />
              ))}
            </div>
          )}
        </div>

        {/* Timestamp */}
        <span className="px-1 text-[11px] text-muted-foreground/60">
          {relativeTime(message.timestamp)}
        </span>
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted mt-0.5">
          <User className="size-4 text-muted-foreground" />
        </div>
      )}
    </div>
  )
}
