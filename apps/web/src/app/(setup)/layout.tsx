"use client"

import { Shield } from "lucide-react"
import { usePathname } from "next/navigation"
import { WizardStepper } from "@/components/setup/wizard-stepper"

const stepRoutes = [
  "/setup",
  "/setup/cloud",
  "/setup/integrations",
  "/setup/team",
  "/setup/review",
  "/setup/complete",
]

export default function SetupLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const currentStep = stepRoutes.indexOf(pathname)
  const resolvedStep = currentStep === -1 ? 0 : currentStep

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="flex flex-col items-center gap-6 px-6 pt-10 pb-2">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 glow-matrix">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="font-heading text-2xl font-bold tracking-tight text-foreground">
              Aegis
            </h1>
            <p className="text-xs text-muted-foreground font-mono">Setup</p>
          </div>
        </div>

        {/* Step indicator */}
        <div className="w-full max-w-2xl">
          <WizardStepper currentStep={resolvedStep} />
        </div>
      </header>

      {/* Content */}
      <main className="flex flex-1 flex-col items-center px-6 py-8">
        <div className="w-full max-w-2xl">{children}</div>
      </main>
    </div>
  )
}
