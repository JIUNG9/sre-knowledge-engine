"use client"

import * as React from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardAction,
  CardDescription,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  Settings,
  Globe,
  Palette,
  RotateCcw,
  Plug,
  TestTube,
  Unplug,
  Cloud,
  Plus,
  Trash2,
  Brain,
  Key,
  Eye,
  EyeOff,
  BarChart3,
  RefreshCw,
  Users,
  UserPlus,
  Shield,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Wrench,
} from "lucide-react"
import { cn } from "@/lib/utils"

// =============================================================================
// Mock data
// =============================================================================

// --- Token usage (30 days) ---

const tokenUsageData = Array.from({ length: 30 }, (_, i) => ({
  date: `Apr ${i + 1}`,
  tokens: Math.floor(Math.random() * 50000) + 10000,
  cost: Number((Math.random() * 0.3 + 0.05).toFixed(2)),
}))

const TOKEN_MONTHLY_TOTAL = tokenUsageData.reduce((s, d) => s + d.tokens, 0)
const TOKEN_MONTHLY_COST = tokenUsageData.reduce((s, d) => s + d.cost, 0)

// --- Token usage by module ---

const moduleUsage = [
  { module: "Logs", tokens: 285000, color: "#00FF88" },
  { module: "SLO", tokens: 180000, color: "#00BFFF" },
  { module: "FinOps", tokens: 142000, color: "#FFB020" },
  { module: "Incidents", tokens: 210000, color: "#A855F7" },
  { module: "Security", tokens: 96000, color: "#FF6B6B" },
]

// --- Integrations ---

type IntegrationStatus = "connected" | "disconnected" | "error"

interface Integration {
  id: string
  name: string
  category: string
  status: IntegrationStatus
  icon: string
  description: string
}

const INTEGRATIONS: Integration[] = [
  {
    id: "int-1",
    name: "SigNoz",
    category: "Observability",
    status: "connected",
    icon: "SN",
    description: "Open-source APM & observability platform",
  },
  {
    id: "int-2",
    name: "Datadog",
    category: "Observability",
    status: "disconnected",
    icon: "DD",
    description: "Cloud monitoring and analytics platform",
  },
  {
    id: "int-3",
    name: "Prometheus",
    category: "Monitoring",
    status: "connected",
    icon: "PR",
    description: "Open-source monitoring and alerting toolkit",
  },
  {
    id: "int-4",
    name: "Slack",
    category: "Communication",
    status: "connected",
    icon: "SL",
    description: "Team messaging and notification channel",
  },
  {
    id: "int-5",
    name: "JIRA",
    category: "Project Management",
    status: "error",
    icon: "JI",
    description: "Issue tracking and project management",
  },
  {
    id: "int-6",
    name: "GitHub",
    category: "Source Control",
    status: "connected",
    icon: "GH",
    description: "Source code hosting and collaboration",
  },
  {
    id: "int-7",
    name: "ArgoCD",
    category: "GitOps",
    status: "connected",
    icon: "AC",
    description: "Declarative GitOps continuous delivery",
  },
  {
    id: "int-8",
    name: "Trivy",
    category: "Security",
    status: "disconnected",
    icon: "TV",
    description: "Vulnerability scanner for containers",
  },
]

// --- Cloud accounts ---

interface CloudAccount {
  id: string
  name: string
  provider: "AWS" | "GCP" | "Azure"
  region: string
  role: string
  status: "active" | "error" | "pending"
}

const CLOUD_ACCOUNTS: CloudAccount[] = [
  {
    id: "acc-1",
    name: "prod-main",
    provider: "AWS",
    region: "ap-northeast-2",
    role: "arn:aws:iam::123456789012:role/AegisReadOnly",
    status: "active",
  },
  {
    id: "acc-2",
    name: "prod-k8s",
    provider: "AWS",
    region: "ap-northeast-2",
    role: "arn:aws:iam::234567890123:role/AegisReadOnly",
    status: "active",
  },
  {
    id: "acc-3",
    name: "staging",
    provider: "AWS",
    region: "ap-northeast-2",
    role: "arn:aws:iam::345678901234:role/AegisReadOnly",
    status: "active",
  },
  {
    id: "acc-4",
    name: "shared",
    provider: "AWS",
    region: "ap-northeast-2",
    role: "arn:aws:iam::456789012345:role/AegisReadOnly",
    status: "error",
  },
  {
    id: "acc-5",
    name: "gcp-prod",
    provider: "GCP",
    region: "asia-northeast3",
    role: "projects/gcp-prod/serviceAccounts/aegis@...",
    status: "active",
  },
]

