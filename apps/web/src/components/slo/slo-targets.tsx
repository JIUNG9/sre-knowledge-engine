"use client"

import * as React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import {
  Target,
  Clock,
  FileCheck,
  Flame,
  ArrowUp,
  ArrowDown,
} from "lucide-react"

const teamTargets = {
  sloTarget: { target: 99.9, actual: 99.85, unit: "%" },
  mttrTarget: { target: 30, actual: 42, unit: "min" },
  slaCommitment: { target: 99.5, actual: 99.91, unit: "%" },
  errorBudget: { total: 43.2, used: 18.5, unit: "min" },
}

interface TargetCardProps {
  title: string
  icon: React.ComponentType<{ className?: string }>
  targetLabel: string
  targetValue: string
  actualLabel: string
  actualValue: string
  delta: string
  isMeeting: boolean
  progress?: number // 0-100
}

function TargetCard({
  title,
  icon: Icon,
  targetLabel,
  targetValue,
  actualLabel,
  actualValue,
  delta,
  isMeeting,
  progress,
}: TargetCardProps) {
  const DeltaIcon = isMeeting ? ArrowUp : ArrowDown
  const deltaColor = isMeeting ? "#00FF88" : "#FF4444"
  const accentColor = isMeeting ? "#00FF88" : "#FF4444"

  return (
    <Card className="border-t-2" style={{ borderTopColor: accentColor }}>
      <CardContent className="grid gap-3 p-5">
        {/* Title row */}
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-muted-foreground" />
          <span className="font-mono text-sm font-medium text-muted-foreground">
            {title}
          </span>
        </div>

        {/* Values */}
        <div className="flex items-baseline gap-3">
          <span
            className="font-mono text-3xl font-bold tracking-tight"
            style={{ color: accentColor }}
          >
            {actualValue}
          </span>
          <span className="font-mono text-sm text-muted-foreground">
            / {targetValue}
          </span>
        </div>

        {/* Delta */}
        <div className="flex items-center gap-1.5">
          <DeltaIcon className="size-3.5" style={{ color: deltaColor }} />
          <span
            className="font-mono text-sm font-medium"
            style={{ color: deltaColor }}
          >
            {delta}
          </span>
          <span className="font-mono text-xs text-muted-foreground">
            {isMeeting ? "on track" : "behind target"}
          </span>
        </div>

        {/* Progress bar */}
        {progress !== undefined && (
          <div className="mt-1">
            <div className="h-2.5 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(progress, 100)}%`,
                  backgroundColor: accentColor,
                  boxShadow: `0 0 8px ${accentColor}30`,
                }}
              />
            </div>
          </div>
        )}

        {/* Labels */}
        <div className="flex items-center justify-between font-mono text-xs text-muted-foreground/60">
          <span>{targetLabel}</span>
          <span>{actualLabel}</span>
        </div>
      </CardContent>
    </Card>
  )
}

export function SloTargets() {
  const { sloTarget, mttrTarget, slaCommitment, errorBudget } = teamTargets

  const sloMeeting = sloTarget.actual >= sloTarget.target
  const sloDelta = Math.abs(sloTarget.actual - sloTarget.target).toFixed(2)

  const mttrMeeting = mttrTarget.actual <= mttrTarget.target
  const mttrDelta = `${Math.abs(mttrTarget.actual - mttrTarget.target)}${mttrTarget.unit}`

  const slaMeeting = slaCommitment.actual >= slaCommitment.target
  const slaDelta = `+${(slaCommitment.actual - slaCommitment.target).toFixed(2)}${slaCommitment.unit}`

  const budgetUsedPercent = Math.round(
    (errorBudget.used / errorBudget.total) * 100
  )
  const budgetMeeting = budgetUsedPercent < 80
  const budgetRemaining = errorBudget.total - errorBudget.used

  return (
    <div>
      <h2 className="mb-4 font-mono text-sm font-medium uppercase tracking-widest text-muted-foreground/50">
        Team Targets
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <TargetCard
          title="SLO Target vs Actual"
          icon={Target}
          targetLabel={`Target: ${sloTarget.target}%`}
          targetValue={`${sloTarget.target}%`}
          actualLabel={`Actual: ${sloTarget.actual}%`}
          actualValue={`${sloTarget.actual}%`}
          delta={`${sloDelta}%`}
          isMeeting={sloMeeting}
        />
        <TargetCard
          title="MTTR vs Target"
          icon={Clock}
          targetLabel={`Target: ${mttrTarget.target}min`}
          targetValue={`${mttrTarget.target}min`}
          actualLabel={`Actual: ${mttrTarget.actual}min`}
          actualValue={`${mttrTarget.actual}min`}
          delta={mttrDelta}
          isMeeting={mttrMeeting}
        />
        <TargetCard
          title="SLA Commitment"
          icon={FileCheck}
          targetLabel={`SLA: ${slaCommitment.target}%`}
          targetValue={`${slaCommitment.target}%`}
          actualLabel={`Current: ${slaCommitment.actual}%`}
          actualValue={`${slaCommitment.actual}%`}
          delta={slaDelta}
          isMeeting={slaMeeting}
        />
        <TargetCard
          title="Error Budget Status"
          icon={Flame}
          targetLabel={`Budget: ${errorBudget.total}min`}
          targetValue={`${errorBudget.total}min`}
          actualLabel={`Used: ${errorBudget.used}min (${budgetUsedPercent}%)`}
          actualValue={`${budgetRemaining.toFixed(1)}min`}
          delta={`${budgetUsedPercent}% consumed`}
          isMeeting={budgetMeeting}
          progress={budgetUsedPercent}
        />
      </div>
    </div>
  )
}
