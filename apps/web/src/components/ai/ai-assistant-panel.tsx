"use client"

import * as React from "react"
import { X, Sparkles, Send, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useAIStore } from "@/lib/stores/ai-store"
import { AIChatMessage } from "@/components/ai/ai-chat-message"
import { SystemSummary } from "@/components/ai/system-summary"

export function AIAssistantPanel() {
  const {
    isOpen,
    closePanel,
    messages,
    currentModule,
    sessionTokens,
    sessionCost,
    isLoading,
    sendMessage,
  } = useAIStore()

  const [input, setInput] = React.useState("")
  const messagesEndRef = React.useRef<HTMLDivElement>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom when messages change
  React.useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages, isLoading])

  // Focus textarea when panel opens
  React.useEffect(() => {
    if (isOpen && textareaRef.current) {
      setTimeout(() => textareaRef.current?.focus(), 300)
    }
  }, [isOpen])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return
    sendMessage(trimmed)
    setInput("")
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    // Auto-resize
    const el = e.target
    el.style.height = "auto"
    const maxHeight = 6 * 24 // ~6 lines
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`
  }

  const formatTokens = (tokens: number): string => {
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`
    return tokens.toString()
  }

  // Estimate tokens for current input (~4 chars per token)
  const estimatedTokens = Math.max(Math.ceil(input.length / 4) + 1500, 0)
  const estimatedCost = estimatedTokens * 0.000005

  return (
    <>
      {/* Backdrop overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 transition-opacity duration-300"
          onClick={closePanel}
          aria-hidden="true"
        />
      )}

      {/* Panel */}
      <aside
        className={cn(
          "fixed top-0 right-0 z-50 flex h-full w-[420px] flex-col bg-card shadow-2xl transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
        role="complementary"
        aria-label="AI Assistant"
      >
        {/* Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex size-7 items-center justify-center rounded-md bg-primary/15">
              <Sparkles className="size-4 text-primary" />
            </div>
            <h2 className="font-heading text-sm font-semibold text-foreground">
              AI Assistant
            </h2>
            <Badge variant="secondary" className="text-[11px]">
              {currentModule}
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={closePanel}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="size-4" />
            <span className="sr-only">Close AI panel</span>
          </Button>
        </div>

        {/* System summary */}
        <SystemSummary />

        {/* Chat messages */}
        <ScrollArea className="flex-1 overflow-y-auto">
          <div className="py-2">
            {messages.map((msg) => (
              <AIChatMessage key={msg.id} message={msg} />
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <div className="flex gap-2.5 px-4 py-2">
                <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/15">
                  <Loader2 className="size-4 animate-spin text-primary" />
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-background px-3 py-2">
                  <span className="text-[13px] text-muted-foreground">
                    Analyzing...
                  </span>
                  <span className="flex gap-1">
                    <span className="size-1.5 animate-pulse rounded-full bg-primary/40" />
                    <span className="size-1.5 animate-pulse rounded-full bg-primary/40 [animation-delay:150ms]" />
                    <span className="size-1.5 animate-pulse rounded-full bg-primary/40 [animation-delay:300ms]" />
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Token usage footer */}
        <div className="shrink-0 border-t border-border/50 px-4 py-1.5">
          <span className="font-mono text-[11px] text-muted-foreground/60">
            Session: {formatTokens(sessionTokens)} tokens (~${sessionCost.toFixed(2)})
          </span>
        </div>

        {/* Input area */}
        <div className="shrink-0 border-t border-border bg-card px-4 pb-4 pt-2">
          {/* Token estimate */}
          {input.length > 0 && (
            <div className="mb-1.5 text-right">
              <span className="font-mono text-[11px] text-muted-foreground/50">
                Estimated: ~{formatTokens(estimatedTokens)} tokens (~${estimatedCost.toFixed(2)})
              </span>
            </div>
          )}

          <div className="flex items-end gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your infrastructure..."
              rows={2}
              className={cn(
                "flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-[14px] leading-relaxed text-foreground outline-none transition-colors",
                "placeholder:text-muted-foreground/50",
                "focus:border-primary/50 focus:ring-2 focus:ring-primary/20",
                "disabled:cursor-not-allowed disabled:opacity-50"
              )}
              style={{ maxHeight: `${6 * 24}px` }}
              disabled={isLoading}
            />
            <Button
              size="icon"
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="shrink-0"
            >
              {isLoading ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Send className="size-4" />
              )}
              <span className="sr-only">Send message</span>
            </Button>
          </div>
        </div>
      </aside>
    </>
  )
}
