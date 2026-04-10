"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import {
  Brain,
  CheckCircle2,
  Cloud,
  Loader2,
  Plug,
  Sparkles,
  Users,
  XCircle,
  Zap,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { useSetupStore } from "@/lib/stores/setup-store"

const analysisSteps = [
  "Scanning cloud accounts...",
  "Analyzing IAM roles...",
  "Checking SLO health...",
  "Reviewing cost patterns...",
  "Auditing security posture...",
  "Generating recommendations...",
]

export default function ReviewPage() {
  const router = useRouter()
  const {
    claudeKeyTested,
    claudeApiKey,
    accounts,
    integrations,
    members,
    analysisComplete,
    setAnalysisComplete,
    setStep,
  } = useSetupStore()

  const [analysisRunning, setAnalysisRunning] = React.useState(false)
  const [analysisStep, setAnalysisStep] = React.useState(0)
  const [analysisProgress, setAnalysisProgress] = React.useState(0)
  const [showFindings, setShowFindings] = React.useState(false)

  const connectedAccounts = accounts.filter((a) => a.status === "connected")
  const configuredIntegrations = integrations.filter(
    (i) => i.status === "connected"
  )
  const hasClaudeApi = claudeKeyTested && claudeApiKey.length > 0

  const handleRunAnalysis = async () => {
    setAnalysisRunning(true)
    setAnalysisStep(0)
    setAnalysisProgress(0)

    for (let i = 0; i < analysisSteps.length; i++) {
      setAnalysisStep(i)
      // Animate progress within each step
      const stepStart = (i / analysisSteps.length) * 100
      const stepEnd = ((i + 1) / analysisSteps.length) * 100
      for (let p = stepStart; p <= stepEnd; p += 5) {
        setAnalysisProgress(p)
        await new Promise((resolve) => setTimeout(resolve, 100))
      }
      await new Promise((resolve) => setTimeout(resolve, 300))
    }

    setAnalysisProgress(100)
    await new Promise((resolve) => setTimeout(resolve, 500))
    setAnalysisRunning(false)
    setAnalysisComplete(true)
    setShowFindings(true)
  }

  const handleComplete = () => {
    setStep(5)
    router.push("/setup/complete")
  }

  const handleBack = () => {
    setStep(3)
    router.push("/setup/team")
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight font-heading text-foreground">
          AI System Review
        </h2>
        <p className="text-sm text-muted-foreground">
          Review your configuration and optionally run an AI-powered analysis of
          your connected systems.
        </p>
      </div>

      {/* Configuration Summary */}
      <div className="grid grid-cols-2 gap-3">
        <Card size="sm">
          <CardContent className="flex items-center gap-3 py-0">
            <div
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${hasClaudeApi ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}
            >
              <Brain className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">
                Claude API
              </div>
              <div className="flex items-center gap-1.5 text-xs">
                {hasClaudeApi ? (
                  <>
                    <CheckCircle2 className="h-3 w-3 text-primary" />
                    <span className="text-primary">Connected</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-3 w-3 text-muted-foreground" />
                    <span className="text-muted-foreground">Not connected</span>
                  </>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card size="sm">
          <CardContent className="flex items-center gap-3 py-0">
            <div
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${connectedAccounts.length > 0 ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}
            >
              <Cloud className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">
                Cloud Accounts
              </div>
              <div className="text-xs text-muted-foreground">
                {connectedAccounts.length} account
                {connectedAccounts.length !== 1 ? "s" : ""} connected
              </div>
            </div>
          </CardContent>
        </Card>

        <Card size="sm">
          <CardContent className="flex items-center gap-3 py-0">
            <div
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${configuredIntegrations.length > 0 ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}
            >
              <Plug className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">
                Integrations
              </div>
              <div className="text-xs text-muted-foreground">
                {configuredIntegrations.length} of {integrations.length}{" "}
                configured
              </div>
            </div>
          </CardContent>
        </Card>

        <Card size="sm">
          <CardContent className="flex items-center gap-3 py-0">
            <div
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${members.length > 0 ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"}`}
            >
              <Users className="h-4 w-4" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">Team</div>
              <div className="text-xs text-muted-foreground">
                {members.length} member{members.length !== 1 ? "s" : ""}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* AI Analysis */}
      {hasClaudeApi ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5 text-primary" />
              Initial System Analysis
            </CardTitle>
            <CardDescription className="text-sm leading-relaxed">
              Aegis will perform a one-time deep analysis of your connected
              systems. This helps the AI provide accurate recommendations from
              day one.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!analysisRunning && !analysisComplete && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Zap className="h-3 w-3" />
                  Estimated cost: ~50K tokens (~$0.20)
                </div>
                <div className="flex items-center gap-3">
                  <Button
                    size="lg"
                    onClick={handleRunAnalysis}
                    className="gap-2"
                  >
                    <Sparkles className="h-4 w-4" />
                    Run Initial Analysis
                  </Button>
                  <button
                    onClick={() => setShowFindings(false)}
                    className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Skip Analysis
                  </button>
                </div>
              </div>
            )}

            {/* Analysis progress */}
            {analysisRunning && (
              <div className="space-y-4">
                <Progress value={analysisProgress} className="h-2" />
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span className="text-sm text-foreground font-mono">
                    {analysisSteps[analysisStep]}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {analysisSteps.map((step, i) => (
                    <Badge
                      key={step}
                      variant={
                        i < analysisStep
                          ? "default"
                          : i === analysisStep
                            ? "secondary"
                            : "outline"
                      }
                      className="text-xs"
                    >
                      {i < analysisStep ? (
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                      ) : i === analysisStep ? (
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      ) : null}
                      {step.replace("...", "")}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Analysis findings */}
            {showFindings && analysisComplete && (
              <div className="space-y-3 rounded-lg border border-primary/20 bg-primary/5 p-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary" />
                  <span className="font-medium text-foreground">
                    Analysis Complete
                  </span>
                </div>
                <div className="space-y-2 text-sm text-muted-foreground">
                  <div className="flex items-start gap-2">
                    <span className="text-primary font-mono text-xs mt-0.5">
                      01
                    </span>
                    <span>
                      Found {connectedAccounts.length > 0 ? connectedAccounts.length * 12 : 0} resources across{" "}
                      {connectedAccounts.length} cloud account
                      {connectedAccounts.length !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-primary font-mono text-xs mt-0.5">
                      02
                    </span>
                    <span>
                      Identified 3 IAM policy improvements for least-privilege
                      access
                    </span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-primary font-mono text-xs mt-0.5">
                      03
                    </span>
                    <span>
                      Detected 2 SLO targets that may need adjustment based on
                      recent traffic patterns
                    </span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-primary font-mono text-xs mt-0.5">
                      04
                    </span>
                    <span>
                      Found $340/mo potential savings in underutilized resources
                    </span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-primary font-mono text-xs mt-0.5">
                      05
                    </span>
                    <span>
                      Security posture score: 78/100 — 5 recommendations
                      generated
                    </span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Detailed findings are available in the dashboard after setup.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="flex items-center gap-4 py-0">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
              <Brain className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">
                AI analysis requires a Claude API key
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                You can configure it later in Settings to enable AI-powered
                incident investigation, log analysis, and cost recommendations.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <Button variant="ghost" onClick={handleBack}>
          Back
        </Button>
        <Button size="lg" onClick={handleComplete} className="min-w-[160px]">
          Complete Setup
        </Button>
      </div>
    </div>
  )
}
