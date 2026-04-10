"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import {
  Activity,
  BarChart3,
  Bell,
  Bug,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  GitBranch,
  Loader2,
  Rocket,
  Shield,
  Ticket,
  X,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { useSetupStore } from "@/lib/stores/setup-store"

interface IntegrationDef {
  id: string
  name: string
  category: string
  description: string
  icon: React.ElementType
  fields: { key: string; label: string; placeholder: string; type?: string }[]
}

const integrationDefs: IntegrationDef[] = [
  {
    id: "signoz",
    name: "SigNoz",
    category: "Monitoring",
    description: "Open-source APM and observability platform",
    icon: Activity,
    fields: [
      { key: "url", label: "SigNoz URL", placeholder: "https://signoz.example.com" },
      { key: "apiKey", label: "API Key", placeholder: "Your SigNoz API key", type: "password" },
    ],
  },
  {
    id: "datadog",
    name: "Datadog",
    category: "Monitoring",
    description: "Cloud monitoring and analytics platform",
    icon: BarChart3,
    fields: [
      { key: "apiKey", label: "API Key", placeholder: "Your Datadog API key", type: "password" },
      { key: "appKey", label: "App Key", placeholder: "Your Datadog App key", type: "password" },
    ],
  },
  {
    id: "prometheus",
    name: "Prometheus",
    category: "Monitoring",
    description: "Open-source metrics and alerting toolkit",
    icon: Activity,
    fields: [
      { key: "url", label: "Prometheus URL", placeholder: "https://prometheus.example.com" },
    ],
  },
  {
    id: "slack",
    name: "Slack",
    category: "Notification",
    description: "Team messaging and incident notifications",
    icon: Bell,
    fields: [
      { key: "botToken", label: "Bot Token", placeholder: "xoxb-...", type: "password" },
      { key: "signingSecret", label: "Signing Secret", placeholder: "Signing secret", type: "password" },
    ],
  },
  {
    id: "jira",
    name: "JIRA",
    category: "Ticketing",
    description: "Issue tracking and project management",
    icon: Ticket,
    fields: [
      { key: "baseUrl", label: "Base URL", placeholder: "https://yourorg.atlassian.net" },
      { key: "apiToken", label: "API Token", placeholder: "Your JIRA API token", type: "password" },
    ],
  },
  {
    id: "github",
    name: "GitHub",
    category: "Ticketing",
    description: "Code hosting and issue tracking",
    icon: GitBranch,
    fields: [
      { key: "token", label: "Personal Access Token", placeholder: "ghp_...", type: "password" },
    ],
  },
  {
    id: "argocd",
    name: "ArgoCD",
    category: "Deployment",
    description: "GitOps continuous delivery for Kubernetes",
    icon: Rocket,
    fields: [
      { key: "serverUrl", label: "Server URL", placeholder: "https://argocd.example.com" },
      { key: "authToken", label: "Auth Token", placeholder: "ArgoCD auth token", type: "password" },
    ],
  },
  {
    id: "trivy",
    name: "Trivy",
    category: "Security",
    description: "Container and IaC vulnerability scanner",
    icon: Shield,
    fields: [
      { key: "url", label: "Trivy Server URL (optional)", placeholder: "https://trivy.example.com" },
    ],
  },
]

const categoryIcons: Record<string, React.ElementType> = {
  Monitoring: Activity,
  Notification: Bell,
  Ticketing: Ticket,
  Deployment: Rocket,
  Security: Shield,
}

const categoryColors: Record<string, string> = {
  Monitoring: "text-[oklch(0.75_0.15_230)]",
  Notification: "text-[oklch(0.78_0.15_75)]",
  Ticketing: "text-[oklch(0.65_0.2_280)]",
  Deployment: "text-primary",
  Security: "text-[oklch(0.7_0.2_25)]",
}

