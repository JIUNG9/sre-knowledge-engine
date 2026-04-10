"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { RemediationSteps } from "./remediation-steps"
import { InvestigationChat } from "./investigation-chat"
import { MCPToolBadge } from "./mcp-tool-badge"
import type { AIInvestigation } from "@/lib/mock-data/ai-investigation"
import {
  Bot,
  Brain,
  ChevronDown,
  ChevronRight,
  Clock,
  Coins,
  RefreshCw,
  Server,
  Zap,
} from "lucide-react"

// ---- Confidence meter ----

interface ConfidenceMeterProps {
  score: number
}

function ConfidenceMeter({ score }: ConfidenceMeterProps) {
  const color =
    score >= 90
      ? "#00FF88"
      : score >= 75
        ? "#00B8FF"
        : score >= 60
          ? "#FFB020"
          : "#FF4444"

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${score}%`,
            backgroundColor: color,
          }}
        />
      </div>
      <span
        className="font-mono text-xs font-bold"
        style={{ color }}
      >
        {score}%
      </span>
    </div>
  )
}

// ---- Token usage display ----

interface TokenUsageDisplayProps {
  usage: AIInvestigation["tokenUsage"]
}

function TokenUsageDisplay({ usage }: TokenUsageDisplayProps) {
  function formatTokens(n: number): string {
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`
    return String(n)
  }

  return (
    <div className="flex flex-wrap items-center gap-3 font-mono text-xs text-muted-foreground">
      <span>
        <span className="text-foreground/60">in:</span> {formatTokens(usage.input)}
      </span>
      <span>
        <span className="text-foreground/60">out:</span> {formatTokens(usage.output)}
      </span>
      <span>
        <span className="text-foreground/60">cached:</span>{" "}
        <span className="text-[#00B8FF]">{formatTokens(usage.cached)}</span>
      </span>
      <span className="flex items-center gap-1">
        <Coins className="size-2.5" />~${usage.estimatedCost.toFixed(2)}
      </span>
    </div>
  )
}

// ---- Loading state ----

function InvestigationLoading() {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="relative">
        <Bot className="size-8 text-[#00B8FF]" />
        <span className="absolute -right-1 -top-1 inline-block size-2.5 animate-pulse rounded-full bg-[#00B8FF]" />
      </div>
      <div className="mt-4 font-mono text-xs text-foreground">
        <span>Investigating</span>
        <span className="inline-block animate-pulse">_</span>
      </div>
      <p className="mt-2 font-mono text-xs text-muted-foreground">
        Querying logs, metrics, traces, and runbooks...
      </p>
      <div className="mt-4 flex items-center gap-2 font-mono text-xs text-muted-foreground">
        <Clock className="size-3 animate-spin" />
        <span>Elapsed: analyzing...</span>
      </div>
    </div>
  )
}

// ---- Main panel ----

interface AIInvestigationPanelProps {
  investigation: AIInvestigation | null
  isLoading?: boolean
  onReinvestigate?: () => void
  className?: string
}

