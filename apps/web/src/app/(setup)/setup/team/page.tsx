"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import {
  Plus,
  X,
  Users,
  Loader2,
  CheckCircle2,
  ShieldCheck,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
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
import {
  useSetupStore,
  type TeamMember,
  type KeycloakConfig,
} from "@/lib/stores/setup-store"

const roleColors: Record<string, string> = {
  admin: "default",
  member: "secondary",
  viewer: "outline",
}

export default function TeamPage() {
  const router = useRouter()
  const {
    teamName,
    members,
    keycloakEnabled,
    keycloakConfig,
    setTeamName,
    addMember,
    removeMember,
    setKeycloakEnabled,
    setKeycloakConfig,
    setStep,
  } = useSetupStore()

  // Member form state
  const [memberName, setMemberName] = React.useState("")
  const [memberEmail, setMemberEmail] = React.useState("")
  const [memberRole, setMemberRole] = React.useState<TeamMember["role"]>("member")
  const [showMemberForm, setShowMemberForm] = React.useState(false)

  // Keycloak form state
  const [kcUrl, setKcUrl] = React.useState(keycloakConfig?.url || "")
  const [kcRealm, setKcRealm] = React.useState(keycloakConfig?.realm || "")
  const [kcClientId, setKcClientId] = React.useState(keycloakConfig?.clientId || "")
  const [kcClientSecret, setKcClientSecret] = React.useState(keycloakConfig?.clientSecret || "")
  const [kcTesting, setKcTesting] = React.useState(false)
  const [kcTested, setKcTested] = React.useState(false)

  const handleAddMember = () => {
    if (!memberName || !memberEmail) return
    addMember({
      id: crypto.randomUUID(),
      name: memberName,
      email: memberEmail,
      role: memberRole,
    })
    setMemberName("")
    setMemberEmail("")
    setMemberRole("member")
    setShowMemberForm(false)
  }

  const handleKeycloakToggle = (checked: boolean) => {
    setKeycloakEnabled(checked)
    if (!checked) {
      setKeycloakConfig(null)
      setKcTested(false)
    }
  }

  const handleTestSSO = async () => {
    setKcTesting(true)
    await new Promise((resolve) => setTimeout(resolve, 1200))
    setKeycloakConfig({
      url: kcUrl,
      realm: kcRealm,
      clientId: kcClientId,
      clientSecret: kcClientSecret,
    })
    setKcTested(true)
    setKcTesting(false)
  }

  const handleContinue = () => {
    setStep(4)
    router.push("/setup/review")
  }

  const handleBack = () => {
    setStep(2)
    router.push("/setup/integrations")
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-tight font-heading text-foreground">
          Set Up Your Team
        </h2>
        <p className="text-sm text-muted-foreground">
          Configure your team name, invite members, and optionally set up SSO
          with Keycloak OIDC.
        </p>
      </div>

      {/* Team Name */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="h-5 w-5 text-primary" />
            Team Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="team-name" className="text-sm">
              Team Name
            </Label>
            <Input
              id="team-name"
              placeholder="e.g., Platform Engineering"
              value={teamName}
              onChange={(e) => setTeamName(e.target.value)}
              className="max-w-sm"
            />
            <p className="text-xs text-muted-foreground">
              This name appears in dashboards and notifications
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Team Members */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Team Members</CardTitle>
          <CardDescription>
            Add team members who will access Aegis. You can manage members later
            in Settings.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Member list */}
          {members.length > 0 && (
            <div className="space-y-2">
              {members.map((member) => (
                <div
                  key={member.id}
                  className="flex items-center gap-3 rounded-lg border border-border bg-muted/20 px-3 py-2"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                    {member.name
                      .split(" ")
                      .map((n) => n[0])
                      .join("")
                      .toUpperCase()
                      .slice(0, 2)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-foreground truncate">
                      {member.name}
                    </div>
                    <div className="text-xs text-muted-foreground truncate">
                      {member.email}
                    </div>
                  </div>
                  <Badge
                    variant={roleColors[member.role] as "default" | "secondary" | "outline"}
                    className="capitalize"
                  >
                    {member.role}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => removeMember(member.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* Add member form */}
          {showMemberForm ? (
            <div className="space-y-3 rounded-lg border border-border bg-muted/10 p-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="member-name" className="text-sm">
                    Name
                  </Label>
                  <Input
                    id="member-name"
                    placeholder="Jane Doe"
                    value={memberName}
                    onChange={(e) => setMemberName(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="member-email" className="text-sm">
                    Email
                  </Label>
                  <Input
                    id="member-email"
                    type="email"
                    placeholder="jane@company.com"
                    value={memberEmail}
                    onChange={(e) => setMemberEmail(e.target.value)}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-sm">Role</Label>
                <Select
                  value={memberRole}
                  onValueChange={(val) =>
                    setMemberRole(val as TeamMember["role"])
                  }
                >
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="member">Member</SelectItem>
                    <SelectItem value="viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Admins can manage settings. Members can view and act on
                  incidents. Viewers have read-only access.
                </p>
              </div>
              <div className="flex items-center gap-3 pt-1">
                <Button
                  onClick={handleAddMember}
                  disabled={!memberName || !memberEmail}
                >
                  Add Member
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setShowMemberForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <Button
              variant="outline"
              className="w-full h-10 border-dashed gap-2"
              onClick={() => setShowMemberForm(true)}
            >
              <Plus className="h-4 w-4" />
              Add Team Member
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Keycloak SSO */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="h-5 w-5 text-primary" />
            Single Sign-On (SSO)
          </CardTitle>
          <CardDescription>
            Optionally connect Keycloak OIDC for centralized authentication.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <Switch
              checked={keycloakEnabled}
              onCheckedChange={handleKeycloakToggle}
            />
            <Label className="text-sm">
              Enable Keycloak OIDC SSO
            </Label>
          </div>

          {keycloakEnabled && (
            <div className="space-y-3 rounded-lg border border-border bg-muted/10 p-4">
              <div className="space-y-1.5">
                <Label htmlFor="kc-url" className="text-sm">
                  Keycloak URL
                </Label>
                <Input
                  id="kc-url"
                  placeholder="https://keycloak.example.com"
                  value={kcUrl}
                  onChange={(e) => {
                    setKcUrl(e.target.value)
                    setKcTested(false)
                  }}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="kc-realm" className="text-sm">
                  Realm
                </Label>
                <Input
                  id="kc-realm"
                  placeholder="e.g., aegis"
                  value={kcRealm}
                  onChange={(e) => {
                    setKcRealm(e.target.value)
                    setKcTested(false)
                  }}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="kc-client-id" className="text-sm">
                    Client ID
                  </Label>
                  <Input
                    id="kc-client-id"
                    placeholder="aegis-web"
                    value={kcClientId}
                    onChange={(e) => {
                      setKcClientId(e.target.value)
                      setKcTested(false)
                    }}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="kc-client-secret" className="text-sm">
                    Client Secret
                  </Label>
                  <Input
                    id="kc-client-secret"
                    type="password"
                    placeholder="Client secret"
                    value={kcClientSecret}
                    onChange={(e) => {
                      setKcClientSecret(e.target.value)
                      setKcTested(false)
                    }}
                  />
                </div>
              </div>
              <div className="flex items-center gap-3 pt-1">
                <Button
                  variant="outline"
                  onClick={handleTestSSO}
                  disabled={kcTesting || !kcUrl || !kcRealm || !kcClientId}
                >
                  {kcTesting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Testing SSO...
                    </>
                  ) : kcTested ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-primary" />
                      SSO Connected
                    </>
                  ) : (
                    "Test SSO Connection"
                  )}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <Button variant="ghost" onClick={handleBack}>
          Back
        </Button>
        <Button size="lg" onClick={handleContinue} className="min-w-[140px]">
          Continue
        </Button>
      </div>
    </div>
  )
}
