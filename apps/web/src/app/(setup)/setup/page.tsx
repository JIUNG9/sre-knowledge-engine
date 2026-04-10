"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import {
  Eye,
  EyeOff,
  CheckCircle2,
  Loader2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  AlertTriangle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { useSetupStore } from "@/lib/stores/setup-store"

export default function SetupWelcomePage() {
  const router = useRouter()
  const {
    claudeApiKey,
    claudeKeyTested,
    setClaudeApiKey,
    setClaudeKeyTested,
    setStep,
  } = useSetupStore()

  const [showKey, setShowKey] = React.useState(false)
  const [testing, setTesting] = React.useState(false)
  const [whyOpen, setWhyOpen] = React.useState(false)
  const [showSkipWarning, setShowSkipWarning] = React.useState(false)

  const handleTestConnection = async () => {
    setTesting(true)
    // Simulated test - shows green checkmark after 1s
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setClaudeKeyTested(true)
    setTesting(false)
  }

  const handleContinue = () => {
    setStep(1)
    router.push("/setup/cloud")
  }

  const handleSkip = () => {
    if (!showSkipWarning) {
      setShowSkipWarning(true)
      return
    }
    setStep(1)
    router.push("/setup/cloud")
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Welcome header */}
      <div className="text-center space-y-3">
        <h2 className="text-3xl font-bold tracking-tight font-heading text-foreground">
          Welcome to Aegis
        </h2>
        <p className="text-base text-muted-foreground max-w-lg mx-auto">
          Let&apos;s set up your DevSecOps command center. This wizard will guide
          you through connecting your AI engine, cloud accounts, tools, and team.
        </p>
      </div>

      {/* Claude API Key Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Sparkles className="h-5 w-5 text-primary" />
            Claude AI Engine
          </CardTitle>
          <CardDescription className="text-sm leading-relaxed">
            Aegis uses Claude AI to power incident investigation, log analysis,
            cost optimization, and more. Your API key is stored encrypted and
            used only for your operations.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* API Key input */}
          <div className="space-y-2">
            <Label htmlFor="claude-api-key" className="text-sm">
              Claude API Key
            </Label>
            <div className="relative">
              <Input
                id="claude-api-key"
                type={showKey ? "text" : "password"}
                placeholder="sk-ant-api03-..."
                value={claudeApiKey}
                onChange={(e) => setClaudeApiKey(e.target.value)}
                className="h-11 pr-20 font-mono text-sm"
              />
              <div className="absolute right-1 top-1/2 -translate-y-1/2 flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => setShowKey(!showKey)}
                  aria-label={showKey ? "Hide API key" : "Show API key"}
                >
                  {showKey ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Get your API key from{" "}
              <a
                href="https://console.anthropic.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                console.anthropic.com
              </a>
            </p>
          </div>

          {/* Test connection */}
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="default"
              onClick={handleTestConnection}
              disabled={!claudeApiKey || testing || claudeKeyTested}
            >
              {testing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Testing...
                </>
              ) : claudeKeyTested ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                  Connected
                </>
              ) : (
                "Test Connection"
              )}
            </Button>
            {claudeKeyTested && (
              <span className="text-sm text-primary font-medium">
                API key verified successfully
              </span>
            )}
          </div>

          {/* Why Claude AI first? collapsible */}
          <div className="rounded-lg border border-border bg-muted/30">
            <button
              onClick={() => setWhyOpen(!whyOpen)}
              className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              <span>Why Claude AI first?</span>
              {whyOpen ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>
            {whyOpen && (
              <div className="px-4 pb-4 text-sm text-muted-foreground leading-relaxed space-y-2">
                <p>
                  Claude AI assists throughout the entire setup process. Once
                  connected, it can:
                </p>
                <ul className="list-disc list-inside space-y-1 ml-1">
                  <li>Auto-detect cloud account configurations</li>
                  <li>Recommend which integrations to enable</li>
                  <li>Suggest team roles based on your organization</li>
                  <li>
                    Run a deep analysis of your infrastructure on first launch
                  </li>
                </ul>
                <p>
                  Setting it up first ensures the best experience for the
                  remaining steps.
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Skip warning */}
      {showSkipWarning && !claudeKeyTested && (
        <div className="flex items-start gap-3 rounded-lg border border-status-warning/30 bg-status-warning/5 p-4">
          <AlertTriangle className="h-5 w-5 text-[oklch(var(--status-warning))] shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">
              AI features will be limited
            </p>
            <p className="text-sm text-muted-foreground">
              Without a Claude API key, incident investigation, log analysis,
              cost recommendations, and the initial system analysis will be
              unavailable. You can configure it later in Settings.
            </p>
            <Button
              variant="ghost"
              size="sm"
              className="mt-2 text-muted-foreground hover:text-foreground"
              onClick={() => {
                setStep(1)
                router.push("/setup/cloud")
              }}
            >
              Continue without AI
            </Button>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={handleSkip}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Skip for now
        </button>
        <Button
          size="lg"
          onClick={handleContinue}
          disabled={!claudeKeyTested && claudeApiKey.length === 0}
          className="min-w-[140px]"
        >
          Continue
        </Button>
      </div>
    </div>
  )
}
