"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import {
  CheckCircle2,
  Cloud,
  ExternalLink,
  Plug,
  Settings,
  Users,
  LayoutDashboard,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { useSetupStore } from "@/lib/stores/setup-store"

export default function CompletePage() {
  const router = useRouter()
  const { accounts, integrations, members, completeSetup } = useSetupStore()

  const connectedAccounts = accounts.filter((a) => a.status === "connected")
  const configuredIntegrations = integrations.filter(
    (i) => i.status === "connected"
  )

  // Mark setup as complete
  React.useEffect(() => {
    completeSetup()
  }, [completeSetup])

  return (
    <div className="flex flex-col items-center gap-8 py-8">
      {/* Success animation */}
      <div className="relative flex h-24 w-24 items-center justify-center">
        {/* Outer glow ring */}
        <div className="absolute inset-0 rounded-full bg-primary/20 animate-ping" />
        {/* Middle glow ring */}
        <div className="absolute inset-2 rounded-full bg-primary/10" />
        {/* Inner circle */}
        <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-primary/20 glow-matrix-strong">
          <CheckCircle2 className="h-10 w-10 text-primary" />
        </div>
      </div>

      {/* Title */}
      <div className="text-center space-y-2">
        <h2 className="text-3xl font-bold tracking-tight font-heading text-foreground text-glow">
          Aegis is Ready!
        </h2>
        <p className="text-base text-muted-foreground max-w-md">
          Your DevSecOps command center is configured and ready to protect your
          infrastructure.
        </p>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-3 gap-4 w-full max-w-md">
        <Card size="sm">
          <CardContent className="flex flex-col items-center gap-1 py-0 text-center">
            <Cloud className="h-5 w-5 text-primary" />
            <span className="text-2xl font-bold font-mono text-foreground">
              {connectedAccounts.length}
            </span>
            <span className="text-xs text-muted-foreground">
              Account{connectedAccounts.length !== 1 ? "s" : ""}
            </span>
          </CardContent>
        </Card>

        <Card size="sm">
          <CardContent className="flex flex-col items-center gap-1 py-0 text-center">
            <Plug className="h-5 w-5 text-primary" />
            <span className="text-2xl font-bold font-mono text-foreground">
              {configuredIntegrations.length}
            </span>
            <span className="text-xs text-muted-foreground">
              Integration{configuredIntegrations.length !== 1 ? "s" : ""}
            </span>
          </CardContent>
        </Card>

        <Card size="sm">
          <CardContent className="flex flex-col items-center gap-1 py-0 text-center">
            <Users className="h-5 w-5 text-primary" />
            <span className="text-2xl font-bold font-mono text-foreground">
              {members.length}
            </span>
            <span className="text-xs text-muted-foreground">
              Member{members.length !== 1 ? "s" : ""}
            </span>
          </CardContent>
        </Card>
      </div>

      {/* CTA Buttons */}
      <div className="flex flex-col gap-3 w-full max-w-sm pt-4">
        <Button
          size="lg"
          className="w-full h-12 text-base gap-2 glow-matrix"
          onClick={() => router.push("/logs")}
        >
          <LayoutDashboard className="h-5 w-5" />
          Open Dashboard
        </Button>

        <Button
          variant="outline"
          size="lg"
          className="w-full h-11 gap-2"
          onClick={() => router.push("/settings")}
        >
          <Settings className="h-4 w-4" />
          Configure More Settings
        </Button>

        <Button
          variant="ghost"
          size="lg"
          className="w-full h-11 gap-2 text-muted-foreground"
          onClick={() => window.open("/docs", "_blank")}
        >
          <ExternalLink className="h-4 w-4" />
          Read Documentation
        </Button>
      </div>
    </div>
  )
}
