"use client"

import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { SERVICES } from "@/lib/mock-data/services"
import type { SliType, SloWindow } from "@/lib/mock-data/slo"
import { Plus } from "lucide-react"

const SLI_TYPES: { value: SliType; label: string }[] = [
  { value: "availability", label: "Availability" },
  { value: "latency", label: "Latency" },
  { value: "error_rate", label: "Error Rate" },
  { value: "throughput", label: "Throughput" },
]

const WINDOWS: { value: SloWindow; label: string }[] = [
  { value: "7d", label: "7 days" },
  { value: "30d", label: "30 days" },
  { value: "90d", label: "90 days" },
  { value: "365d", label: "365 days" },
]

export function SloForm() {
  const [name, setName] = React.useState("")
  const [service, setService] = React.useState<string>("")
  const [target, setTarget] = React.useState("")
  const [window, setWindow] = React.useState<SloWindow>("30d")
  const [sliType, setSliType] = React.useState<SliType>("availability")
  const [description, setDescription] = React.useState("")
  const [open, setOpen] = React.useState(false)

  const handleSave = () => {
    // In a real app, this would call an API
    setOpen(false)
    // Reset form
    setName("")
    setService("")
    setTarget("")
    setWindow("30d")
    setSliType("availability")
    setDescription("")
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button size="sm" className="gap-1.5 font-mono text-[11px]">
            <Plus className="size-3.5" />
            Create SLO
          </Button>
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create SLO</DialogTitle>
          <DialogDescription>
            Define a new Service Level Objective for monitoring.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          {/* Service */}
          <div className="grid gap-1.5">
            <label className="font-mono text-xs text-muted-foreground">
              Service
            </label>
            <Select value={service} onValueChange={(v) => setService(v ?? "")}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a service" />
              </SelectTrigger>
              <SelectContent>
                {SERVICES.map((svc) => (
                  <SelectItem key={svc.id} value={svc.name}>
                    {svc.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* SLO Name */}
          <div className="grid gap-1.5">
            <label className="font-mono text-xs text-muted-foreground">
              SLO Name
            </label>
            <Input
              placeholder="e.g., API Gateway Availability"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="font-mono text-sm"
            />
          </div>

          {/* Target */}
          <div className="grid gap-1.5">
            <label className="font-mono text-xs text-muted-foreground">
              Target (%)
            </label>
            <Input
              type="number"
              step="0.01"
              placeholder="e.g., 99.9"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              className="font-mono text-sm"
            />
          </div>

          {/* Window + SLI Type */}
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <label className="font-mono text-xs text-muted-foreground">
                Window
              </label>
              <Select
                value={window}
                onValueChange={(v) => { if (v) setWindow(v as SloWindow) }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {WINDOWS.map((w) => (
                    <SelectItem key={w.value} value={w.value}>
                      {w.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <label className="font-mono text-xs text-muted-foreground">
                SLI Type
              </label>
              <Select
                value={sliType}
                onValueChange={(v) => { if (v) setSliType(v as SliType) }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SLI_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Description */}
          <div className="grid gap-1.5">
            <label className="font-mono text-xs text-muted-foreground">
              Description
            </label>
            <Textarea
              placeholder="What does this SLO measure?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="font-mono text-sm"
            />
          </div>
        </div>

        <DialogFooter>
          <DialogClose
            render={<Button variant="outline" size="sm" className="font-mono text-xs" />}
          >
            Cancel
          </DialogClose>
          <Button
            size="sm"
            className="font-mono text-xs"
            onClick={handleSave}
            disabled={!name || !service || !target}
          >
            Save SLO
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
