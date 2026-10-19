"use client"

import * as React from "react"
import {
  Cloud,
  Plus,
  Users,
  KeyRound,
  TestTube,
  Pencil,
  Unplug,
  UserPlus,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Globe,
  Server,
  Eye,
  EyeOff,
  Info,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
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
import { Checkbox } from "@/components/ui/checkbox"
import { Separator } from "@/components/ui/separator"
import { useAccountStore, type AccountProvider } from "@/lib/stores/account-store"

// ── Provider display config ───────────────────────────────────

const providerConfig: Record<
  AccountProvider | "custom",
  { label: string; color: string; bgColor: string; borderColor: string }
> = {
  aws: {
    label: "AWS",
    color: "#FF9900",
    bgColor: "bg-[#FF9900]/10",
    borderColor: "border-[#FF9900]/30",
  },
  gcp: {
    label: "GCP",
    color: "#4285F4",
    bgColor: "bg-[#4285F4]/10",
    borderColor: "border-[#4285F4]/30",
  },
  azure: {
    label: "Azure",
    color: "#0078D4",
    bgColor: "bg-[#0078D4]/10",
    borderColor: "border-[#0078D4]/30",
  },
  ncloud: {
    label: "NCloud",
    color: "#03CF5D",
    bgColor: "bg-[#03CF5D]/10",
    borderColor: "border-[#03CF5D]/30",
  },
  custom: {
    label: "Custom",
    color: "#A855F7",
    bgColor: "bg-[#A855F7]/10",
    borderColor: "border-[#A855F7]/30",
  },
}

const roleLabels: Record<string, { label: string; color: string }> = {
  hub: { label: "Hub", color: "text-primary bg-primary/10 border-primary/30" },
  spoke: {
    label: "Spoke",
    color: "text-blue-400 bg-blue-400/10 border-blue-400/30",
  },
  standalone: {
    label: "Standalone",
    color: "text-purple-400 bg-purple-400/10 border-purple-400/30",
  },
}

// ── Mock team members ─────────────────────────────────────────

type MemberRole = "Admin" | "Member" | "Viewer"

interface TeamMember {
  id: string
  name: string
  email: string
  role: MemberRole
  initials: string
  accountAccess: string[]
  lastActive: string
}

const TEAM_MEMBERS: TeamMember[] = [
  {
    id: "mem-1",
    name: "June Gu",
    email: "june.gu@acme-corp.com",
    role: "Admin",
    initials: "JG",
    accountAccess: ["hub", "shared-services", "prod-a", "prod-b"],
    lastActive: "2026-04-11T09:30:00Z",
  },
  {
    id: "mem-2",
    name: "Seungho Park",
    email: "sh.park@acme-corp.com",
    role: "Admin",
    initials: "SP",
    accountAccess: ["hub", "shared-services", "prod-a"],
    lastActive: "2026-04-11T08:15:00Z",
  },
  {
    id: "mem-3",
    name: "Minjae Kim",
    email: "mj.kim@acme-corp.com",
    role: "Member",
    initials: "MK",
    accountAccess: ["hub", "shared-services"],
    lastActive: "2026-04-10T17:22:00Z",
  },
  {
    id: "mem-4",
    name: "Yujin Lee",
    email: "yj.lee@acme-corp.com",
    role: "Member",
    initials: "YL",
    accountAccess: ["prod-a", "prod-b"],
    lastActive: "2026-04-10T14:00:00Z",
  },
  {
    id: "mem-5",
    name: "Donghyun Choi",
    email: "dh.choi@acme-corp.com",
    role: "Viewer",
    initials: "DC",
    accountAccess: ["hub"],
    lastActive: "2026-04-09T11:45:00Z",
  },
]

// ── SSO mock state ────────────────────────────────────────────

interface SSOConfig {
  providerName: string
  discoveryUrl: string
  clientId: string
  clientSecret: string
  realm: string
  connected: boolean
  enforceSSO: boolean
  allowLocalPassword: boolean
}

const DEFAULT_SSO: SSOConfig = {
  providerName: "Keycloak",
  discoveryUrl: "https://sso.acme-corp.com/realms/aegis/.well-known/openid-configuration",
  clientId: "aegis-dashboard",
  clientSecret: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  realm: "aegis",
  connected: true,
  enforceSSO: true,
  allowLocalPassword: false,
}

// ── Helpers ───────────────────────────────────────────────────

function timeAgo(ts: string) {
  const now = new Date("2026-04-11T10:00:00Z")
  const d = new Date(ts)
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / (1000 * 60))
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHrs = Math.floor(diffMin / 60)
  if (diffHrs < 24) return `${diffHrs}h ago`
  const diffDays = Math.floor(diffHrs / 24)
  if (diffDays === 1) return "Yesterday"
  return `${diffDays}d ago`
}

