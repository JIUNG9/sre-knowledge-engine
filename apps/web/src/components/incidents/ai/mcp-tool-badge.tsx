"use client"

import { cn } from "@/lib/utils"
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "@/components/ui/tooltip"
import type { ToolStatus } from "@/lib/mock-data/ai-investigation"
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Search,
  Activity,
  GitBranch,
  Database,
  FileText,
  Terminal,
  Globe,
  HardDrive,
} from "lucide-react"

// ---- Tool icon mapping ----

const TOOL_ICONS: Record<string, typeof Search> = {
  query_logs: Search,
  query_metrics: Activity,
  query_traces: GitBranch,
  query_database: Database,
  query_runbooks: FileText,
  query_kubernetes: Terminal,
  query_git: GitBranch,
  check_external_status: Globe,
  analyze_heap_dump: HardDrive,
}

function getStatusConfig(status: ToolStatus) {
  switch (status) {
    case "succeeded":
      return {
        color: "#00FF88",
        bg: "bg-[#00FF88]/10",
        border: "border-[#00FF88]/30",
        icon: CheckCircle2,
        label: "Succeeded",
      }
    case "failed":
      return {
        color: "#FF4444",
        bg: "bg-[#FF4444]/10",
        border: "border-[#FF4444]/30",
        icon: XCircle,
        label: "Failed",
      }
    case "pending":
      return {
        color: "#FFB020",
        bg: "bg-[#FFB020]/10",
        border: "border-[#FFB020]/30",
        icon: Loader2,
        label: "Pending Approval",
      }
  }
}

// ---- Component ----

interface MCPToolBadgeProps {
  toolName: string
  status: ToolStatus
  durationMs: number
  description?: string
  className?: string
}

export function MCPToolBadge({
  toolName,
  status,
  durationMs,
  description,
  className,
}: MCPToolBadgeProps) {
  const config = getStatusConfig(status)
  const ToolIcon = TOOL_ICONS[toolName] ?? Terminal
  const StatusIcon = config.icon

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger
          className={cn(
            "inline-flex items-center gap-1.5 rounded-sm border px-1.5 py-0.5 font-mono text-[10px] transition-colors",
            config.bg,
            config.border,
            className
          )}
          style={{ color: config.color }}
        >
          <ToolIcon className="size-3" />
          <span>{toolName}</span>
          <StatusIcon
            className={cn(
              "size-2.5",
              status === "pending" && "animate-spin"
            )}
          />
        </TooltipTrigger>
        <TooltipContent side="bottom">
          <div className="space-y-1">
            <div className="font-medium">{toolName}</div>
            {description && (
              <div className="text-xs opacity-80">{description}</div>
            )}
            <div className="flex items-center gap-2 text-xs opacity-80">
              <span>{config.label}</span>
              <span>|</span>
              <span>{durationMs}ms</span>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
