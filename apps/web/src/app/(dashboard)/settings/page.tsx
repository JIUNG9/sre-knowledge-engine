"use client"

import * as React from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
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
  ChevronDown,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Wrench,
  Zap,
  Sparkles,
  Check,
  AlertTriangle,
  DollarSign,
  TrendingDown,
  MessageSquare,
  Bot,
  Database,
  SlidersHorizontal,
  BookOpen,
  Upload,
  FileText,
  X,
  Clock,
  Hash,
  Thermometer,
  RotateCw,
  Quote,
  Target,
  Search,
  Link,
  ShieldAlert,
} from "lucide-react"
import { useAIStore, type AIMode } from "@/lib/stores/ai-store"
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

// --- Daily spend (30 days) ---

const dailySpendData = Array.from({ length: 30 }, (_, i) => ({
  date: `Apr ${i + 1}`,
  spend: Number((Math.random() * 0.45 + 0.05).toFixed(2)),
}))

// --- Spend by mode ---

const spendByMode = [
  { mode: "Eco", spend: 1.24, color: "#00BFFF" },
  { mode: "Standard", spend: 2.68, color: "#00FF88" },
  { mode: "Deep", spend: 0.9, color: "#A855F7" },
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
    role: "arn:aws:iam::111122223333:role/AegisReadOnly",
    status: "active",
  },
  {
    id: "acc-3",
    name: "staging",
    provider: "AWS",
    region: "ap-northeast-2",
    role: "arn:aws:iam::987654321098:role/AegisReadOnly",
    status: "active",
  },
  {
    id: "acc-4",
    name: "shared",
    provider: "AWS",
    region: "ap-northeast-2",
    role: "arn:aws:iam::000000000000:role/AegisReadOnly",
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
    email: "june.gu@acme-corp.com",
    role: "Admin",
    initials: "JG",
  },
  {
    id: "mem-2",
    name: "Seungho Park",
    email: "sh.park@acme-corp.com",
    role: "Admin",
    initials: "SP",
  },
  {
    id: "mem-3",
    name: "Minjae Kim",
    email: "mj.kim@acme-corp.com",
    role: "Member",
    initials: "MK",
  },
  {
    id: "mem-4",
    name: "Yujin Lee",
    email: "yj.lee@acme-corp.com",
    role: "Member",
    initials: "YL",
  },
  {
    id: "mem-5",
    name: "Donghyun Choi",
    email: "dh.choi@acme-corp.com",
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
                defaultValue="Platform SRE"
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
                        ? `https://${integration.name.toLowerCase()}.your-company.internal`
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

// --- Mode selection card data ---

const AI_MODES = [
  {
    id: "eco" as AIMode,
    label: "Eco",
    model: "Haiku 4.5",
    icon: Zap,
    color: "#00BFFF",
    inputCost: "$1",
    outputCost: "$5",
    features: [
      "Fast responses <2s",
      "Cached prompts",
      "2K max output tokens",
    ],
    bestFor: "Best for: monitoring, status checks",
    tagline: "10x cheaper than Standard",
  },
  {
    id: "standard" as AIMode,
    label: "Standard",
    model: "Sonnet 4.6",
    icon: Brain,
    color: "#00FF88",
    inputCost: "$3",
    outputCost: "$15",
    features: [
      "Balanced speed & quality",
      "Full tool-use support",
      "8K max output tokens",
    ],
    bestFor: "Best for: investigations, analysis",
    tagline: "Recommended for daily use",
  },
  {
    id: "deep" as AIMode,
    label: "Deep Analysis",
    model: "Opus 4.6",
    icon: Sparkles,
    color: "#A855F7",
    inputCost: "$5",
    outputCost: "$25",
    features: [
      "Deepest reasoning",
      "Unlimited tool calls",
      "No output limit",
    ],
    bestFor: "Best for: initial setup, critical incidents",
    tagline: "Use sparingly — 5x Standard cost",
  },
]

// --- Spend tooltip ---

interface SpendTooltipProps {
  active?: boolean
  payload?: Array<{
    value: number
    payload: { date: string; spend: number }
  }>
}

function SpendTooltip({ active, payload }: SpendTooltipProps) {
  if (!active || !payload || !payload.length) return null
  const item = payload[0].payload
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-mono text-muted-foreground">{item.date}</p>
      <p className="font-mono font-medium text-foreground">
        ${item.spend.toFixed(2)}
      </p>
    </div>
  )
}

interface ModeTooltipProps {
  active?: boolean
  payload?: Array<{
    value: number
    payload: { mode: string; spend: number }
  }>
}

function ModeTooltip({ active, payload }: ModeTooltipProps) {
  if (!active || !payload || !payload.length) return null
  const item = payload[0].payload
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="font-mono font-medium text-foreground">
        {item.mode}: ${item.spend.toFixed(2)}
      </p>
    </div>
  )
}

// =============================================================================
// Collapsible Section Component
// =============================================================================

function CollapsibleSection({
  icon: Icon,
  title,
  defaultOpen = false,
  children,
}: {
  icon: React.ElementType
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [isOpen, setIsOpen] = React.useState(defaultOpen)

  return (
    <div className="rounded-xl border border-border/50 bg-card overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center gap-3 px-5 py-4 text-left transition-colors hover:bg-muted/30"
      >
        <Icon className="size-4 text-primary shrink-0" />
        <span className="font-heading text-sm font-semibold text-foreground flex-1">
          {title}
        </span>
        {isOpen ? (
          <ChevronDown className="size-4 text-muted-foreground transition-transform" />
        ) : (
          <ChevronRight className="size-4 text-muted-foreground transition-transform" />
        )}
      </button>
      {isOpen && (
        <div className="border-t border-border/50 px-5 py-5">
          {children}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Button Group Component
// =============================================================================

function ButtonGroup<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { label: string; value: T; sublabel?: string }[]
  value: T
  onChange: (val: T) => void
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-lg border px-3.5 py-2 font-mono text-xs font-medium transition-all",
            value === opt.value
              ? "border-primary/40 bg-primary text-primary-foreground"
              : "border-border/50 bg-muted/50 text-foreground hover:border-border hover:bg-muted"
          )}
        >
          {opt.label}
          {opt.sublabel && (
            <span className="ml-1 opacity-60">{opt.sublabel}</span>
          )}
        </button>
      ))}
    </div>
  )
}

