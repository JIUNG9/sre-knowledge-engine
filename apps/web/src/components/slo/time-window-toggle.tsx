"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import type { SloWindow } from "@/lib/mock-data/slo"

const WINDOWS: { value: SloWindow; label: string }[] = [
  { value: "7d", label: "Weekly" },
  { value: "30d", label: "Monthly" },
  { value: "90d", label: "Quarterly" },
  { value: "365d", label: "Annually" },
]

interface TimeWindowToggleProps {
  value: SloWindow | "all"
  onChange: (window: SloWindow | "all") => void
}

export function TimeWindowToggle({ value, onChange }: TimeWindowToggleProps) {
  return (
    <div className="flex items-center gap-0.5 rounded-lg bg-muted p-0.5">
      <Button
        variant={value === "all" ? "secondary" : "ghost"}
        size="xs"
        className={cn(
          "font-mono text-xs",
          value === "all" && "bg-primary/15 text-primary"
        )}
        onClick={() => onChange("all")}
      >
        All
      </Button>
      {WINDOWS.map((w) => (
        <Button
          key={w.value}
          variant={value === w.value ? "secondary" : "ghost"}
          size="xs"
          className={cn(
            "font-mono text-xs",
            value === w.value && "bg-primary/15 text-primary"
          )}
          onClick={() => onChange(w.value)}
        >
          {w.label}
        </Button>
      ))}
    </div>
  )
}