function getRoleColor(role: MemberRole): string {
  switch (role) {
    case "Admin":
      return "text-purple-400 bg-purple-400/10 border-purple-400/30"
    case "Member":
      return "text-blue-400 bg-blue-400/10 border-blue-400/30"
    case "Viewer":
      return "text-muted-foreground bg-muted/50 border-border"
  }
}

// ── Cloud Accounts Tab ────────────────────────────────────────

function CloudAccountsTab() {
  const accounts = useAccountStore((s) => s.accounts)
  const [addOpen, setAddOpen] = React.useState(false)

  const connectedCount = accounts.filter((a) => a.status === "connected").length
  const disconnectedCount = accounts.filter(
    (a) => a.status === "disconnected"
  ).length

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
        <Card className="border-border/50 bg-card p-6">
          <div className="flex items-center gap-2">
            <Cloud className="size-5 text-muted-foreground" />
            <span className="font-mono text-sm text-muted-foreground">
              Total Accounts
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold">{accounts.length}</p>
        </Card>
        <Card className="border-border/50 bg-card p-6">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="size-5 text-emerald-400" />
            <span className="font-mono text-sm text-muted-foreground">
              Connected
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-emerald-400">
            {connectedCount}
          </p>
        </Card>
        <Card className="border-border/50 bg-card p-6">
          <div className="flex items-center gap-2">
            <XCircle className="size-5 text-red-400" />
            <span className="font-mono text-sm text-muted-foreground">
              Disconnected
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-red-400">
            {disconnectedCount}
          </p>
        </Card>
        <Card className="border-border/50 bg-card p-6">
          <div className="flex items-center gap-2">
            <Server className="size-5 text-primary" />
            <span className="font-mono text-sm text-muted-foreground">
              Hub Accounts
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-primary">
            {accounts.filter((a) => a.role === "hub").length}
          </p>
        </Card>
      </div>

      {/* Add Account button */}
      <div className="flex justify-end">
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger
            render={
              <Button size="sm" className="gap-1.5 font-mono text-sm">
                <Plus className="size-3.5" />
                Add Account
              </Button>
            }
          />
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-mono">Add Cloud Account</DialogTitle>
              <DialogDescription className="font-mono text-xs">
                Connect a new cloud provider account to Aegis.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label className="font-mono text-xs">Provider</Label>
                <Select defaultValue="aws">
                  <SelectTrigger className="w-full font-mono text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="aws">AWS</SelectItem>
                    <SelectItem value="gcp">GCP</SelectItem>
                    <SelectItem value="azure">Azure</SelectItem>
                    <SelectItem value="ncloud">NCloud</SelectItem>
                    <SelectItem value="custom">Custom</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label className="font-mono text-xs">Account Name</Label>
                  <Input
                    placeholder="e.g. production"
                    className="font-mono text-sm"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="font-mono text-xs">Alias</Label>
                  <Input
                    placeholder="e.g. prod"
                    className="font-mono text-sm"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label className="font-mono text-xs">
                  Account ID / Project ID
                </Label>
                <Input
                  placeholder="e.g. 123456789012"
                  className="font-mono text-sm"
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label className="font-mono text-xs">Region</Label>
                  <Select defaultValue="ap-northeast-2">
                    <SelectTrigger className="w-full font-mono text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="us-east-1">us-east-1</SelectItem>
                      <SelectItem value="us-west-2">us-west-2</SelectItem>
                      <SelectItem value="eu-west-1">eu-west-1</SelectItem>
                      <SelectItem value="ap-northeast-1">
                        ap-northeast-1
                      </SelectItem>
                      <SelectItem value="ap-northeast-2">
                        ap-northeast-2
                      </SelectItem>
                      <SelectItem value="ap-southeast-1">
                        ap-southeast-1
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label className="font-mono text-xs">Role</Label>
                  <Select defaultValue="spoke">
                    <SelectTrigger className="w-full font-mono text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hub">Hub</SelectItem>
                      <SelectItem value="spoke">Spoke</SelectItem>
                      <SelectItem value="standalone">Standalone</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label className="font-mono text-xs">Connection Method</Label>
                <Select defaultValue="assume-role">
                  <SelectTrigger className="w-full font-mono text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="access-key">Access Key</SelectItem>
                    <SelectItem value="assume-role">
                      Assume Role ARN
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="font-mono text-xs">
                  Assume Role ARN
                </Label>
                <Input
                  placeholder="arn:aws:iam::123456789012:role/AegisRole"
                  className="font-mono text-sm"
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                className="font-mono text-sm"
                onClick={() => setAddOpen(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                className="font-mono text-sm"
                onClick={() => setAddOpen(false)}
              >
                Connect Account
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Account cards */}
      <div className="grid gap-5 lg:grid-cols-2">
        {accounts.map((account) => {
          const provider = providerConfig[account.provider]
          const role = roleLabels[account.role] ?? roleLabels.standalone
          const isConnected = account.status === "connected"

          return (
            <Card
              key={account.id}
              className="border-border/50 bg-card p-6"
            >
              <div className="flex items-start gap-4">
                {/* Provider icon */}
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${provider.bgColor} ${provider.borderColor}`}
                >
                  <span
                    className="font-mono text-sm font-bold"
                    style={{ color: provider.color }}
                  >
                    {provider.label.slice(0, 2).toUpperCase()}
                  </span>
                </div>

                {/* Info */}
                <div className="flex-1 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-base font-semibold text-foreground">
                          {account.name}
                        </span>
                        <Badge
                          variant="outline"
                          className={`font-mono text-[10px] ${role.color}`}
                        >
                          {role.label}
                        </Badge>
                      </div>
                      <p className="mt-0.5 font-mono text-xs text-muted-foreground">
                        {account.alias} &middot; {account.accountId}
                      </p>
                    </div>
                    {/* Connection status */}
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`inline-block h-3 w-3 rounded-full ${
                          isConnected ? "bg-emerald-500" : "bg-red-500"
                        }`}
                      />
                      <span
                        className={`font-mono text-xs ${
                          isConnected
                            ? "text-emerald-400"
                            : "text-red-400"
                        }`}
                      >
                        {isConnected ? "Connected" : "Disconnected"}
                      </span>
                    </div>
                  </div>

                  {/* Details row */}
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1.5">
                      <Globe className="size-3.5 text-muted-foreground" />
                      <span className="font-mono text-xs text-muted-foreground">
                        {account.region}
                      </span>
                    </div>
                    <Badge
                      variant="outline"
                      className="font-mono text-[10px]"
                      style={{
                        borderColor: `${provider.color}40`,
                        color: provider.color,
                      }}
                    >
                      {provider.label}
                    </Badge>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 pt-1">
                    <Button
                      variant="outline"
                      size="xs"
                      className="gap-1 font-mono text-xs"
                    >
                      <TestTube className="size-3" />
                      Test Connection
                    </Button>
                    <Button
                      variant="outline"
                      size="xs"
                      className="gap-1 font-mono text-xs"
                    >
                      <Pencil className="size-3" />
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="xs"
                      className="gap-1 font-mono text-xs"
                    >
                      <Unplug className="size-3" />
                      Disconnect
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

// ── Team Access Tab ───────────────────────────────────────────

function TeamAccessTab() {
  const accounts = useAccountStore((s) => s.accounts)
  const [inviteOpen, setInviteOpen] = React.useState(false)

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 gap-5 lg:grid-cols-3">
        <Card className="border-border/50 bg-card p-6">
          <div className="flex items-center gap-2">
            <Users className="size-5 text-muted-foreground" />
            <span className="font-mono text-sm text-muted-foreground">
              Total Members
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold">
            {TEAM_MEMBERS.length}
          </p>
        </Card>
        <Card className="border-border/50 bg-card p-6">
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-5 text-purple-400" />
            <span className="font-mono text-sm text-muted-foreground">
              Admins
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-purple-400">
            {TEAM_MEMBERS.filter((m) => m.role === "Admin").length}
          </p>
        </Card>
        <Card className="border-border/50 bg-card p-6">
          <div className="flex items-center gap-2">
            <Users className="size-5 text-blue-400" />
            <span className="font-mono text-sm text-muted-foreground">
              Active Members
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-blue-400">
            {TEAM_MEMBERS.filter((m) => m.role === "Member").length}
          </p>
        </Card>
      </div>

      {/* Invite button */}
      <div className="flex justify-end">
        <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
          <DialogTrigger
            render={
              <Button size="sm" className="gap-1.5 font-mono text-sm">
                <UserPlus className="size-3.5" />
                Invite Member
              </Button>
            }
          />
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle className="font-mono">Invite Team Member</DialogTitle>
              <DialogDescription className="font-mono text-xs">
                Send an invitation to join your Aegis workspace.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label className="font-mono text-xs">Email Address</Label>
                <Input
                  type="email"
                  placeholder="colleague@company.com"
                  className="font-mono text-sm"
                />
              </div>
              <div className="space-y-2">
                <Label className="font-mono text-xs">Role</Label>
                <Select defaultValue="Member">
                  <SelectTrigger className="w-full font-mono text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Admin">Admin</SelectItem>
                    <SelectItem value="Member">Member</SelectItem>
                    <SelectItem value="Viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="font-mono text-xs">Account Access</Label>
                <div className="space-y-2 rounded-lg border border-border/50 p-3">
                  {accounts.map((account) => (
                    <label
                      key={account.id}
                      className="flex items-center gap-2 cursor-pointer"
                    >
                      <Checkbox />
                      <span className="font-mono text-sm text-foreground">
                        {account.name}
                      </span>
                      <span className="font-mono text-xs text-muted-foreground">
                        ({account.alias})
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                className="font-mono text-sm"
                onClick={() => setInviteOpen(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                className="font-mono text-sm"
                onClick={() => setInviteOpen(false)}
              >
                Send Invitation
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Team table */}
      <Card className="border-border/50 bg-card">
        <Table>
          <TableHeader>
            <TableRow className="border-border/50 hover:bg-transparent">
              <TableHead className="h-14 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Member
              </TableHead>
              <TableHead className="h-14 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Email
              </TableHead>
              <TableHead className="h-14 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Role
              </TableHead>
              <TableHead className="h-14 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Account Access
              </TableHead>
              <TableHead className="h-14 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Last Active
              </TableHead>
              <TableHead className="h-14 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Actions
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {TEAM_MEMBERS.map((member) => (
              <TableRow
                key={member.id}
                className="h-14 border-border/30 hover:bg-muted/30"
              >
                {/* Avatar + Name */}
                <TableCell>
                  <div className="flex items-center gap-3">
                    <Avatar size="default">
                      <AvatarFallback className="bg-muted font-mono text-xs font-bold text-foreground">
                        {member.initials}
                      </AvatarFallback>
                    </Avatar>
                    <span className="font-mono text-sm font-medium text-foreground">
                      {member.name}
                    </span>
                  </div>
                </TableCell>

                {/* Email */}
                <TableCell className="font-mono text-sm text-muted-foreground">
                  {member.email}
                </TableCell>

                {/* Role dropdown */}
                <TableCell>
                  <Select defaultValue={member.role}>
                    <SelectTrigger className="h-7 w-24 font-mono text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Admin">Admin</SelectItem>
                      <SelectItem value="Member">Member</SelectItem>
                      <SelectItem value="Viewer">Viewer</SelectItem>
                    </SelectContent>
                  </Select>
                </TableCell>

                {/* Account access */}
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {member.accountAccess.map((acc) => (
                      <span
                        key={acc}
                        className="rounded bg-muted/50 px-2 py-0.5 font-mono text-[10px] text-muted-foreground"
                      >
                        {acc}
                      </span>
                    ))}
                  </div>
                </TableCell>

                {/* Last active */}
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {timeAgo(member.lastActive)}
                </TableCell>

                {/* Actions */}
                <TableCell>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="outline"
                      size="xs"
                      className="gap-1 font-mono text-xs"
                    >
                      <Pencil className="size-3" />
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="xs"
                      className="font-mono text-xs"
                    >
                      Remove
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}

// ── SSO Configuration Tab ─────────────────────────────────────

function SSOConfigurationTab() {
  const [showSecret, setShowSecret] = React.useState(false)
  const [sso, setSso] = React.useState<SSOConfig>(DEFAULT_SSO)

  return (
    <div className="space-y-6">
      {/* Status card */}
      <Card className="border-border/50 bg-card p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-primary/30 bg-primary/10">
              <KeyRound className="size-5 text-primary" />
            </div>
            <div>
              <p className="font-mono text-base font-semibold text-foreground">
                SSO Status
              </p>
              <p className="font-mono text-xs text-muted-foreground">
                Single Sign-On via OIDC
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`inline-block h-3 w-3 rounded-full ${
                sso.connected ? "bg-emerald-500" : "bg-red-500"
              }`}
            />
            <span
              className={`font-mono text-sm font-medium ${
                sso.connected ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {sso.connected ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>
      </Card>

      {/* OIDC Configuration form */}
      <Card className="border-border/50 bg-card">
        <CardHeader className="border-b border-border/30">
          <CardTitle className="flex items-center gap-2 font-mono text-xl">
            <ShieldCheck className="size-5 text-primary" />
            OIDC Provider Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6 pt-6">
          <div className="grid gap-5 md:grid-cols-2">
            <div className="space-y-2">
              <Label className="font-mono text-xs">Provider Name</Label>
              <Input
                value={sso.providerName}
                onChange={(e) =>
                  setSso((p) => ({
                    ...p,
                    providerName: (e.target as HTMLInputElement).value,
                  }))
                }
                className="font-mono text-sm"
              />
            </div>
            <div className="space-y-2">
              <Label className="font-mono text-xs">Realm</Label>
              <Input
                value={sso.realm}
                onChange={(e) =>
                  setSso((p) => ({
                    ...p,
                    realm: (e.target as HTMLInputElement).value,
                  }))
                }
                className="font-mono text-sm"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="font-mono text-xs">OIDC Discovery URL</Label>
            <Input
              value={sso.discoveryUrl}
              onChange={(e) =>
                setSso((p) => ({
                  ...p,
                  discoveryUrl: (e.target as HTMLInputElement).value,
                }))
              }
              className="font-mono text-sm"
            />
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            <div className="space-y-2">
              <Label className="font-mono text-xs">Client ID</Label>
              <Input
                value={sso.clientId}
                onChange={(e) =>
                  setSso((p) => ({
                    ...p,
                    clientId: (e.target as HTMLInputElement).value,
                  }))
                }
                className="font-mono text-sm"
              />
            </div>
            <div className="space-y-2">
              <Label className="font-mono text-xs">Client Secret</Label>
              <div className="relative">
                <Input
                  type={showSecret ? "text" : "password"}
                  value={sso.clientSecret}
                  onChange={(e) =>
                    setSso((p) => ({
                      ...p,
                      clientSecret: (e.target as HTMLInputElement).value,
                    }))
                  }
                  className="pr-9 font-mono text-sm"
                />
                <button
                  type="button"
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  onClick={() => setShowSecret(!showSecret)}
                >
                  {showSecret ? (
                    <EyeOff className="size-4" />
                  ) : (
                    <Eye className="size-4" />
                  )}
                </button>
              </div>
            </div>
          </div>

          <Separator />

          {/* Test connection */}
          <div className="flex items-center justify-between rounded-lg border border-border/50 p-4">
            <div className="flex items-center gap-3">
              <TestTube className="size-5 text-muted-foreground" />
              <div>
                <p className="font-mono text-sm font-medium text-foreground">
                  Test SSO Connection
                </p>
                <p className="font-mono text-xs text-muted-foreground">
                  Verify the OIDC provider is reachable and configured
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {sso.connected && (
                <Badge
                  variant="outline"
                  className="gap-1 font-mono text-[10px] border-emerald-400/30 text-emerald-400"
                >
                  <CheckCircle2 className="size-3" />
                  Verified
                </Badge>
              )}
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5 font-mono text-sm"
              >
                <TestTube className="size-3.5" />
                Test Connection
              </Button>
            </div>
          </div>

          <Separator />

          {/* Toggles */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="font-mono text-sm">
                  Enforce SSO for all users
                </Label>
                <p className="font-mono text-xs text-muted-foreground">
                  All users must authenticate via the SSO provider
                </p>
              </div>
              <Switch
                checked={sso.enforceSSO}
                onCheckedChange={(checked) =>
                  setSso((p) => ({ ...p, enforceSSO: checked }))
                }
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="font-mono text-sm">
                  Allow local password login
                </Label>
                <p className="font-mono text-xs text-muted-foreground">
                  Users can sign in with email/password in addition to SSO
                </p>
              </div>
              <Switch
                checked={sso.allowLocalPassword}
                onCheckedChange={(checked) =>
                  setSso((p) => ({ ...p, allowLocalPassword: checked }))
                }
              />
            </div>
          </div>

          <Separator />

          {/* Info note */}
          <div className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-4">
            <Info className="mt-0.5 size-4 shrink-0 text-primary" />
            <p className="font-mono text-sm leading-relaxed text-foreground/80">
              When SSO is enabled, users will be redirected to your identity
              provider for authentication. Ensure your OIDC provider is
              correctly configured with the Aegis callback URL before
              enabling enforcement.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Save */}
      <div className="flex justify-end">
        <Button size="sm" className="font-mono text-sm">
          Save SSO Configuration
        </Button>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────

export default function AccountManagementPage() {
  return (
    <ScrollArea className="flex-1">
      <div className="space-y-6 p-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-mono text-2xl font-bold">
              Account Management
            </h1>
            <p className="mt-1 font-mono text-sm text-muted-foreground">
              Manage cloud accounts, team access, and SSO configuration
            </p>
          </div>
          <Badge variant="outline" className="font-mono text-xs">
            4 accounts connected
          </Badge>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="cloud-accounts">
          <TabsList className="bg-card">
            <TabsTrigger
              value="cloud-accounts"
              className="gap-1.5 font-mono text-sm"
            >
              <Cloud className="size-3.5" />
              Cloud Accounts
            </TabsTrigger>
            <TabsTrigger
              value="team-access"
              className="gap-1.5 font-mono text-sm"
            >
              <Users className="size-3.5" />
              Team Access
            </TabsTrigger>
            <TabsTrigger
              value="sso-config"
              className="gap-1.5 font-mono text-sm"
            >
              <KeyRound className="size-3.5" />
              SSO Configuration
            </TabsTrigger>
          </TabsList>

          <TabsContent value="cloud-accounts" className="mt-5">
            <CloudAccountsTab />
          </TabsContent>

          <TabsContent value="team-access" className="mt-5">
            <TeamAccessTab />
          </TabsContent>

          <TabsContent value="sso-config" className="mt-5">
            <SSOConfigurationTab />
          </TabsContent>
        </Tabs>
      </div>
    </ScrollArea>
  )
}