// =============================================================================
// Toggle Row Component
// =============================================================================

function ToggleRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string
  description?: string
  checked: boolean
  onChange: (val: boolean) => void
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="space-y-0.5">
        <Label className="font-mono text-sm">{label}</Label>
        {description && (
          <p className="font-mono text-[10px] text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={cn(
          "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors",
          checked ? "bg-[#00FF88]" : "bg-muted-foreground/30"
        )}
      >
        <span
          className={cn(
            "inline-block size-4.5 rounded-full bg-white shadow-sm transition-transform",
            checked ? "translate-x-5.5" : "translate-x-0.5"
          )}
        />
      </button>
    </div>
  )
}

// =============================================================================
// Tool Permission Types
// =============================================================================

type ToolPermission = "allow" | "approve" | "block"
type ToolCategory = "READ" | "WRITE" | "BLOCKED"

interface MCPTool {
  name: string
  category: ToolCategory
  defaultPermission: ToolPermission
}

const MCP_TOOLS: MCPTool[] = [
  { name: "query_logs", category: "READ", defaultPermission: "allow" },
  { name: "query_metrics", category: "READ", defaultPermission: "allow" },
  { name: "kubectl_read", category: "READ", defaultPermission: "allow" },
  { name: "kubectl_action", category: "WRITE", defaultPermission: "approve" },
  { name: "terraform_apply", category: "WRITE", defaultPermission: "approve" },
  { name: "terraform_destroy", category: "BLOCKED", defaultPermission: "block" },
  { name: "aws_iam_modify", category: "BLOCKED", defaultPermission: "block" },
]

function getCategoryColor(cat: ToolCategory): string {
  switch (cat) {
    case "READ":
      return "#00FF88"
    case "WRITE":
      return "#FFB020"
    case "BLOCKED":
      return "#FF4444"
  }
}

// =============================================================================
// Mock RAG Documents
// =============================================================================

interface RAGDocument {
  id: string
  name: string
  size: string
  indexedDate: string
}

const MOCK_RAG_DOCS: RAGDocument[] = [
  { id: "rag-1", name: "incident-response-runbook.md", size: "24 KB", indexedDate: "Apr 10, 2026" },
  { id: "rag-2", name: "k8s-architecture.pdf", size: "1.2 MB", indexedDate: "Apr 8, 2026" },
  { id: "rag-3", name: "terraform-modules.md", size: "18 KB", indexedDate: "Apr 11, 2026" },
]

