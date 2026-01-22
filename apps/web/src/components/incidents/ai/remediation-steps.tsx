"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import type { RemediationStep, RiskLevel, StepApproval } from "@/lib/mock-data/ai-investigation"
import {
  Check,
  X,
  CheckCheck,
  XCircle,
  ShieldAlert,
  ShieldCheck,
  Shield,
  ChevronDown,
  ChevronRight,
} from "lucide-react"

// ---- Risk level config ----

function getRiskConfig(level: RiskLevel) {
  switch (level) {
    case "low":
      return {
        label: "LOW RISK",
        color: "#00FF88",
        bg: "bg-[#00FF88]/10",
        border: "border-[#00FF88]/30",
        icon: ShieldCheck,
      }
    case "medium":
      return {
        label: "MEDIUM RISK",
        color: "#FFB020",
        bg: "bg-[#FFB020]/10",
        border: "border-[#FFB020]/30",
        icon: Shield,
      }
    case "high":
      return {
        label: "HIGH RISK",
        color: "#FF4444",
        bg: "bg-[#FF4444]/10",
        border: "border-[#FF4444]/30",
        icon: ShieldAlert,
      }
  }
}

function getApprovalConfig(approval: StepApproval) {
  switch (approval) {
    case "approved":
      return {
        color: "#00FF88",
        bg: "bg-[#00FF88]/10",
        label: "Approved",
        icon: Check,
      }
    case "rejected":
      return {
        color: "#FF4444",
        bg: "bg-[#FF4444]/10",
        label: "Rejected",
        icon: X,
      }
    case "pending":
      return {
        color: "#888",
        bg: "bg-muted",
        label: "Pending",
        icon: null,
      }
  }
}

// ---- Step item ----

interface StepItemProps {
  step: RemediationStep
  onApprove: (id: string) => void
  onReject: (id: string) => void
}

