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
    <div className="flex items-center gap-1 rounded-lg bg-muted p-1">
      <Button
        variant={value === "all" ? "secondary" : "ghost"}
        className={cn(
          "px-5 py-2.5 font-mono text-sm",
          value === "all" && "bg-primary/15 text-primary shadow-sm"
        )}
        onClick={() => onChange("all")}
      >
        All
      </Button>
      {WINDOWS.map((w) => (
        <Button
          key={w.value}
          variant={value === w.value ? "secondary" : "ghost"}
          className={cn(
            "px-5 py-2.5 font-mono text-sm",
            value === w.value && "bg-primary/15 text-primary shadow-sm"
          )}
          onClick={() => onChange(w.value)}
        >
          {w.label}
        </Button>
      ))}
    </div>
  )
}
