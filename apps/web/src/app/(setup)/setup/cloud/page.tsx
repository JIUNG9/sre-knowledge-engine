"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import {
  Plus,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Cloud,
  Server,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useSetupStore, type CloudAccount } from "@/lib/stores/setup-store"

const providers = [
  { value: "aws", label: "AWS", icon: "aws" },
  { value: "gcp", label: "GCP", icon: "gcp" },
  { value: "azure", label: "Azure", icon: "azure" },
  { value: "ncloud", label: "a regional cloud", icon: "ncloud" },
  { value: "custom", label: "Custom", icon: "custom" },
] as const

const regions = [
  "us-east-1",
  "us-west-2",
  "eu-west-1",
  "eu-central-1",
  "ap-northeast-1",
  "ap-northeast-2",
  "ap-southeast-1",
  "ap-south-1",
  "ca-central-1",
]

function ProviderIcon({ provider }: { provider: string }) {
  const icons: Record<string, string> = {
    aws: "AWS",
    gcp: "GCP",
    azure: "AZ",
    ncloud: "NC",
    custom: "C",
  }
  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-xs font-mono font-bold text-primary">
      {icons[provider] || "?"}
    </div>
  )
}

export default function CloudAccountsPage() {
  const router = useRouter()
  const { accounts, addAccount, removeAccount, updateAccountStatus, setStep } =
    useSetupStore()

  const [showForm, setShowForm] = React.useState(false)
  const [testingId, setTestingId] = React.useState<string | null>(null)

  // Form state
  const [formProvider, setFormProvider] = React.useState<CloudAccount["provider"]>("aws")
  const [formName, setFormName] = React.useState("")
  const [formAlias, setFormAlias] = React.useState("")
  const [formAccountId, setFormAccountId] = React.useState("")
  const [formRegion, setFormRegion] = React.useState("us-east-1")
  const [formRole, setFormRole] = React.useState<CloudAccount["role"]>("standalone")
  const [formConnectionMethod, setFormConnectionMethod] = React.useState<CloudAccount["connectionMethod"]>("access-key")
  const [formConnectionValue, setFormConnectionValue] = React.useState("")

  const resetForm = () => {
    setFormProvider("aws")
    setFormName("")
    setFormAlias("")
    setFormAccountId("")
    setFormRegion("us-east-1")
    setFormRole("standalone")
    setFormConnectionMethod("access-key")
    setFormConnectionValue("")
  }

  const handleAddAccount = () => {
    const account: CloudAccount = {
      id: crypto.randomUUID(),
      provider: formProvider,
      name: formName,
      alias: formAlias,
      accountId: formAccountId,
      region: formRegion,
      role: formRole,
      connectionMethod: formConnectionMethod,
      connectionValue: formConnectionValue,
      status: "pending",
    }
    addAccount(account)
    resetForm()
    setShowForm(false)
  }

  const handleTestConnection = async (id: string) => {
    setTestingId(id)
    await new Promise((resolve) => setTimeout(resolve, 1200))
    updateAccountStatus(id, "connected")
    setTestingId(null)
  }

  const handleContinue = () => {
    setStep(2)
    router.push("/setup/integrations")
  }

  const handleBack = () => {
    setStep(0)
    router.push("/setup")
  }

  const isFormValid = formName && formAlias && formAccountId

  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight font-heading text-foreground">
          Connect Cloud Accounts
        </h2>
        <p className="text-sm text-muted-foreground">
          Add your AWS, GCP, Azure, or a regional cloud accounts. Aegis will monitor
          resources, costs, and security posture across all connected accounts.
        </p>
      </div>

      {/* Existing accounts */}
      {accounts.length > 0 && (
        <div className="space-y-3">
          {accounts.map((account) => (
            <Card key={account.id} size="sm">
              <CardContent className="flex items-center gap-4 py-0">
                <ProviderIcon provider={account.provider} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm text-foreground truncate">
                      {account.name}
                    </span>
                    <span className="text-xs text-muted-foreground font-mono">
                      ({account.alias})
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="uppercase">{account.provider}</span>
                    <span>·</span>
                    <span>{account.region}</span>
                    <span>·</span>
                    <span className="capitalize">{account.role}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {account.status === "connected" ? (
                    <Badge variant="default" className="gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      Connected
                    </Badge>
                  ) : account.status === "error" ? (
                    <Badge variant="destructive" className="gap-1">
                      <AlertCircle className="h-3 w-3" />
                      Error
                    </Badge>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestConnection(account.id)}
                      disabled={testingId === account.id}
                    >
                      {testingId === account.id ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        "Test"
                      )}
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => removeAccount(account.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add Account */}
      {!showForm ? (
        <Button
          variant="outline"
          className="w-full h-12 border-dashed gap-2"
          onClick={() => setShowForm(true)}
        >
          <Plus className="h-4 w-4" />
          Add Cloud Account
        </Button>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Cloud className="h-5 w-5 text-primary" />
              New Cloud Account
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Provider selector */}
            <div className="space-y-2">
              <Label className="text-sm">Provider</Label>
              <div className="flex gap-2">
                {providers.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => setFormProvider(p.value)}
                    className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors ${
                      formProvider === p.value
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-transparent text-muted-foreground hover:text-foreground hover:border-foreground/30"
                    }`}
                  >
                    <ProviderIcon provider={p.value} />
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Name + Alias */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="account-name" className="text-sm">
                  Account Name
                </Label>
                <Input
                  id="account-name"
                  placeholder="e.g., nexus"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Human-readable name for this account
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="account-alias" className="text-sm">
                  Alias
                </Label>
                <Input
                  id="account-alias"
                  placeholder="e.g., nx"
                  value={formAlias}
                  onChange={(e) => setFormAlias(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Short code used in dashboards
                </p>
              </div>
            </div>

            {/* Account ID */}
            <div className="space-y-2">
              <Label htmlFor="account-id" className="text-sm">
                Account ID / Project ID
              </Label>
              <Input
                id="account-id"
                placeholder="e.g., 123456789012"
                value={formAccountId}
                onChange={(e) => setFormAccountId(e.target.value)}
                className="font-mono"
              />
            </div>

            {/* Region + Role */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm">Region</Label>
                <Select
                  value={formRegion}
                  onValueChange={(val) => setFormRegion(val ?? "")}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {regions.map((r) => (
                      <SelectItem key={r} value={r}>
                        {r}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-sm">Role</Label>
                <Select
                  value={formRole}
                  onValueChange={(val) =>
                    setFormRole(val as CloudAccount["role"])
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="hub">Hub</SelectItem>
                    <SelectItem value="spoke">Spoke</SelectItem>
                    <SelectItem value="standalone">Standalone</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Hub-spoke for multi-account setups
                </p>
              </div>
            </div>

            {/* Connection Method */}
            <div className="space-y-2">
              <Label className="text-sm">Connection Method</Label>
              <div className="flex gap-3">
                <button
                  onClick={() => setFormConnectionMethod("access-key")}
                  className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm transition-colors ${
                    formConnectionMethod === "access-key"
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Server className="h-4 w-4" />
                  Access Key
                </button>
                <button
                  onClick={() => setFormConnectionMethod("assume-role")}
                  className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm transition-colors ${
                    formConnectionMethod === "assume-role"
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Server className="h-4 w-4" />
                  Assume Role ARN
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="connection-value" className="text-sm">
                {formConnectionMethod === "access-key"
                  ? "Access Key ID"
                  : "Role ARN"}
              </Label>
              <Input
                id="connection-value"
                type="password"
                placeholder={
                  formConnectionMethod === "access-key"
                    ? "AKIAIOSFODNN7EXAMPLE"
                    : "arn:aws:iam::123456789012:role/AegisRole"
                }
                value={formConnectionValue}
                onChange={(e) => setFormConnectionValue(e.target.value)}
                className="font-mono text-sm"
              />
            </div>

            {/* Form actions */}
            <div className="flex items-center gap-3 pt-2">
              <Button
                onClick={handleAddAccount}
                disabled={!isFormValid}
              >
                Add Account
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  resetForm()
                  setShowForm(false)
                }}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {accounts.length === 0 && !showForm && (
        <div className="text-center py-8 text-muted-foreground text-sm">
          <Cloud className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
          <p>No cloud accounts connected yet.</p>
          <p className="text-xs mt-1">
            Add at least one account to enable cloud monitoring and cost
            analysis.
          </p>
        </div>
      )}

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