// --- Team members ---

type MemberRole = "Admin" | "Member" | "Viewer"

interface TeamMember {
  id: string
  name: string
  email: string
  role: MemberRole
  initials: string
}

const TEAM_MEMBERS: TeamMember[] = [
  {
    id: "mem-1",
    name: "June Gu",
    email: "june.gu@acme-corp.ai",
    role: "Admin",
    initials: "JG",
  },
  {
    id: "mem-2",
    name: "Seungho Park",
    email: "sh.park@acme-corp.ai",
    role: "Admin",
    initials: "SP",
  },
  {
    id: "mem-3",
    name: "Minjae Kim",
    email: "mj.kim@acme-corp.ai",
    role: "Member",
    initials: "MK",
  },
  {
    id: "mem-4",
    name: "Yujin Lee",
    email: "yj.lee@acme-corp.ai",
    role: "Member",
    initials: "YL",
  },
  {
    id: "mem-5",
    name: "Donghyun Choi",
    email: "dh.choi@acme-corp.ai",
    role: "Viewer",
    initials: "DC",
  },
]

// =============================================================================
// Helpers
// =============================================================================

function getStatusIcon(status: string) {
  switch (status) {
    case "connected":
    case "active":
      return <CheckCircle2 className="size-3.5 text-[#00FF88]" />
    case "error":
      return <AlertCircle className="size-3.5 text-[#FF4444]" />
    default:
      return <XCircle className="size-3.5 text-muted-foreground/50" />
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case "connected":
    case "active":
      return "Connected"
    case "error":
      return "Error"
    case "pending":
      return "Pending"
    default:
      return "Disconnected"
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case "connected":
    case "active":
      return "#00FF88"
    case "error":
      return "#FF4444"
    case "pending":
      return "#FFB020"
    default:
      return "rgba(255,255,255,0.3)"
  }
}

function getRoleColor(role: MemberRole): string {
  switch (role) {
    case "Admin":
      return "#A855F7"
    case "Member":
      return "#00BFFF"
    case "Viewer":
      return "rgba(255,255,255,0.4)"
  }
}

// =============================================================================
// General Tab
// =============================================================================

function GeneralTab() {
  return (
    <div className="space-y-6">
      <Card size="sm">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-muted-foreground">
            <Settings className="size-4 text-primary" />
            General Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <Label className="font-mono text-xs">Team Name</Label>
              <Input
                defaultValue="acme-corp SRE"
                className="font-mono text-sm"
              />
            </div>
            <div className="space-y-2">
              <Label className="font-mono text-xs">Default Language</Label>
              <Select defaultValue="en">
                <SelectTrigger className="w-full font-mono text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="ko">Korean</SelectItem>
                  <SelectItem value="ja">Japanese</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Separator />

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="font-mono text-sm">
                  <Palette className="mr-1.5 inline size-3.5" />
                  Theme Preference
                </Label>
                <p className="font-mono text-xs text-muted-foreground">
                  Choose between dark and light modes
                </p>
              </div>
              <Select defaultValue="dark">
                <SelectTrigger className="w-32 font-mono text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dark">Dark</SelectItem>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="system">System</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="font-mono text-sm">
                  <Globe className="mr-1.5 inline size-3.5" />
                  Compact Mode
                </Label>
                <p className="font-mono text-xs text-muted-foreground">
                  Reduce padding and spacing for denser layouts
                </p>
              </div>
              <Switch />
            </div>
          </div>

          <Separator />

          <div className="flex items-center justify-between rounded-lg border border-border/50 p-4">
            <div className="space-y-0.5">
              <p className="font-mono text-sm font-medium text-foreground">
                Setup Wizard
              </p>
              <p className="font-mono text-xs text-muted-foreground">
                Re-run the initial setup wizard to reconfigure integrations
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 font-mono text-xs"
            >
              <RotateCcw className="size-3" />
              Re-run Setup
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button size="sm" className="font-mono text-xs">
          Save Changes
        </Button>
      </div>
    </div>
  )
}

// =============================================================================
// Integrations Tab
// =============================================================================