function StepItem({ step, onApprove, onReject }: StepItemProps) {
  const [expanded, setExpanded] = React.useState(false)
  const riskConfig = getRiskConfig(step.riskLevel)
  const approvalConfig = getApprovalConfig(step.approval)
  const RiskIcon = riskConfig.icon

  return (
    <div
      className={cn(
        "rounded-md border border-border/50 bg-muted/30 transition-colors",
        step.approval === "approved" && "border-[#00FF88]/20 bg-[#00FF88]/5",
        step.approval === "rejected" && "border-[#FF4444]/20 bg-[#FF4444]/5 opacity-60"
      )}
    >
      {/* Header */}
      <div className="flex items-start gap-2 p-3">
        {/* Step number */}
        <span
          className={cn(
            "flex size-5 shrink-0 items-center justify-center rounded-full font-mono text-[10px] font-bold",
            step.approval === "approved"
              ? "bg-[#00FF88]/20 text-[#00FF88]"
              : step.approval === "rejected"
                ? "bg-[#FF4444]/20 text-[#FF4444]"
                : "bg-muted text-muted-foreground"
          )}
        >
          {step.approval === "approved" ? (
            <Check className="size-3" />
          ) : step.approval === "rejected" ? (
            <X className="size-3" />
          ) : (
            step.order
          )}
        </span>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="flex-1 font-mono text-xs font-medium text-foreground">
              {step.description}
            </p>
            {/* Risk badge */}
            <span
              className={cn(
                "inline-flex shrink-0 items-center gap-1 rounded-sm border px-1.5 py-0.5 font-mono text-[9px] font-bold",
                riskConfig.bg,
                riskConfig.border
              )}
              style={{ color: riskConfig.color }}
            >
              <RiskIcon className="size-2.5" />
              {riskConfig.label}
            </span>
          </div>

          <p className="mt-1 font-mono text-[10px] text-muted-foreground">
            {step.estimatedImpact}
          </p>

          {/* Command preview toggle */}
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-2 flex items-center gap-1 font-mono text-[10px] text-muted-foreground transition-colors hover:text-foreground"
          >
            {expanded ? (
              <ChevronDown className="size-3" />
            ) : (
              <ChevronRight className="size-3" />
            )}
            Command preview
          </button>

          {/* Collapsible command block */}
          {expanded && (
            <div className="mt-2 overflow-x-auto rounded-md bg-[#0A0A0A] p-3">
              <pre className="font-mono text-[11px] leading-relaxed text-[#00FF88]/90">
                <code>{step.command}</code>
              </pre>
            </div>
          )}

          {/* Approval buttons */}
          {step.approval === "pending" && (
            <div className="mt-2 flex gap-2">
              <Button
                variant="outline"
                size="xs"
                className="font-mono text-[10px] text-[#00FF88] hover:bg-[#00FF88]/10 hover:text-[#00FF88]"
                onClick={() => onApprove(step.id)}
              >
                <Check className="size-3" />
                Approve
              </Button>
              <Button
                variant="outline"
                size="xs"
                className="font-mono text-[10px] text-[#FF4444] hover:bg-[#FF4444]/10 hover:text-[#FF4444]"
                onClick={() => onReject(step.id)}
              >
                <X className="size-3" />
                Reject
              </Button>
            </div>
          )}

          {/* Approval status */}
          {step.approval !== "pending" && (
            <div
              className="mt-2 flex items-center gap-1 font-mono text-[10px]"
              style={{ color: approvalConfig.color }}
            >
              {approvalConfig.icon && <approvalConfig.icon className="size-3" />}
              {approvalConfig.label}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ---- Main component ----

interface RemediationStepsProps {
  steps: RemediationStep[]
  className?: string
}

export function RemediationSteps({ steps: initialSteps, className }: RemediationStepsProps) {
  const [steps, setSteps] = React.useState(initialSteps)

  const pendingCount = steps.filter((s) => s.approval === "pending").length
  const approvedCount = steps.filter((s) => s.approval === "approved").length
  const rejectedCount = steps.filter((s) => s.approval === "rejected").length

  function handleApprove(id: string) {
    setSteps((prev) =>
      prev.map((s) => (s.id === id ? { ...s, approval: "approved" as StepApproval } : s))
    )
  }

  function handleReject(id: string) {
    setSteps((prev) =>
      prev.map((s) => (s.id === id ? { ...s, approval: "rejected" as StepApproval } : s))
    )
  }

  function handleApproveAll() {
    setSteps((prev) =>
      prev.map((s) => (s.approval === "pending" ? { ...s, approval: "approved" as StepApproval } : s))
    )
  }

  function handleRejectAll() {
    setSteps((prev) =>
      prev.map((s) => (s.approval === "pending" ? { ...s, approval: "rejected" as StepApproval } : s))
    )
  }

  return (
    <div className={cn("space-y-3", className)}>
      {/* Header with bulk actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h4 className="font-mono text-xs font-medium text-foreground">
            Remediation Steps ({steps.length})
          </h4>
          <div className="flex items-center gap-2 font-mono text-[10px] text-muted-foreground">
            {approvedCount > 0 && (
              <span className="text-[#00FF88]">{approvedCount} approved</span>
            )}
            {rejectedCount > 0 && (
              <span className="text-[#FF4444]">{rejectedCount} rejected</span>
            )}
            {pendingCount > 0 && <span>{pendingCount} pending</span>}
          </div>
        </div>

        {pendingCount > 0 && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="xs"
              className="font-mono text-[10px] text-[#00FF88] hover:bg-[#00FF88]/10 hover:text-[#00FF88]"
              onClick={handleApproveAll}
            >
              <CheckCheck className="size-3" />
              Approve All
            </Button>
            <Button
              variant="outline"
              size="xs"
              className="font-mono text-[10px] text-[#FF4444] hover:bg-[#FF4444]/10 hover:text-[#FF4444]"
              onClick={handleRejectAll}
            >
              <XCircle className="size-3" />
              Reject All
            </Button>
          </div>
        )}
      </div>

      {/* Steps list */}
      <div className="space-y-2">
        {steps.map((step) => (
          <StepItem
            key={step.id}
            step={step}
            onApprove={handleApprove}
            onReject={handleReject}
          />
        ))}
      </div>
    </div>
  )
}