export function AIInvestigationPanel({
  investigation,
  isLoading = false,
  onReinvestigate,
  className,
}: AIInvestigationPanelProps) {
  const [summaryExpanded, setSummaryExpanded] = React.useState(true)
  const [toolsExpanded, setToolsExpanded] = React.useState(false)

  if (isLoading) {
    return (
      <div className={cn("space-y-4", className)}>
        <InvestigationLoading />
      </div>
    )
  }

  if (!investigation) {
    return (
      <div className={cn("flex flex-col items-center justify-center py-12", className)}>
        <Bot className="size-8 text-muted-foreground/50" />
        <p className="mt-3 font-mono text-xs text-muted-foreground">
          No AI investigation has been run for this incident.
        </p>
        <p className="mt-1 font-mono text-xs text-muted-foreground/60">
          Click &quot;Investigate with AI&quot; to start an analysis.
        </p>
      </div>
    )
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header row: confidence + duration + re-investigate */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-4">
          <div>
            <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Confidence
            </span>
            <ConfidenceMeter score={investigation.confidenceScore} />
          </div>
          <div>
            <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Duration
            </span>
            <div className="flex items-center gap-1 font-mono text-xs text-foreground">
              <Zap className="size-3 text-[#FFB020]" />
              {investigation.durationSeconds}s
            </div>
          </div>
        </div>
        <Button
          variant="outline"
          size="xs"
          className="font-mono text-xs"
          onClick={onReinvestigate}
        >
          <RefreshCw className="size-3" />
          Re-investigate
        </Button>
      </div>

      {/* Token usage */}
      <TokenUsageDisplay usage={investigation.tokenUsage} />

      <Separator />

      {/* Summary section (collapsible) */}
      <div>
        <button
          onClick={() => setSummaryExpanded(!summaryExpanded)}
          className="flex w-full items-center gap-2 text-left"
        >
          {summaryExpanded ? (
            <ChevronDown className="size-3 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-3 text-muted-foreground" />
          )}
          <Brain className="size-3 text-[#00B8FF]" />
          <span className="font-mono text-xs font-medium text-foreground">
            AI Summary
          </span>
        </button>
        {summaryExpanded && (
          <div className="mt-2 space-y-3 pl-5">
            <p className="font-mono text-xs leading-relaxed text-muted-foreground">
              {investigation.summary}
            </p>

            {/* Root cause */}
            <div>
              <span className="font-mono text-xs uppercase tracking-wider text-[#FF8C00]">
                Root Cause
              </span>
              <p className="mt-1 rounded-md border border-[#FF8C00]/20 bg-[#FF8C00]/5 px-3 py-2 font-mono text-xs leading-relaxed text-foreground/80">
                {investigation.rootCause}
              </p>
            </div>

            {/* Affected services */}
            {investigation.affectedServices.length > 0 && (
              <div>
                <span className="flex items-center gap-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  <Server className="size-2.5" />
                  Affected Services
                </span>
                <div className="mt-1 flex flex-wrap gap-1">
                  {investigation.affectedServices.map((svc) => (
                    <Badge
                      key={svc}
                      variant="outline"
                      className="font-mono text-xs"
                    >
                      {svc}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <Separator />

      {/* Tools used (collapsible) */}
      <div>
        <button
          onClick={() => setToolsExpanded(!toolsExpanded)}
          className="flex w-full items-center gap-2 text-left"
        >
          {toolsExpanded ? (
            <ChevronDown className="size-3 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-3 text-muted-foreground" />
          )}
          <Zap className="size-3 text-[#FFB020]" />
          <span className="font-mono text-xs font-medium text-foreground">
            MCP Tools Used ({investigation.toolCalls.length})
          </span>
        </button>
        {toolsExpanded && (
          <div className="mt-2 flex flex-wrap gap-1.5 pl-5">
            {investigation.toolCalls.map((tc) => (
              <MCPToolBadge
                key={tc.id}
                toolName={tc.toolName}
                status={tc.status}
                durationMs={tc.durationMs}
                description={tc.description}
              />
            ))}
          </div>
        )}
      </div>

      <Separator />

      {/* Tabs: Remediation / Chat */}
      <Tabs defaultValue="remediation">
        <TabsList variant="line" className="font-mono text-xs">
          <TabsTrigger value="remediation" className="font-mono text-xs">
            Remediation
          </TabsTrigger>
          <TabsTrigger value="chat" className="font-mono text-xs">
            Investigation Log
          </TabsTrigger>
        </TabsList>

        <TabsContent value="remediation" className="mt-3">
          <RemediationSteps steps={investigation.remediationSteps} />
        </TabsContent>

        <TabsContent value="chat" className="mt-3">
          <InvestigationChat
            messages={investigation.messages}
            isRunning={investigation.status === "running"}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
