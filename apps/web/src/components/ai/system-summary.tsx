"use client"

import * as React from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { mockSystemSummary, type SystemSummaryItem } from "@/lib/mock-data/ai-chat"

const levelStyles: Record<SystemSummaryItem["level"], { dot: string; text: string }> = {
  critical: {
    dot: "bg-red-500",
    text: "text-red-400",
  },
  warning: {
    dot: "bg-amber-500",
    text: "text-amber-400",
  },
  healthy: {
    dot: "bg-emerald-500",
    text: "text-emerald-400",
  },
}

export function SystemSummary() {
  const [expanded, setExpanded] = React.useState(true)

  return (
    <div className="border-b border-border">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        {expanded ? (
          <ChevronDown className="size-3.5 shrink-0" />
        ) : (
          <ChevronRight className="size-3.5 shrink-0" />
        )}
        <span>System Status</span>
        {!expanded && (
          <span className="ml-auto flex items-center gap-1.5">
            {mockSystemSummary.map((item) => (
              <span
                key={item.level}
                className={cn(
                  "flex items-center gap-1 text-xs",
                  levelStyles[item.level].text
                )}
              >
                <span
                  className={cn(
                    "inline-block size-1.5 rounded-full",
                    levelStyles[item.level].dot
                  )}
                />
                {item.count}
              </span>
            ))}
          </span>
        )}
      </button>
      {expanded && (
        <div className="space-y-1 px-4 pb-3">
          {mockSystemSummary.map((item) => (
            <div key={item.level} className="flex items-center gap-2.5">
              <span
                className={cn(
                  "inline-block size-2 shrink-0 rounded-full",
                  levelStyles[item.level].dot
                )}
              />
              <span
                className={cn(
                  "text-[13px] leading-snug",
                  levelStyles[item.level].text
                )}
              >
                {item.description}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
