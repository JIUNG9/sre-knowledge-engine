"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { MCPToolBadge } from "./mcp-tool-badge"
import type { InvestigationMessage } from "@/lib/mock-data/ai-investigation"
import {
  Bot,
  ChevronDown,
  ChevronRight,
  Send,
  User,
  Terminal,
} from "lucide-react"

// ---- Timestamp formatter ----

function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })
}

// ---- Tool call block (collapsible) ----

interface ToolCallBlockProps {
  message: InvestigationMessage
}

function ToolCallBlock({ message }: ToolCallBlockProps) {
  const [expanded, setExpanded] = React.useState(false)
  const tool = message.toolCall
  if (!tool) return null

  return (
    <div className="rounded-md border border-border/50 bg-[#0A0A0A]">
      {/* Collapsible header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left font-mono text-[11px] transition-colors hover:bg-muted/20"
      >
        {expanded ? (
          <ChevronDown className="size-3 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-3 shrink-0 text-muted-foreground" />
        )}
        <Terminal className="size-3 shrink-0 text-[#00B8FF]" />
        <span className="flex-1 truncate text-muted-foreground">
          {message.content}
        </span>
        <MCPToolBadge
          toolName={tool.toolName}
          status={tool.status}
          durationMs={tool.durationMs}
          description={tool.description}
        />
      </button>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t border-border/30 px-3 py-2">
          {tool.input && (
            <div className="mb-2">
              <span className="font-mono text-[9px] font-medium uppercase tracking-wider text-muted-foreground">
                Input
              </span>
              <pre className="mt-1 overflow-x-auto whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-[#00B8FF]/80">
                {tool.input}
              </pre>
            </div>
          )}
          {tool.output && (
            <div>
              <span className="font-mono text-[9px] font-medium uppercase tracking-wider text-muted-foreground">
                Output
              </span>
              <pre className="mt-1 overflow-x-auto whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-[#00FF88]/80">
                {tool.output}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---- Message item ----

interface MessageItemProps {
  message: InvestigationMessage
}

function MessageItem({ message }: MessageItemProps) {
  if (message.role === "tool") {
    return (
      <div className="pl-8">
        <ToolCallBlock message={message} />
      </div>
    )
  }

  const isUser = message.role === "user"

  return (
    <div className="flex gap-3">
      {/* Avatar */}
      <div
        className={cn(
          "flex size-6 shrink-0 items-center justify-center rounded-sm",
          isUser ? "bg-muted" : "bg-[#00B8FF]/10"
        )}
      >
        {isUser ? (
          <User className="size-3 text-muted-foreground" />
        ) : (
          <Bot className="size-3 text-[#00B8FF]" />
        )}
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] font-medium text-foreground">
            {isUser ? "You" : "Aegis AI"}
          </span>
          <span className="font-mono text-[9px] text-muted-foreground">
            {formatTimestamp(message.timestamp)}
          </span>
        </div>
        <div className="mt-1 font-mono text-[11px] leading-relaxed text-muted-foreground whitespace-pre-wrap">
          {message.content.split("\n").map((line, i) => {
            // Bold markdown sections
            if (line.startsWith("**") && line.endsWith("**")) {
              return (
                <div key={i} className="mt-1 font-medium text-foreground">
                  {line.replace(/\*\*/g, "")}
                </div>
              )
            }
            // Lines containing bold
            if (line.includes("**")) {
              const parts = line.split(/(\*\*.*?\*\*)/)
              return (
                <div key={i}>
                  {parts.map((part, j) =>
                    part.startsWith("**") && part.endsWith("**") ? (
                      <span key={j} className="font-medium text-foreground">
                        {part.replace(/\*\*/g, "")}
                      </span>
                    ) : (
                      <span key={j}>{part}</span>
                    )
                  )}
                </div>
              )
            }
            return <div key={i}>{line || "\u00A0"}</div>
          })}
        </div>
      </div>
    </div>
  )
}

// ---- Blinking cursor (loading state) ----

function ThinkingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="flex size-6 shrink-0 items-center justify-center rounded-sm bg-[#00B8FF]/10">
        <Bot className="size-3 text-[#00B8FF]" />
      </div>
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] font-medium text-foreground">
          Aegis AI
        </span>
        <span className="inline-block font-mono text-[11px] text-[#00B8FF]">
          investigating
          <span className="inline-block animate-pulse">_</span>
        </span>
      </div>
    </div>
  )
}

// ---- Main component ----

interface InvestigationChatProps {
  messages: InvestigationMessage[]
  isRunning?: boolean
  className?: string
}

export function InvestigationChat({
  messages,
  isRunning = false,
  className,
}: InvestigationChatProps) {
  const [input, setInput] = React.useState("")
  const scrollRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages.length])

  return (
    <div className={cn("flex flex-col", className)}>
      {/* Messages area */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-4 overflow-y-auto rounded-md border border-border/50 bg-[#0A0A0A] p-4"
        style={{ maxHeight: "400px" }}
      >
        {messages.map((msg) => (
          <MessageItem key={msg.id} message={msg} />
        ))}
        {isRunning && <ThinkingIndicator />}
      </div>

      {/* Input area */}
      <div className="mt-3 flex items-center gap-2">
        <div className="relative flex-1">
          <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 font-mono text-[10px] text-[#00B8FF]">
            &gt;
          </span>
          <Input
            placeholder="Ask a follow-up question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="h-8 pl-6 font-mono text-xs bg-[#0A0A0A] border-border/50"
            onKeyDown={(e) => {
              if (e.key === "Enter" && input.trim()) {
                setInput("")
              }
            }}
          />
        </div>
        <Button
          size="icon-sm"
          variant="ghost"
          className="shrink-0 text-muted-foreground hover:text-[#00B8FF]"
          onClick={() => {
            if (input.trim()) setInput("")
          }}
        >
          <Send className="size-3.5" />
        </Button>
      </div>
    </div>
  )
}
