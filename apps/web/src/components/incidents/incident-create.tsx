"use client"

import * as React from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { ASSIGNEES, INCIDENT_SERVICES } from "@/lib/mock-data/incidents"
import type { IncidentSeverity } from "@/lib/mock-data/incidents"
import { Plus } from "lucide-react"

const SEVERITY_OPTIONS: { value: IncidentSeverity; label: string; color: string }[] = [
  { value: "critical", label: "Critical", color: "#FF4444" },
  { value: "high", label: "High", color: "#FF8C00" },
  { value: "medium", label: "Medium", color: "#FFB020" },
  { value: "low", label: "Low", color: "#00B8FF" },
]

export function IncidentCreate() {
  const [open, setOpen] = React.useState(false)
  const [title, setTitle] = React.useState("")
  const [description, setDescription] = React.useState("")
  const [severity, setSeverity] = React.useState<IncidentSeverity>("medium")
  const [service, setService] = React.useState<string>("")
  const [assignee, setAssignee] = React.useState<string>("")

  function handleReset() {
    setTitle("")
    setDescription("")
    setSeverity("medium")
    setService("")
    setAssignee("")
  }

  function handleCreate() {
    // In a real app, this would call an API
    handleReset()
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button size="sm" className="font-mono text-xs">
            <Plus className="size-3" />
            New Incident
          </Button>
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create Incident</DialogTitle>
          <DialogDescription>
            Manually create an incident and begin the response workflow.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3">
          {/* Title */}
          <div>
            <label className="mb-1 block font-mono text-xs text-muted-foreground">
              Title
            </label>
            <Input
              placeholder="Brief description of the issue..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="font-mono text-xs"
            />
          </div>

          {/* Description */}
          <div>
            <label className="mb-1 block font-mono text-xs text-muted-foreground">
              Description
            </label>
            <Textarea
              placeholder="Detailed description, impact, and any known context..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="min-h-20 font-mono text-xs"
            />
          </div>

          {/* Severity */}
          <div>
            <label className="mb-1 block font-mono text-xs text-muted-foreground">
              Severity
            </label>
            <div className="flex gap-1.5">
              {SEVERITY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setSeverity(opt.value)}
                  className={cn(
                    "flex-1 rounded-md border px-2 py-1.5 font-mono text-xs font-medium transition-all",
                    severity === opt.value
                      ? "ring-1"
                      : "border-border text-muted-foreground hover:text-foreground"
                  )}
                  style={
                    severity === opt.value
                      ? {
                          borderColor: `${opt.color}50`,
                          backgroundColor: `${opt.color}10`,
                          color: opt.color,
                          boxShadow: `0 0 8px ${opt.color}20`,
                        }
                      : undefined
                  }
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Service */}
          <div>
            <label className="mb-1 block font-mono text-xs text-muted-foreground">
              Service
            </label>
            <Select value={service} onValueChange={(v) => { if (v) setService(v) }}>
              <SelectTrigger size="sm" className="w-full font-mono text-xs">
                <SelectValue placeholder="Select service..." />
              </SelectTrigger>
              <SelectContent>
                {INCIDENT_SERVICES.map((svc) => (
                  <SelectItem key={svc} value={svc}>
                    {svc}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Assignee */}
          <div>
            <label className="mb-1 block font-mono text-xs text-muted-foreground">
              Assignee
            </label>
            <Select value={assignee} onValueChange={(v) => { if (v) setAssignee(v) }}>
              <SelectTrigger size="sm" className="w-full font-mono text-xs">
                <SelectValue placeholder="Assign to..." />
              </SelectTrigger>
              <SelectContent>
                {ASSIGNEES.map((name) => (
                  <SelectItem key={name} value={name}>
                    {name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Status note */}
          <p className="font-mono text-xs text-muted-foreground/60">
            Initial status will be set to <strong className="text-[#FF4444]">Open</strong>.
          </p>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            className="font-mono text-xs"
            onClick={() => setOpen(false)}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            className="font-mono text-xs"
            disabled={!title.trim() || !service}
            onClick={handleCreate}
          >
            Create Incident
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
