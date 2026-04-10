"use client"

import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

const steps = [
  { label: "AI Engine" },
  { label: "Cloud Accounts" },
  { label: "Integrations" },
  { label: "Team" },
  { label: "Review" },
  { label: "Complete" },
] as const

interface WizardStepperProps {
  currentStep: number
}

export function WizardStepper({ currentStep }: WizardStepperProps) {
  return (
    <nav aria-label="Setup progress" className="w-full">
      <ol className="flex items-center justify-between gap-2">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep
          const isCurrent = index === currentStep
          const isFuture = index > currentStep

          return (
            <li key={step.label} className="flex flex-1 items-center gap-2">
              <div className="flex flex-col items-center gap-1.5 flex-1">
                {/* Step circle + connector line */}
                <div className="flex items-center w-full">
                  {/* Connector line (left) */}
                  {index > 0 && (
                    <div
                      className={cn(
                        "h-px flex-1 transition-colors",
                        isCompleted || isCurrent
                          ? "bg-primary"
                          : "bg-border"
                      )}
                    />
                  )}

                  {/* Circle */}
                  <div
                    className={cn(
                      "relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-mono font-semibold transition-all",
                      isCompleted &&
                        "border-primary bg-primary text-primary-foreground",
                      isCurrent &&
                        "border-primary bg-primary/10 text-primary glow-matrix",
                      isFuture &&
                        "border-muted-foreground/30 bg-transparent text-muted-foreground/50"
                    )}
                  >
                    {isCompleted ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <span>{index + 1}</span>
                    )}
                  </div>

                  {/* Connector line (right) */}
                  {index < steps.length - 1 && (
                    <div
                      className={cn(
                        "h-px flex-1 transition-colors",
                        isCompleted ? "bg-primary" : "bg-border"
                      )}
                    />
                  )}
                </div>

                {/* Label */}
                <span
                  className={cn(
                    "text-xs font-medium text-center whitespace-nowrap transition-colors",
                    isCompleted && "text-primary",
                    isCurrent && "text-primary",
                    isFuture && "text-muted-foreground/50"
                  )}
                >
                  {step.label}
                </span>
              </div>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