function AITokensTab() {
  const [showKey, setShowKey] = React.useState(false)
  const {
    aiMode,
    setAIMode,
    monthlyBudget,
    monthlySpent,
    setMonthlyBudget,
    autoDowngradeThreshold,
    setAutoDowngradeThreshold,
    notificationThresholds,
    toggleNotificationThreshold,
  } = useAIStore()

  // --- Section 1: Response Preferences ---
  const [responseStyle, setResponseStyle] = React.useState<"brief" | "balanced" | "detailed">("balanced")
  const [outputLanguage, setOutputLanguage] = React.useState<"en" | "ko" | "auto">("en")
  const [autoSaveFindings, setAutoSaveFindings] = React.useState(true)
  const [showTokenCost, setShowTokenCost] = React.useState(true)
  const [preOperationConfirm, setPreOperationConfirm] = React.useState(true)

  // --- Section 2: Agent Behavior ---
  const [toolPermissions, setToolPermissions] = React.useState<Record<string, ToolPermission>>(
    Object.fromEntries(MCP_TOOLS.map((t) => [t.name, t.defaultPermission]))
  )
  const [fallbackChain, setFallbackChain] = React.useState<"opus-sonnet-haiku" | "sonnet-haiku" | "none">("opus-sonnet-haiku")
  const [trigger1Enabled, setTrigger1Enabled] = React.useState(true)
  const [trigger2Enabled, setTrigger2Enabled] = React.useState(true)
  const [trigger3Enabled, setTrigger3Enabled] = React.useState(false)

  // --- Section 3: Context Management ---
  const [contextWindow, setContextWindow] = React.useState<"5" | "10" | "20" | "unlimited">("10")
  const [promptCaching, setPromptCaching] = React.useState<"aggressive" | "balanced" | "conservative">("aggressive")
  const [serviceScope, setServiceScope] = React.useState<"current" | "all" | "custom">("current")
  const [historyRetention, setHistoryRetention] = React.useState<"7" | "30" | "90" | "forever">("30")
  const [includeSystemStatus, setIncludeSystemStatus] = React.useState(true)
  const [includeRecentIncidents, setIncludeRecentIncidents] = React.useState(true)

  // --- Section 4: Output & Quality ---
  const [temperature, setTemperature] = React.useState<"low" | "medium" | "high">("low")
  const [maxRetries, setMaxRetries] = React.useState<"1" | "3" | "5">("3")
  const [maxOutputTokens, setMaxOutputTokens] = React.useState<"2k" | "4k" | "8k" | "16k">("8k")
  const [structuredOutput, setStructuredOutput] = React.useState(false)
  const [citationMode, setCitationMode] = React.useState(true)
  const [confidenceScores, setConfidenceScores] = React.useState(true)

  // --- Section 5: Knowledge Base (RAG) ---
  const [ragEnabled, setRagEnabled] = React.useState(false)
  const [vectorDB, setVectorDB] = React.useState<"pgvector" | "qdrant" | "pinecone">("pgvector")
  const [syncConfluence, setSyncConfluence] = React.useState(false)
  const [syncNotion, setSyncNotion] = React.useState(false)
  const [syncGithubWiki, setSyncGithubWiki] = React.useState(false)
  const [ragDocs, setRagDocs] = React.useState<RAGDocument[]>(MOCK_RAG_DOCS)

  // --- Section 6: Safety & Guardrails ---
  const [antiHallucination, setAntiHallucination] = React.useState<"off" | "warn" | "strict">("warn")
  const [groundingMode, setGroundingMode] = React.useState<"hybrid" | "data-only">("hybrid")
  const [contextCap, setContextCap] = React.useState<"50k" | "100k" | "200k" | "unlimited">("100k")
  const [blockPII, setBlockPII] = React.useState(true)
  const [blockSecrets, setBlockSecrets] = React.useState(true)
  const [blockSQLInjection, setBlockSQLInjection] = React.useState(true)
  const [customRegexFilter, setCustomRegexFilter] = React.useState(false)
  const [validateCommands, setValidateCommands] = React.useState(true)
  const [blockDestructiveActions, setBlockDestructiveActions] = React.useState(true)
  const [validateJSONOutput, setValidateJSONOutput] = React.useState(false)
  const [redactSecretsOutput, setRedactSecretsOutput] = React.useState(true)
  const [blockProdNamespaces, setBlockProdNamespaces] = React.useState(true)
  const [requireDryRun, setRequireDryRun] = React.useState(false)
  const [logToolInputs, setLogToolInputs] = React.useState(true)
  const [aiAuditLog, setAiAuditLog] = React.useState(true)

  const usagePercent = Math.min((monthlySpent / monthlyBudget) * 100, 100)
  const budgetResetDate = "May 1, 2026"

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

      {/* ================================================================== */}
      {/* Mode Selection Cards                                                */}
      {/* ================================================================== */}

      <div>
        <h2 className="mb-1 font-heading text-lg font-semibold text-foreground">
          AI Mode
        </h2>
        <p className="mb-4 font-mono text-xs text-muted-foreground">
          Choose the Claude model for AI-powered features across all modules
        </p>
        <div className="grid gap-4 lg:grid-cols-3">
          {AI_MODES.map((mode) => {
            const Icon = mode.icon
            const isActive = aiMode === mode.id

            return (
              <button
                key={mode.id}
                onClick={() => setAIMode(mode.id)}
                className={cn(
                  "group relative flex flex-col rounded-xl border p-5 text-left transition-all duration-200",
                  isActive
                    ? "border-transparent"
                    : "border-border/50 hover:border-border"
                )}
                style={
                  isActive
                    ? {
                        boxShadow: `0 0 24px ${mode.color}20, inset 0 1px 0 ${mode.color}10, 0 0 0 2px ${mode.color}`,
                      }
                    : undefined
                }
              >
                {/* Active badge */}
                {isActive && (
                  <Badge
                    className="absolute top-3 right-3 gap-1 border-0 font-mono text-[10px]"
                    style={{
                      backgroundColor: `${mode.color}20`,
                      color: mode.color,
                    }}
                  >
                    <Check className="size-2.5" />
                    Active
                  </Badge>
                )}

                {/* Icon & title */}
                <div className="flex items-center gap-2.5">
                  <div
                    className="flex size-9 items-center justify-center rounded-lg"
                    style={{ backgroundColor: `${mode.color}15` }}
                  >
                    <Icon
                      className="size-4.5"
                      style={{ color: mode.color }}
                    />
                  </div>
                  <div>
                    <p className="font-heading text-sm font-semibold text-foreground">
                      {mode.label}
                    </p>
                    <p className="font-mono text-[10px] text-muted-foreground">
                      {mode.model}
                    </p>
                  </div>
                </div>

                {/* Pricing */}
                <div className="mt-4 flex items-baseline gap-2">
                  <span
                    className="font-mono text-xl font-bold"
                    style={{ color: mode.color }}
                  >
                    {mode.inputCost}
                  </span>
                  <span className="font-mono text-[10px] text-muted-foreground">
                    / {mode.outputCost} per 1M tokens
                  </span>
                </div>

                {/* Features */}
                <ul className="mt-3 space-y-1.5">
                  {mode.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-center gap-2 font-mono text-xs text-muted-foreground"
                    >
                      <Check
                        className="size-3 shrink-0"
                        style={{ color: mode.color }}
                      />
                      {feature}
                    </li>
                  ))}
                </ul>

                {/* Best for */}
                <Separator className="my-3" />
                <p className="font-mono text-[11px] font-medium text-foreground">
                  {mode.bestFor}
                </p>
                <p
                  className="mt-1 font-mono text-[10px]"
                  style={{ color: mode.color }}
                >
                  {mode.tagline}
                </p>
              </button>
            )
          })}
        </div>
      </div>

      {/* ================================================================== */}
      {/* Budget Guardrails                                                   */}
      {/* ================================================================== */}

      <Card size="sm">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-muted-foreground">
            <Shield className="size-4 text-primary" />
            Budget Guardrails
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6 pt-5">
          {/* Monthly budget input */}
          <div className="flex items-center gap-4">
            <div className="space-y-1.5">
              <Label className="font-mono text-xs">Monthly Budget (USD)</Label>
              <p className="font-mono text-[10px] text-muted-foreground">
                Maximum AI spend per calendar month
              </p>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <div className="relative">
                <DollarSign className="absolute left-2.5 top-1/2 size-3 -translate-y-1/2 text-muted-foreground" />
                <Input
                  type="number"
                  value={monthlyBudget}
                  onChange={(e) =>
                    setMonthlyBudget(Number(e.target.value) || 0)
                  }
                  className="w-28 pl-7 font-mono text-sm"
                  step="1.00"
                  min="0"
                />
              </div>
            </div>
          </div>

          <Separator />

          {/* Auto-downgrade threshold */}
          <div className="flex items-center gap-4">
            <div className="space-y-1.5">
              <Label className="font-mono text-xs">
                <TrendingDown className="mr-1.5 inline size-3" />
                Auto-Downgrade Threshold
              </Label>
              <p className="font-mono text-[10px] text-muted-foreground">
                Switches to Eco mode to preserve budget
              </p>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <Input
                type="number"
                value={autoDowngradeThreshold}
                onChange={(e) =>
                  setAutoDowngradeThreshold(Number(e.target.value) || 0)
                }
                className="w-20 font-mono text-sm"
                min="0"
                max="100"
              />
              <span className="font-mono text-xs text-muted-foreground">%</span>
            </div>
          </div>

          <Separator />

          {/* Notification thresholds */}
          <div>
            <Label className="font-mono text-xs">
              Notification Thresholds
            </Label>
            <p className="mt-1 mb-3 font-mono text-[10px] text-muted-foreground">
              Get alerted when spend reaches these levels
            </p>
            <div className="flex gap-2">
              {[50, 80, 100].map((threshold) => {
                const active = notificationThresholds.includes(threshold)
                return (
                  <button
                    key={threshold}
                    onClick={() => toggleNotificationThreshold(threshold)}
                    className={cn(
                      "flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 font-mono text-xs font-medium transition-all",
                      active
                        ? "border-primary/40 bg-primary/10 text-primary"
                        : "border-border/50 text-muted-foreground hover:border-border hover:text-foreground"
                    )}
                  >
                    {active && <Check className="size-3" />}
                    {threshold}%
                  </button>
                )
              })}
            </div>
          </div>

          <Separator />

          {/* Current usage progress */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <Label className="font-mono text-xs">Current Usage</Label>
              <span className="font-mono text-xs text-muted-foreground">
                ${monthlySpent.toFixed(2)} / ${monthlyBudget.toFixed(2)}
              </span>
            </div>
            <div className="relative h-3 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${usagePercent}%`,
                  backgroundColor:
                    usagePercent >= 100
                      ? "#FF4444"
                      : usagePercent >= 80
                        ? "#FFB020"
                        : "#00FF88",
                }}
              />
            </div>
            <p className="mt-1.5 font-mono text-[10px] text-muted-foreground">
              {usagePercent.toFixed(0)}% of monthly budget used
            </p>
          </div>
        </CardContent>
      </Card>

      {/* ================================================================== */}
      {/* Budget Exhaustion Warning                                           */}
      {/* ================================================================== */}

      <Card
        size="sm"
        className="border-[#FF4444]/20 bg-[#FF4444]/5"
      >
        <CardContent className="pt-4">
          <div className="flex items-start gap-3">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-[#FF4444]/15">
              <AlertTriangle className="size-4 text-[#FF4444]" />
            </div>
            <div className="flex-1">
              <p className="font-heading text-sm font-semibold text-[#FF4444]">
                When Budget is Exhausted
              </p>
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                Token budget exhausted. Resets on{" "}
                <span className="font-medium text-foreground">
                  {budgetResetDate}
                </span>
                .
              </p>
              <ul className="mt-3 space-y-2">
                <li className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                  <Zap className="size-3 shrink-0 text-[#00BFFF]" />
                  Switch to Eco mode (may still work within remaining tokens)
                </li>
                <li className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                  <CheckCircle2 className="size-3 shrink-0 text-[#00FF88]" />
                  All dashboard data still works — only AI features are paused
                </li>
                <li className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                  <RefreshCw className="size-3 shrink-0 text-[#FFB020]" />
                  Increase budget or wait for monthly reset
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ================================================================== */}
      {/* Section 1: Response Preferences (default OPEN)                     */}
      {/* ================================================================== */}

      <CollapsibleSection icon={MessageSquare} title="Response Preferences" defaultOpen>
        <div className="space-y-5">
          {/* Response style */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Response Style</Label>
            <ButtonGroup
              options={[
                { label: "Brief", value: "brief" as const },
                { label: "Balanced", value: "balanced" as const },
                { label: "Detailed", value: "detailed" as const },
              ]}
              value={responseStyle}
              onChange={setResponseStyle}
            />
          </div>

          {/* Output language */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Output Language</Label>
            <ButtonGroup
              options={[
                { label: "English", value: "en" as const },
                { label: "Korean", value: "ko" as const },
                { label: "Auto", value: "auto" as const },
              ]}
              value={outputLanguage}
              onChange={setOutputLanguage}
            />
          </div>

          <Separator />

          {/* Toggles */}
          <ToggleRow
            label="Auto-save findings"
            description="Automatically save AI investigation results"
            checked={autoSaveFindings}
            onChange={setAutoSaveFindings}
          />
          <ToggleRow
            label="Show token cost in responses"
            description="Display token usage and cost after each AI response"
            checked={showTokenCost}
            onChange={setShowTokenCost}
          />
          <ToggleRow
            label="Pre-operation confirmation"
            description="Ask before operations > $0.05"
            checked={preOperationConfirm}
            onChange={setPreOperationConfirm}
          />
        </div>
      </CollapsibleSection>

      {/* ================================================================== */}
      {/* Section 2: Agent Behavior / Harness (default CLOSED)              */}
      {/* ================================================================== */}

      <CollapsibleSection icon={Bot} title="Agent Behavior / Harness">
        <div className="space-y-6">
          {/* Tool Permissions Table */}
          <div className="space-y-3">
            <Label className="font-mono text-xs flex items-center gap-2">
              <Wrench className="size-3" />
              Tool Permissions
            </Label>
            <p className="font-mono text-[10px] text-muted-foreground">
              Control MCP tool access levels for AI agent operations
            </p>
            <div className="rounded-lg border border-border/50 overflow-hidden">
              {/* Table header */}
              <div className="grid grid-cols-[1fr_90px_200px] gap-3 bg-muted/30 px-4 py-2.5 border-b border-border/50">
                <span className="font-mono text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Tool</span>
                <span className="font-mono text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Category</span>
                <span className="font-mono text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Permission</span>
              </div>
              {/* Table rows */}
              {MCP_TOOLS.map((tool) => {
                const catColor = getCategoryColor(tool.category)
                const currentPerm = toolPermissions[tool.name]
                return (
                  <div
                    key={tool.name}
                    className="grid grid-cols-[1fr_90px_200px] gap-3 items-center px-4 py-3 border-b border-border/30 last:border-b-0 hover:bg-muted/20 transition-colors"
                  >
                    <span className="font-mono text-xs text-foreground">{tool.name}</span>
                    <Badge
                      variant="outline"
                      className="w-fit font-mono text-[10px] border-0"
                      style={{
                        backgroundColor: `${catColor}15`,
                        color: catColor,
                      }}
                    >
                      {tool.category}
                    </Badge>
                    <div className="flex gap-1.5">
                      {(["allow", "approve", "block"] as const).map((perm) => (
                        <button
                          key={perm}
                          onClick={() =>
                            setToolPermissions((prev) => ({
                              ...prev,
                              [tool.name]: perm,
                            }))
                          }
                          className={cn(
                            "rounded-md border px-2.5 py-1 font-mono text-[10px] font-medium capitalize transition-all",
                            currentPerm === perm
                              ? perm === "allow"
                                ? "border-[#00FF88]/40 bg-[#00FF88]/15 text-[#00FF88]"
                                : perm === "approve"
                                  ? "border-[#FFB020]/40 bg-[#FFB020]/15 text-[#FFB020]"
                                  : "border-[#FF4444]/40 bg-[#FF4444]/15 text-[#FF4444]"
                              : "border-border/50 text-muted-foreground/60 hover:border-border hover:text-muted-foreground"
                          )}
                        >
                          {perm}
                        </button>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <Separator />

          {/* Pre/Post Hooks */}
          <div className="space-y-3">
            <Label className="font-mono text-xs flex items-center gap-2">
              <Link className="size-3" />
              Pre/Post Hooks
            </Label>
            <div className="space-y-2">
              <div className="flex items-center gap-3 rounded-lg border border-border/50 p-3">
                <Badge
                  variant="outline"
                  className="shrink-0 font-mono text-[10px] border-[#00BFFF]/30 text-[#00BFFF] bg-[#00BFFF]/10"
                >
                  PRE-HOOK
                </Badge>
                <span className="font-mono text-xs text-foreground flex-1">
                  Before incident investigation &rarr; auto-pull last 1h logs
                </span>
              </div>
              <div className="flex items-center gap-3 rounded-lg border border-border/50 p-3">
                <Badge
                  variant="outline"
                  className="shrink-0 font-mono text-[10px] border-[#A855F7]/30 text-[#A855F7] bg-[#A855F7]/10"
                >
                  POST-HOOK
                </Badge>
                <span className="font-mono text-xs text-foreground flex-1">
                  After investigation &rarr; create JIRA ticket + notify Slack
                </span>
              </div>
              <button className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-border/50 p-3 font-mono text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary">
                <Plus className="size-3" />
                Add Hook
              </button>
            </div>
          </div>

          <Separator />

          {/* Automated Triggers */}
          <div className="space-y-3">
            <Label className="font-mono text-xs flex items-center gap-2">
              <Zap className="size-3" />
              Automated Triggers
            </Label>
            <div className="space-y-2">
              {[
                { condition: "Error budget < 10%", action: "Auto-investigate top error source", enabled: trigger1Enabled, toggle: setTrigger1Enabled },
                { condition: "Critical incident opened", action: "Start AI investigation", enabled: trigger2Enabled, toggle: setTrigger2Enabled },
                { condition: "Cost anomaly detected", action: "Analyze and notify Slack", enabled: trigger3Enabled, toggle: setTrigger3Enabled },
              ].map((trigger) => (
                <div
                  key={trigger.condition}
                  className="flex items-center gap-3 rounded-lg border border-border/50 p-3"
                >
                  <div className="flex-1 min-w-0">
                    <span className="font-mono text-xs text-foreground">
                      &ldquo;{trigger.condition}&rdquo;
                    </span>
                    <span className="font-mono text-xs text-muted-foreground mx-2">&rarr;</span>
                    <span className="font-mono text-xs text-muted-foreground">
                      &ldquo;{trigger.action}&rdquo;
                    </span>
                  </div>
                  <button
                    onClick={() => trigger.toggle(!trigger.enabled)}
                    className={cn(
                      "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors",
                      trigger.enabled ? "bg-[#00FF88]" : "bg-muted-foreground/30"
                    )}
                  >
                    <span
                      className={cn(
                        "inline-block size-4.5 rounded-full bg-white shadow-sm transition-transform",
                        trigger.enabled ? "translate-x-5.5" : "translate-x-0.5"
                      )}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <Separator />

          {/* Fallback Chain */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Fallback Chain</Label>
            <p className="font-mono text-[10px] text-muted-foreground">
              Model fallback order when primary model is unavailable or rate-limited
            </p>
            <ButtonGroup
              options={[
                { label: "Opus \u2192 Sonnet \u2192 Haiku", value: "opus-sonnet-haiku" as const },
                { label: "Sonnet \u2192 Haiku", value: "sonnet-haiku" as const },
                { label: "No fallback", value: "none" as const },
              ]}
              value={fallbackChain}
              onChange={setFallbackChain}
            />
          </div>
        </div>
      </CollapsibleSection>

      {/* ================================================================== */}
      {/* Section 3: Context Management (default CLOSED)                    */}
      {/* ================================================================== */}

      <CollapsibleSection icon={Database} title="Context Management">
        <div className="space-y-5">
          {/* Context window */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Context Window</Label>
            <p className="font-mono text-[10px] text-muted-foreground">
              Number of previous messages included in each AI request
            </p>
            <ButtonGroup
              options={[
                { label: "5 msgs", value: "5" as const },
                { label: "10 msgs", value: "10" as const },
                { label: "20 msgs", value: "20" as const },
                { label: "Unlimited", value: "unlimited" as const },
              ]}
              value={contextWindow}
              onChange={setContextWindow}
            />
          </div>

          {/* Prompt caching */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Prompt Caching</Label>
            <p className="font-mono text-[10px] text-muted-foreground">
              Cache static system prompts to reduce token costs
            </p>
            <ButtonGroup
              options={[
                { label: "Aggressive", value: "aggressive" as const },
                { label: "Balanced", value: "balanced" as const },
                { label: "Conservative", value: "conservative" as const },
              ]}
              value={promptCaching}
              onChange={setPromptCaching}
            />
          </div>

          {/* Service scope */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Service Scope</Label>
            <p className="font-mono text-[10px] text-muted-foreground">
              Which accounts the AI agent can access
            </p>
            <ButtonGroup
              options={[
                { label: "Current account", value: "current" as const },
                { label: "All accounts", value: "all" as const },
                { label: "Custom", value: "custom" as const },
              ]}
              value={serviceScope}
              onChange={setServiceScope}
            />
          </div>

          {/* History retention */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">History Retention</Label>
            <p className="font-mono text-[10px] text-muted-foreground">
              How long AI conversation history is kept
            </p>
            <ButtonGroup
              options={[
                { label: "7 days", value: "7" as const },
                { label: "30 days", value: "30" as const },
                { label: "90 days", value: "90" as const },
                { label: "Forever", value: "forever" as const },
              ]}
              value={historyRetention}
              onChange={setHistoryRetention}
            />
          </div>

          <Separator />

          {/* Toggles */}
          <ToggleRow
            label="Include system status"
            description="Auto-inject current system health into AI context"
            checked={includeSystemStatus}
            onChange={setIncludeSystemStatus}
          />
          <ToggleRow
            label="Include recent incidents"
            description="Auto-inject last 24h incidents into AI context"
            checked={includeRecentIncidents}
            onChange={setIncludeRecentIncidents}
          />
        </div>
      </CollapsibleSection>

      {/* ================================================================== */}
      {/* Section 4: Output & Quality (default CLOSED)                      */}
      {/* ================================================================== */}

      <CollapsibleSection icon={SlidersHorizontal} title="Output & Quality">
        <div className="space-y-5">
          {/* Temperature */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Temperature</Label>
            <p className="font-mono text-[10px] text-muted-foreground">
              Controls randomness in AI responses &mdash; lower is more deterministic
            </p>
            <ButtonGroup
              options={[
                { label: "Low", value: "low" as const, sublabel: "(0.1)" },
                { label: "Medium", value: "medium" as const, sublabel: "(0.5)" },
                { label: "High", value: "high" as const, sublabel: "(0.8)" },
              ]}
              value={temperature}
              onChange={setTemperature}
            />
          </div>

          {/* Max retries */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Max Retries</Label>
            <p className="font-mono text-[10px] text-muted-foreground">
              Number of retry attempts on AI request failure
            </p>
            <ButtonGroup
              options={[
                { label: "1", value: "1" as const },
                { label: "3", value: "3" as const },
                { label: "5", value: "5" as const },
              ]}
              value={maxRetries}
              onChange={setMaxRetries}
            />
          </div>

          {/* Max output tokens */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Max Output Tokens</Label>
            <p className="font-mono text-[10px] text-muted-foreground">
              Maximum tokens the AI can generate per response
            </p>
            <ButtonGroup
              options={[
                { label: "2K", value: "2k" as const },
                { label: "4K", value: "4k" as const },
                { label: "8K", value: "8k" as const },
                { label: "16K", value: "16k" as const },
              ]}
              value={maxOutputTokens}
              onChange={setMaxOutputTokens}
            />
          </div>

          <Separator />

          {/* Toggles */}
          <ToggleRow
            label="Structured output"
            description="Return AI responses in structured JSON format when applicable"
            checked={structuredOutput}
            onChange={setStructuredOutput}
          />
          <ToggleRow
            label="Citation mode"
            description="AI cites specific log lines and metric values"
            checked={citationMode}
            onChange={setCitationMode}
          />
          <ToggleRow
            label="Confidence scores"
            description="Show confidence percentage for AI findings and recommendations"
            checked={confidenceScores}
            onChange={setConfidenceScores}
          />
        </div>
      </CollapsibleSection>

      {/* ================================================================== */}
      {/* Section 5: Safety & Guardrails (default CLOSED)                   */}
      {/* ================================================================== */}

      <CollapsibleSection icon={ShieldAlert} title="Safety & Guardrails" defaultOpen={false}>
        <div className="space-y-5">

          {/* Anti-Hallucination Mode */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Anti-Hallucination Mode</Label>
            <p className="text-xs text-muted-foreground">Reject AI responses with claims not grounded in actual data</p>
            <ButtonGroup
              options={[
                { label: "Off", value: "off" },
                { label: "Warn", value: "warn" },
                { label: "Strict", value: "strict" },
              ]}
              value={antiHallucination}
              onChange={setAntiHallucination}
            />
          </div>

          {/* Grounding Mode */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Grounding Mode</Label>
            <p className="text-xs text-muted-foreground">Control what data sources AI can use for answers</p>
            <ButtonGroup
              options={[
                { label: "My Data + LLM", value: "hybrid" },
                { label: "My Data Only", value: "data-only" },
              ]}
              value={groundingMode}
              onChange={setGroundingMode}
            />
          </div>

          {/* Pre-LLM Input Validation */}
          <div>
            <Label className="font-mono text-xs mb-2 block">Pre-LLM Input Validation</Label>
            <p className="text-xs text-muted-foreground mb-3">Sanitize inputs before sending to Claude API</p>
            <div className="space-y-2">
              <ToggleRow label="Block PII" description="Strip personal identifiable information from prompts" checked={blockPII} onChange={setBlockPII} />
              <ToggleRow label="Block secrets" description="Detect and mask API keys, passwords, tokens in inputs" checked={blockSecrets} onChange={setBlockSecrets} />
              <ToggleRow label="Block SQL injection" description="Reject inputs containing SQL injection patterns" checked={blockSQLInjection} onChange={setBlockSQLInjection} />
              <ToggleRow label="Custom regex filter" description="Apply custom regex patterns to block specific content" checked={customRegexFilter} onChange={setCustomRegexFilter} />
            </div>
          </div>

          {/* Post-LLM Output Validation */}
          <div>
            <Label className="font-mono text-xs mb-2 block">Post-LLM Output Validation</Label>
            <p className="text-xs text-muted-foreground mb-3">Validate AI responses before showing to user</p>
            <div className="space-y-2">
              <ToggleRow label="Validate commands" description="Check kubectl/terraform commands for dangerous operations" checked={validateCommands} onChange={setValidateCommands} />
              <ToggleRow label="Block destructive actions" description="Reject responses suggesting rm -rf, DROP TABLE, force-push" checked={blockDestructiveActions} onChange={setBlockDestructiveActions} />
              <ToggleRow label="Validate JSON output" description="Ensure structured responses are valid JSON" checked={validateJSONOutput} onChange={setValidateJSONOutput} />
              <ToggleRow label="Redact secrets in output" description="Mask any secrets that appear in AI responses" checked={redactSecretsOutput} onChange={setRedactSecretsOutput} />
            </div>
          </div>

          {/* Pre-Tool Hook */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Pre-Tool Execution Hook</Label>
            <p className="text-xs text-muted-foreground">Inspect and validate MCP tool inputs before execution</p>
            <div className="space-y-2">
              <ToggleRow label="Block production namespaces" description="Prevent kubectl actions on 'production' and 'prod' namespaces" checked={blockProdNamespaces} onChange={setBlockProdNamespaces} />
              <ToggleRow label="Require dry-run first" description="Force --dry-run flag on all kubectl/terraform commands" checked={requireDryRun} onChange={setRequireDryRun} />
              <ToggleRow label="Log all tool inputs" description="Audit log every MCP tool call input for compliance" checked={logToolInputs} onChange={setLogToolInputs} />
            </div>
          </div>

          {/* AI Decision Audit Log */}
          <ToggleRow label="AI decision audit log" description="Tamper-proof log of every AI decision, tool call, and approval (SOC2 compliance)" checked={aiAuditLog} onChange={setAiAuditLog} />

          {/* Context Size Cap */}
          <div className="space-y-2">
            <Label className="font-mono text-xs">Context Size Cap</Label>
            <p className="text-xs text-muted-foreground">Hard limit to prevent accuracy degradation from token stuffing</p>
            <ButtonGroup
              options={[
                { label: "50K", value: "50k" },
                { label: "100K", value: "100k" },
                { label: "200K", value: "200k" },
                { label: "Unlimited", value: "unlimited" },
              ]}
              value={contextCap}
              onChange={setContextCap}
            />
          </div>

          {/* Warning card */}
          <div className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-4">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="size-4 text-amber-400" />
              <span className="text-sm font-semibold text-amber-400">Production Recommendation</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              For production environments, enable: Anti-Hallucination (Strict), Block PII, Block secrets,
              Validate commands, Block destructive actions, AI audit log, and Context cap at 100K.
            </p>
          </div>
        </div>
      </CollapsibleSection>

      {/* ================================================================== */}
      {/* Section 6: Knowledge Base (RAG) (default CLOSED)                  */}
      {/* ================================================================== */}

      <CollapsibleSection icon={BookOpen} title="Knowledge Base (RAG)">
        <div className="space-y-5">
          {/* Enable RAG toggle — prominent */}
          <div className="flex items-center justify-between gap-4 rounded-lg border border-border/50 bg-muted/20 p-4">
            <div className="space-y-1">
              <Label className="font-mono text-sm font-semibold">Enable RAG</Label>
              <p className="font-mono text-[10px] text-muted-foreground">
                Retrieval-Augmented Generation — AI uses your uploaded documents for more accurate, context-aware responses
              </p>
            </div>
            <button
              onClick={() => setRagEnabled(!ragEnabled)}
              className={cn(
                "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors",
                ragEnabled ? "bg-[#00FF88]" : "bg-muted-foreground/30"
              )}
            >
              <span
                className={cn(
                  "inline-block size-4.5 rounded-full bg-white shadow-sm transition-transform",
                  ragEnabled ? "translate-x-5.5" : "translate-x-0.5"
                )}
              />
            </button>
          </div>

          {ragEnabled && (
            <>
              {/* Upload area */}
              <div className="rounded-lg border-2 border-dashed border-border/50 p-8 text-center transition-colors hover:border-primary/30 hover:bg-muted/10">
                <Upload className="mx-auto size-8 text-muted-foreground/40" />
                <p className="mt-3 font-mono text-xs text-muted-foreground">
                  Drag & drop or click to upload runbooks, docs, post-mortems
                </p>
                <p className="mt-1 font-mono text-[10px] text-muted-foreground/50">
                  .md, .pdf, .txt
                </p>
              </div>

              {/* Uploaded documents */}
              <div className="space-y-2">
                <Label className="font-mono text-xs">Uploaded Documents</Label>
                {ragDocs.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-3 rounded-lg border border-border/50 p-3"
                  >
                    <FileText className="size-4 text-muted-foreground shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="font-mono text-xs text-foreground truncate">
                        {doc.name}
                      </p>
                      <p className="font-mono text-[10px] text-muted-foreground">
                        {doc.size} &middot; Indexed {doc.indexedDate}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      onClick={() => setRagDocs((prev) => prev.filter((d) => d.id !== doc.id))}
                      className="text-muted-foreground hover:text-[#FF4444]"
                    >
                      <X className="size-3" />
                    </Button>
                  </div>
                ))}
              </div>

              <Separator />

              {/* Vector DB provider */}
              <div className="space-y-2">
                <Label className="font-mono text-xs">Vector DB Provider</Label>
                <ButtonGroup
                  options={[
                    { label: "Built-in (pgvector)", value: "pgvector" as const },
                    { label: "Qdrant", value: "qdrant" as const },
                    { label: "Pinecone", value: "pinecone" as const },
                  ]}
                  value={vectorDB}
                  onChange={setVectorDB}
                />
              </div>

              {/* Auto-sync toggles */}
              <div className="space-y-3">
                <Label className="font-mono text-xs">Auto-sync from</Label>
                <ToggleRow
                  label="Confluence"
                  description="Sync knowledge base articles from Confluence"
                  checked={syncConfluence}
                  onChange={setSyncConfluence}
                />
                <ToggleRow
                  label="Notion"
                  description="Sync pages and databases from Notion"
                  checked={syncNotion}
                  onChange={setSyncNotion}
                />
                <ToggleRow
                  label="GitHub Wiki"
                  description="Sync wiki pages from GitHub repositories"
                  checked={syncGithubWiki}
                  onChange={setSyncGithubWiki}
                />
              </div>

              <Separator />

              {/* Indexing status */}
              <div className="flex items-center gap-2">
                <CheckCircle2 className="size-3.5 text-[#00FF88]" />
                <span className="font-mono text-xs text-foreground">
                  {ragDocs.length} documents indexed
                </span>
                <span className="font-mono text-[10px] text-muted-foreground">
                  &middot; Last sync: 2m ago
                </span>
              </div>

              {/* Token overhead notice */}
              <div className="rounded-lg border border-[#FFB020]/20 bg-[#FFB020]/5 p-4">
                <div className="flex items-start gap-2.5">
                  <AlertTriangle className="size-4 text-[#FFB020] shrink-0 mt-0.5" />
                  <div>
                    <p className="font-mono text-xs font-medium text-[#FFB020]">
                      Token Overhead Notice
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                      RAG adds ~2K-5K tokens per query (~$0.01-0.03 extra)
                    </p>
                  </div>
                </div>
              </div>

              {/* Test button */}
              <Button
                variant="outline"
                size="sm"
                className="gap-2 font-mono text-xs"
              >
                <Search className="size-3" />
                Test RAG &mdash; Ask a question to verify accuracy
              </Button>
            </>
          )}
        </div>
      </CollapsibleSection>

      {/* ================================================================== */}
      {/* Usage History                                                       */}
      {/* ================================================================== */}

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
                Total Cost
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
              ${Math.max(monthlyBudget - TOKEN_MONTHLY_COST, 0).toFixed(2)}
            </p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              {Math.max(
                ((monthlyBudget - TOKEN_MONTHLY_COST) / monthlyBudget) * 100,
                0
              ).toFixed(0)}
              % remaining
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Daily spend line chart */}
      <Card size="sm">
        <CardHeader className="border-b">
          <CardTitle className="text-muted-foreground">
            Daily Spend (Last 30 Days)
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={dailySpendData}
                margin={{ top: 8, right: 8, left: -10, bottom: 0 }}
              >
                <defs>
                  <linearGradient
                    id="spendGrad"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="0%"
                      stopColor="#00FF88"
                      stopOpacity={0.25}
                    />
                    <stop
                      offset="100%"
                      stopColor="#00FF88"
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
                  tickFormatter={(val: number) => `$${val.toFixed(2)}`}
                />
                <RechartsTooltip content={<SpendTooltip />} />
                <Line
                  type="monotone"
                  dataKey="spend"
                  stroke="#00FF88"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{
                    r: 4,
                    fill: "#00FF88",
                    stroke: "rgba(10,10,15,0.8)",
                    strokeWidth: 2,
                  }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Spend by module + Spend by mode — side by side */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Spend by module bar chart */}
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
                    tick={{
                      fontSize: 9,
                      fill: "rgba(255,255,255,0.4)",
                    }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val: number) =>
                      `${(val / 1000).toFixed(0)}K`
                    }
                  />
                  <YAxis
                    type="category"
                    dataKey="module"
                    tick={{
                      fontSize: 11,
                      fill: "rgba(255,255,255,0.7)",
                    }}
                    tickLine={false}
                    axisLine={false}
                    width={70}
                  />
                  <RechartsTooltip content={<ModuleTooltip />} />
                  <Bar
                    dataKey="tokens"
                    radius={[0, 4, 4, 0]}
                    barSize={20}
                  >
                    {moduleUsage.map((entry) => (
                      <Cell key={entry.module} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Spend by mode donut chart */}
        <Card size="sm">
          <CardHeader className="border-b">
            <CardTitle className="text-muted-foreground">
              Spend by Mode
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="flex items-center gap-6">
              <div className="size-[180px] shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={spendByMode}
                      dataKey="spend"
                      nameKey="mode"
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={70}
                      strokeWidth={0}
                    >
                      {spendByMode.map((entry) => (
                        <Cell key={entry.mode} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip content={<ModeTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-col gap-3">
                {spendByMode.map((entry) => (
                  <div key={entry.mode} className="flex items-center gap-3">
                    <div
                      className="size-3 rounded-full"
                      style={{ backgroundColor: entry.color }}
                    />
                    <div>
                      <p className="font-mono text-xs font-medium text-foreground">
                        {entry.mode}
                      </p>
                      <p className="font-mono text-[10px] text-muted-foreground">
                        ${entry.spend.toFixed(2)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
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
              placeholder="e.g., jane@acme-corp.com"
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
    <div className="h-full overflow-y-auto">
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
      <Tabs defaultValue="general">
        <div className="sticky top-0 z-10 border-b border-border bg-background px-6 pt-2">
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
      </Tabs>
    </div>
  )
}