export default function IntegrationsPage() {
  const router = useRouter()
  const { integrations, updateIntegration, setStep } = useSetupStore()

  const [expandedId, setExpandedId] = React.useState<string | null>(null)
  const [formValues, setFormValues] = React.useState<Record<string, string>>({})
  const [testingId, setTestingId] = React.useState<string | null>(null)

  const handleExpand = (id: string) => {
    if (expandedId === id) {
      setExpandedId(null)
      setFormValues({})
      return
    }
    setExpandedId(id)
    // Pre-populate with existing config
    const integration = integrations.find((i) => i.id === id)
    if (integration) {
      setFormValues(integration.config)
    }
  }

  const handleFieldChange = (key: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [key]: value }))
  }

  const handleTestConnection = async (id: string) => {
    setTestingId(id)
    await new Promise((resolve) => setTimeout(resolve, 1000))
    updateIntegration(id, formValues, "connected")
    setTestingId(null)
    setExpandedId(null)
    setFormValues({})
  }

  const handleContinue = () => {
    setStep(3)
    router.push("/setup/team")
  }

  const handleBack = () => {
    setStep(1)
    router.push("/setup/cloud")
  }

  const connectedCount = integrations.filter(
    (i) => i.status === "connected"
  ).length

  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight font-heading text-foreground">
          Connect Your Tools
        </h2>
        <p className="text-sm text-muted-foreground">
          Integrate your monitoring, deployment, notification, and security
          tools. All integrations are optional and can be configured later.
          <span className="ml-2 text-primary font-medium">
            {connectedCount} of {integrations.length} configured
          </span>
        </p>
      </div>

      {/* Integration Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {integrationDefs.map((def) => {
          const integration = integrations.find((i) => i.id === def.id)
          const isExpanded = expandedId === def.id
          const status = integration?.status || "not-configured"
          const Icon = def.icon

          return (
            <Card key={def.id} size="sm" className={isExpanded ? "md:col-span-2" : ""}>
              <CardContent className="space-y-0 py-0">
                {/* Integration header */}
                <div className="flex items-center gap-3">
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted ${categoryColors[def.category] || "text-foreground"}`}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm text-foreground">
                        {def.name}
                      </span>
                      <Badge variant="outline" className="text-[10px] h-4 px-1.5">
                        {def.category}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      {def.description}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {status === "connected" ? (
                      <Badge variant="default" className="gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Connected
                      </Badge>
                    ) : status === "error" ? (
                      <Badge variant="destructive" className="gap-1">
                        <Bug className="h-3 w-3" />
                        Error
                      </Badge>
                    ) : null}
                    <Button
                      variant={isExpanded ? "secondary" : "outline"}
                      size="sm"
                      onClick={() => handleExpand(def.id)}
                    >
                      {isExpanded ? (
                        <>
                          Close
                          <ChevronUp className="h-3 w-3 ml-1" />
                        </>
                      ) : status === "connected" ? (
                        "Reconfigure"
                      ) : (
                        <>
                          Configure
                          <ChevronDown className="h-3 w-3 ml-1" />
                        </>
                      )}
                    </Button>
                  </div>
                </div>

                {/* Expanded form */}
                {isExpanded && (
                  <div className="pt-4 mt-4 border-t border-border space-y-4">
                    {def.fields.map((field) => (
                      <div key={field.key} className="space-y-1.5">
                        <Label htmlFor={`${def.id}-${field.key}`} className="text-sm">
                          {field.label}
                        </Label>
                        <Input
                          id={`${def.id}-${field.key}`}
                          type={field.type || "text"}
                          placeholder={field.placeholder}
                          value={formValues[field.key] || ""}
                          onChange={(e) =>
                            handleFieldChange(field.key, e.target.value)
                          }
                          className="font-mono text-sm"
                        />
                      </div>
                    ))}
                    <div className="flex items-center gap-3 pt-1">
                      <Button
                        size="default"
                        onClick={() => handleTestConnection(def.id)}
                        disabled={
                          testingId === def.id ||
                          !def.fields.some((f) => formValues[f.key])
                        }
                      >
                        {testingId === def.id ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Testing...
                          </>
                        ) : (
                          "Test Connection"
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => {
                          setExpandedId(null)
                          setFormValues({})
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <Button variant="ghost" onClick={handleBack}>
          Back
        </Button>
        <div className="flex items-center gap-3">
          <button
            onClick={handleContinue}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Skip
          </button>
          <Button size="lg" onClick={handleContinue} className="min-w-[140px]">
            Continue
          </Button>
        </div>
      </div>
    </div>
  )
}