function IntegrationCard({ integration }: { integration: Integration }) {
  const [expanded, setExpanded] = React.useState(false)
  const statusColor = getStatusColor(integration.status)

  return (
    <Card size="sm" className="overflow-hidden">
      <CardContent className="pt-4">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted font-mono text-xs font-bold text-foreground">
            {integration.icon}
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-medium text-foreground">
                  {integration.name}
                </span>
                <Badge
                  variant="outline"
                  className="gap-1 font-mono text-[10px]"
                  style={{
                    borderColor: `${statusColor}40`,
                    color: statusColor,
                  }}
                >
                  {getStatusIcon(integration.status)}
                  {getStatusLabel(integration.status)}
                </Badge>
              </div>
              <Button
                variant="ghost"
                size="icon-xs"
                onClick={() => setExpanded(!expanded)}
                className="text-muted-foreground"
              >
                <ChevronRight
                  className={cn(
                    "size-3.5 transition-transform",
                    expanded && "rotate-90"
                  )}
                />
              </Button>
            </div>
            <p className="mt-0.5 font-mono text-[10px] text-muted-foreground/50">
              {integration.category}
            </p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              {integration.description}
            </p>

            {/* Action buttons */}
            <div className="mt-3 flex items-center gap-2">
              {integration.status === "connected" ? (
                <>
                  <Button
                    variant="outline"
                    size="xs"
                    className="gap-1 font-mono text-xs"
                  >
                    <Wrench className="size-2.5" />
                    Configure
                  </Button>
                  <Button
                    variant="outline"
                    size="xs"
                    className="gap-1 font-mono text-xs"
                  >
                    <TestTube className="size-2.5" />
                    Test
                  </Button>
                  <Button
                    variant="destructive"
                    size="xs"
                    className="gap-1 font-mono text-xs"
                  >
                    <Unplug className="size-2.5" />
                    Disconnect
                  </Button>
                </>
              ) : integration.status === "error" ? (
                <>
                  <Button
                    variant="outline"
                    size="xs"
                    className="gap-1 font-mono text-xs"
                  >
                    <Wrench className="size-2.5" />
                    Configure
                  </Button>
                  <Button
                    variant="outline"
                    size="xs"
                    className="gap-1 font-mono text-xs text-[#FFB020]"
                  >
                    <RefreshCw className="size-2.5" />
                    Retry
                  </Button>
                </>
              ) : (
                <Button
                  variant="outline"
                  size="xs"
                  className="gap-1 font-mono text-xs"
                >
                  <Plug className="size-2.5" />
                  Connect
                </Button>
              )}
            </div>

            {/* Expandable config form */}
            {expanded && (
              <div className="mt-4 space-y-3 border-t border-border/50 pt-4">
                <div className="space-y-2">
                  <Label className="font-mono text-[10px]">Endpoint URL</Label>
                  <Input
                    defaultValue={
                      integration.status === "connected"
                        ? `https://${integration.name.toLowerCase()}.example.com`
                        : ""
                    }
                    placeholder="https://..."
                    className="font-mono text-xs"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="font-mono text-[10px]">API Key</Label>
                  <Input
                    type="password"
                    defaultValue={
                      integration.status === "connected" ? "sk-**********" : ""
                    }
                    placeholder="Enter API key"
                    className="font-mono text-xs"
                  />
                </div>
                <div className="flex justify-end">
                  <Button size="xs" className="font-mono text-xs">
                    Save Configuration
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function IntegrationsTab() {
  const connectedCount = INTEGRATIONS.filter(
    (i) => i.status === "connected"
  ).length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading text-lg font-semibold text-foreground">
            Integrations
          </h2>
          <p className="font-mono text-xs text-muted-foreground">
            {connectedCount} of {INTEGRATIONS.length} connected
          </p>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {INTEGRATIONS.map((integration) => (
          <IntegrationCard key={integration.id} integration={integration} />
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Cloud Accounts Tab
// =============================================================================

function AddAccountDialog() {
  const [open, setOpen] = React.useState(false)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm" className="gap-1.5 font-mono text-xs">
            <Plus className="size-3" />
            Add Account
          </Button>
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Cloud Account</DialogTitle>
          <DialogDescription>
            Connect a new cloud provider account for cost and resource
            monitoring.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label className="font-mono text-xs">Account Name</Label>
            <Input placeholder="e.g., prod-main" className="font-mono text-sm" />
          </div>
          <div className="space-y-2">
            <Label className="font-mono text-xs">Provider</Label>
            <Select defaultValue="aws">
              <SelectTrigger className="w-full font-mono text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="aws">AWS</SelectItem>
                <SelectItem value="gcp">GCP</SelectItem>
                <SelectItem value="azure">Azure</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="font-mono text-xs">Region</Label>
            <Input
              placeholder="e.g., ap-northeast-2"
              className="font-mono text-sm"
            />
          </div>
          <div className="space-y-2">
            <Label className="font-mono text-xs">IAM Role ARN</Label>
            <Input
              placeholder="arn:aws:iam::..."
              className="font-mono text-sm"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setOpen(false)}
            className="font-mono text-xs"
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={() => setOpen(false)}
            className="font-mono text-xs"
          >
            Add Account
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function CloudAccountsTab() {
  return (
    <div className="space-y-6">
      <Card size="sm">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-muted-foreground">
            <Cloud className="size-4 text-primary" />
            Cloud Accounts
          </CardTitle>
          <CardAction>
            <AddAccountDialog />
          </CardAction>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          {CLOUD_ACCOUNTS.map((account) => {
            const statusColor = getStatusColor(account.status)

            return (
              <div
                key={account.id}
                className="flex items-center justify-between rounded-lg border border-border/50 p-4"
              >
                <div className="flex items-center gap-4">
                  <div className="flex size-10 items-center justify-center rounded-lg bg-muted font-mono text-xs font-bold text-foreground">
                    {account.provider}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-medium text-foreground">
                        {account.name}
                      </span>
                      <Badge
                        variant="outline"
                        className="gap-1 font-mono text-[10px]"
                        style={{
                          borderColor: `${statusColor}40`,
                          color: statusColor,
                        }}
                      >
                        {getStatusIcon(account.status)}
                        {getStatusLabel(account.status)}
                      </Badge>
                    </div>
                    <p className="mt-0.5 font-mono text-xs text-muted-foreground">
                      {account.region}
                    </p>
                    <p className="mt-0.5 font-mono text-[10px] text-muted-foreground/50 max-w-md truncate">
                      {account.role}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="xs"
                    className="gap-1 font-mono text-xs"
                  >
                    <TestTube className="size-2.5" />
                    Test
                  </Button>
                  <Button
                    variant="outline"
                    size="xs"
                    className="gap-1 font-mono text-xs"
                  >
                    <Wrench className="size-2.5" />
                    Edit
                  </Button>
                  <Button
                    variant="destructive"
                    size="icon-xs"
                  >
                    <Trash2 className="size-2.5" />
                  </Button>
                </div>
              </div>
            )
          })}
        </CardContent>
      </Card>
    </div>
  )
}

// =============================================================================
// AI & Tokens Tab
// =============================================================================

interface TokenTooltipProps {
  active?: boolean
  payload?: Array<{
    value: number
    dataKey: string
    payload: { date: string; tokens: number; cost: number }
  }>
}

function TokenTooltip({ active, payload }: TokenTooltipProps) {
  if (!active || !payload || !payload.length) return null
  const item = payload[0].payload
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-mono text-muted-foreground">{item.date}</p>
      <p className="font-mono font-medium text-foreground">
        {item.tokens.toLocaleString()} tokens
      </p>
      <p className="font-mono text-xs text-muted-foreground">
        ${item.cost.toFixed(2)}
      </p>
    </div>
  )
}

interface ModuleTooltipProps {
  active?: boolean
  payload?: Array<{
    value: number
    payload: { module: string; tokens: number }
  }>
}

function ModuleTooltip({ active, payload }: ModuleTooltipProps) {
  if (!active || !payload || !payload.length) return null
  const item = payload[0].payload
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="font-mono font-medium text-foreground">
        {item.module}: {(item.tokens / 1000).toFixed(0)}K tokens
      </p>
    </div>
  )
}

function AITokensTab() {
  const [showKey, setShowKey] = React.useState(false)
  const monthlyBudget = 15.0

  return (
    <div className="space-y-6">
      {/* API Key */}
      <Card size="sm">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-muted-foreground">
            <Key className="size-4 text-primary" />
            Claude API Key
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <Input
                type={showKey ? "text" : "password"}
                defaultValue="sk-ant-api03-xxxxxxxxxxxxxxxxxxxx"
                className="font-mono text-sm"
                readOnly
              />
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowKey(!showKey)}
              className="text-muted-foreground"
            >
              {showKey ? (
                <EyeOff className="size-4" />
              ) : (
                <Eye className="size-4" />
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="font-mono text-xs"
            >
              Change Key
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Usage summary cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card size="sm">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Brain className="size-4 text-[#A855F7]" />
              <span className="font-mono text-xs text-muted-foreground">
                Tokens Used
              </span>
            </div>
            <p className="mt-2 font-mono text-3xl font-bold tracking-tight text-foreground">
              {(TOKEN_MONTHLY_TOTAL / 1000).toFixed(0)}K
            </p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              This month
            </p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <BarChart3 className="size-4 text-[#00BFFF]" />
              <span className="font-mono text-xs text-muted-foreground">
                Cost
              </span>
            </div>
            <p className="mt-2 font-mono text-3xl font-bold tracking-tight text-foreground">
              ${TOKEN_MONTHLY_COST.toFixed(2)}
            </p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              of ${monthlyBudget.toFixed(2)} budget
            </p>
          </CardContent>
        </Card>
        <Card size="sm">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <Shield className="size-4 text-[#00FF88]" />
              <span className="font-mono text-xs text-muted-foreground">
                Budget Remaining
              </span>
            </div>
            <p className="mt-2 font-mono text-3xl font-bold tracking-tight text-[#00FF88]">
              ${(monthlyBudget - TOKEN_MONTHLY_COST).toFixed(2)}
            </p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              {(
                ((monthlyBudget - TOKEN_MONTHLY_COST) / monthlyBudget) *
                100
              ).toFixed(0)}
              % remaining
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Monthly budget setting */}
      <Card size="sm">
        <CardHeader className="border-b">
          <CardTitle className="text-muted-foreground">
            Monthly Budget
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3">
            <Label className="font-mono text-xs">Monthly Limit (USD)</Label>
            <Input
              type="number"
              defaultValue="15.00"
              className="w-32 font-mono text-sm"
              step="0.50"
            />
            <Button size="sm" className="font-mono text-xs">
              Update
            </Button>
            <div className="ml-auto">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 font-mono text-xs text-muted-foreground"
              >
                <RefreshCw className="size-3" />
                Reset Monthly Counter
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Token usage chart */}
      <Card size="sm">
        <CardHeader className="border-b">
          <CardTitle className="text-muted-foreground">
            Token Usage (Last 30 Days)
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={tokenUsageData}
                margin={{ top: 8, right: 8, left: -10, bottom: 0 }}
              >
                <defs>
                  <linearGradient
                    id="tokenGrad"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="0%"
                      stopColor="#A855F7"
                      stopOpacity={0.25}
                    />
                    <stop
                      offset="100%"
                      stopColor="#A855F7"
                      stopOpacity={0.02}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(255,255,255,0.05)"
                  vertical={false}
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }}
                  tickLine={false}
                  axisLine={false}
                  interval={4}
                />
                <YAxis
                  tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val: number) => `${(val / 1000).toFixed(0)}K`}
                />
                <RechartsTooltip content={<TokenTooltip />} />
                <Area
                  type="monotone"
                  dataKey="tokens"
                  stroke="#A855F7"
                  strokeWidth={2}
                  fill="url(#tokenGrad)"
                  dot={false}
                  activeDot={{
                    r: 4,
                    fill: "#A855F7",
                    stroke: "rgba(10,10,15,0.8)",
                    strokeWidth: 2,
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Usage by module */}
      <Card size="sm">
        <CardHeader className="border-b">
          <CardTitle className="text-muted-foreground">
            Usage by Module
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={moduleUsage}
                margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
                layout="vertical"
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(255,255,255,0.05)"
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val: number) => `${(val / 1000).toFixed(0)}K`}
                />
                <YAxis
                  type="category"
                  dataKey="module"
                  tick={{ fontSize: 11, fill: "rgba(255,255,255,0.7)" }}
                  tickLine={false}
                  axisLine={false}
                  width={70}
                />
                <RechartsTooltip content={<ModuleTooltip />} />
                <Bar dataKey="tokens" radius={[0, 4, 4, 0]} barSize={20}>
                  {moduleUsage.map((entry) => (
                    <Cell key={entry.module} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// =============================================================================
// Team Tab
// =============================================================================

function AddMemberDialog() {
  const [open, setOpen] = React.useState(false)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm" className="gap-1.5 font-mono text-xs">
            <UserPlus className="size-3" />
            Add Member
          </Button>
        }
      />
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Team Member</DialogTitle>
          <DialogDescription>
            Invite a new team member to the Aegis dashboard.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label className="font-mono text-xs">Full Name</Label>
            <Input placeholder="e.g., Jane Doe" className="font-mono text-sm" />
          </div>
          <div className="space-y-2">
            <Label className="font-mono text-xs">Email</Label>
            <Input
              type="email"
              placeholder="e.g., jane@acme-corp.ai"
              className="font-mono text-sm"
            />
          </div>
          <div className="space-y-2">
            <Label className="font-mono text-xs">Role</Label>
            <Select defaultValue="Member">
              <SelectTrigger className="w-full font-mono text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Admin">Admin</SelectItem>
                <SelectItem value="Member">Member</SelectItem>
                <SelectItem value="Viewer">Viewer</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setOpen(false)}
            className="font-mono text-xs"
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={() => setOpen(false)}
            className="font-mono text-xs"
          >
            Send Invite
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function TeamTab() {
  return (
    <div className="space-y-6">
      <Card size="sm">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-muted-foreground">
            <Users className="size-4 text-primary" />
            Team Members
            <Badge variant="outline" className="font-mono text-xs">
              {TEAM_MEMBERS.length} members
            </Badge>
          </CardTitle>
          <CardAction>
            <AddMemberDialog />
          </CardAction>
        </CardHeader>
        <CardContent className="space-y-3 pt-4">
          {TEAM_MEMBERS.map((member) => {
            const roleColor = getRoleColor(member.role)

            return (
              <div
                key={member.id}
                className="flex items-center justify-between rounded-lg border border-border/50 p-4"
              >
                <div className="flex items-center gap-3">
                  <Avatar>
                    <AvatarFallback className="font-mono text-xs">
                      {member.initials}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <span className="font-mono text-sm font-medium text-foreground">
                      {member.name}
                    </span>
                    <p className="font-mono text-xs text-muted-foreground">
                      {member.email}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Select defaultValue={member.role}>
                    <SelectTrigger className="w-28 font-mono text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Admin">Admin</SelectItem>
                      <SelectItem value="Member">Member</SelectItem>
                      <SelectItem value="Viewer">Viewer</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    variant="destructive"
                    size="icon-xs"
                  >
                    <Trash2 className="size-2.5" />
                  </Button>
                </div>
              </div>
            )
          })}
        </CardContent>
      </Card>
    </div>
  )
}

// =============================================================================
// Main Settings Page
// =============================================================================

export default function SettingsPage() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-border px-6 py-4">
        <Settings className="size-5 text-primary" />
        <h1 className="font-heading text-xl font-semibold text-foreground text-glow">
          Settings
        </h1>
        <span className="font-mono text-sm text-muted-foreground">
          Dashboard Configuration
        </span>
      </div>

      {/* Tabs navigation */}
      <Tabs defaultValue="general" className="flex flex-1 flex-col overflow-hidden">
        <div className="border-b border-border px-6 pt-2">
          <TabsList variant="line">
            <TabsTrigger value="general" className="font-mono text-sm">
              General
            </TabsTrigger>
            <TabsTrigger value="integrations" className="font-mono text-sm">
              Integrations
            </TabsTrigger>
            <TabsTrigger value="cloud" className="font-mono text-sm">
              Cloud Accounts
            </TabsTrigger>
            <TabsTrigger value="ai" className="font-mono text-sm">
              AI & Tokens
            </TabsTrigger>
            <TabsTrigger value="team" className="font-mono text-sm">
              Team
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Scrollable content */}
        <ScrollArea className="flex-1">
          <TabsContent value="general">
            <div className="p-6">
              <GeneralTab />
            </div>
          </TabsContent>

          <TabsContent value="integrations">
            <div className="p-6">
              <IntegrationsTab />
            </div>
          </TabsContent>

          <TabsContent value="cloud">
            <div className="p-6">
              <CloudAccountsTab />
            </div>
          </TabsContent>

          <TabsContent value="ai">
            <div className="p-6">
              <AITokensTab />
            </div>
          </TabsContent>

          <TabsContent value="team">
            <div className="p-6">
              <TeamTab />
            </div>
          </TabsContent>
        </ScrollArea>
      </Tabs>
    </div>
  )
}
