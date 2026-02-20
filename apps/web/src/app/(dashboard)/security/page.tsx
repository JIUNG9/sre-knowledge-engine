"use client";

import { Shield, AlertTriangle, Lock, Eye, Bug } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const vulnerabilities = [
  { id: "CVE-2025-1234", title: "OpenSSL buffer overflow in libcrypto", severity: "critical", package: "openssl", version: "3.0.12", fixedVersion: "3.0.13", service: "api-gateway", scanner: "trivy", detectedAt: "2026-02-28T10:00:00Z" },
  { id: "CVE-2025-5678", title: "Go net/http request smuggling", severity: "high", package: "golang.org/x/net", version: "0.19.0", fixedVersion: "0.20.0", service: "api-gateway", scanner: "trivy", detectedAt: "2026-03-01T08:00:00Z" },
  { id: "CVE-2025-9012", title: "Python Pillow heap overflow", severity: "high", package: "Pillow", version: "10.1.0", fixedVersion: "10.2.0", service: "ai-engine", scanner: "snyk", detectedAt: "2026-03-02T14:00:00Z" },
  { id: "CVE-2025-3456", title: "Node.js path traversal in undici", severity: "medium", package: "undici", version: "5.26.0", fixedVersion: "5.27.0", service: "web", scanner: "trivy", detectedAt: "2026-03-03T09:00:00Z" },
  { id: "CVE-2025-7890", title: "Redis Lua sandbox escape", severity: "medium", package: "redis", version: "7.2.3", fixedVersion: "7.2.4", service: "infrastructure", scanner: "grype", detectedAt: "2026-03-04T11:00:00Z" },
  { id: "CVE-2025-2345", title: "PostgreSQL privilege escalation", severity: "low", package: "postgresql", version: "16.1", fixedVersion: "16.2", service: "infrastructure", scanner: "trivy", detectedAt: "2026-03-05T16:00:00Z" },
];

const complianceChecks = [
  { name: "Container images scanned", status: "pass", category: "CIS" },
  { name: "No root containers running", status: "pass", category: "CIS" },
  { name: "Secrets not in environment vars", status: "fail", category: "SOC2" },
  { name: "TLS 1.2+ enforced", status: "pass", category: "SOC2" },
  { name: "RBAC enforced on all endpoints", status: "pass", category: "ISO27001" },
  { name: "Audit logging enabled", status: "pass", category: "ISO27001" },
  { name: "Dependency audit < 30 days", status: "warn", category: "CIS" },
  { name: "Network policies defined", status: "pass", category: "CIS" },
];

const severityColors: Record<string, string> = {
  critical: "text-red-400 bg-red-400/10 border-red-400/30",
  high: "text-orange-400 bg-orange-400/10 border-orange-400/30",
  medium: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  low: "text-blue-400 bg-blue-400/10 border-blue-400/30",
};

export default function SecurityPage() {
  const criticalCount = vulnerabilities.filter((v) => v.severity === "critical").length;
  const highCount = vulnerabilities.filter((v) => v.severity === "high").length;
  const passCount = complianceChecks.filter((c) => c.status === "pass").length;
  const complianceScore = Math.round((passCount / complianceChecks.length) * 100);

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-2xl font-bold">Security Dashboard</h1>
          <p className="mt-1 font-mono text-sm text-muted-foreground">
            Vulnerability scanning, RBAC audit, compliance tracking
          </p>
        </div>
        <Badge variant="outline" className="font-mono text-xs">
          Last scan: 2h ago
        </Badge>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="border-border/50 bg-[#0D0D12] p-4">
          <div className="flex items-center gap-2">
            <Bug className="h-4 w-4 text-red-400" />
            <span className="font-mono text-xs text-muted-foreground">Critical</span>
          </div>
          <p className="mt-2 font-mono text-2xl font-bold text-red-400">{criticalCount}</p>
        </Card>
        <Card className="border-border/50 bg-[#0D0D12] p-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-orange-400" />
            <span className="font-mono text-xs text-muted-foreground">High</span>
          </div>
          <p className="mt-2 font-mono text-2xl font-bold text-orange-400">{highCount}</p>
        </Card>
        <Card className="border-border/50 bg-[#0D0D12] p-4">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-[#00FF88]" />
            <span className="font-mono text-xs text-muted-foreground">Compliance</span>
          </div>
          <p className="mt-2 font-mono text-2xl font-bold text-[#00FF88]">{complianceScore}%</p>
        </Card>
        <Card className="border-border/50 bg-[#0D0D12] p-4">
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-cyan-400" />
            <span className="font-mono text-xs text-muted-foreground">Total Vulns</span>
          </div>
          <p className="mt-2 font-mono text-2xl font-bold">{vulnerabilities.length}</p>
        </Card>
      </div>

      <Tabs defaultValue="vulnerabilities">
        <TabsList className="bg-[#0D0D12]">
          <TabsTrigger value="vulnerabilities" className="font-mono text-xs">Vulnerabilities</TabsTrigger>
          <TabsTrigger value="compliance" className="font-mono text-xs">Compliance</TabsTrigger>
          <TabsTrigger value="rbac" className="font-mono text-xs">RBAC Audit</TabsTrigger>
        </TabsList>

        <TabsContent value="vulnerabilities" className="mt-4 space-y-2">
          {vulnerabilities.map((vuln) => (
            <div key={vuln.id} className="flex items-center gap-3 rounded border border-border/50 bg-[#0D0D12] p-3">
              <Badge variant="outline" className={`font-mono text-[10px] ${severityColors[vuln.severity]}`}>
                {vuln.severity.toUpperCase()}
              </Badge>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-medium">{vuln.id}</span>
                  <span className="truncate text-sm text-muted-foreground">{vuln.title}</span>
                </div>
                <div className="mt-1 flex items-center gap-3 font-mono text-xs text-muted-foreground">
                  <span>{vuln.package}@{vuln.version}</span>
                  <span>→ {vuln.fixedVersion}</span>
                  <span>·</span>
                  <span>{vuln.service}</span>
                  <span>·</span>
                  <span>{vuln.scanner}</span>
                </div>
              </div>
            </div>
          ))}
        </TabsContent>

        <TabsContent value="compliance" className="mt-4 space-y-2">
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-sm">Overall Compliance Score</span>
              <span className="font-mono text-sm text-[#00FF88]">{complianceScore}%</span>
            </div>
            <Progress value={complianceScore} className="h-2" />
          </div>
          {complianceChecks.map((check, i) => (
            <div key={i} className="flex items-center gap-3 rounded border border-border/50 bg-[#0D0D12] p-3">
              <div className={`h-2 w-2 rounded-full ${check.status === "pass" ? "bg-green-400" : check.status === "fail" ? "bg-red-400" : "bg-amber-400"}`} />
              <span className="flex-1 font-mono text-sm">{check.name}</span>
              <Badge variant="outline" className="font-mono text-[10px]">{check.category}</Badge>
              <span className={`font-mono text-xs ${check.status === "pass" ? "text-green-400" : check.status === "fail" ? "text-red-400" : "text-amber-400"}`}>
                {check.status.toUpperCase()}
              </span>
            </div>
          ))}
        </TabsContent>

        <TabsContent value="rbac" className="mt-4">
          <div className="rounded border border-border/50 bg-[#0D0D12] p-6 text-center">
            <Eye className="mx-auto h-8 w-8 text-muted-foreground" />
            <p className="mt-2 font-mono text-sm text-muted-foreground">
              RBAC audit connected to Keycloak OIDC. 24 users, 6 roles, 3 teams.
            </p>
            <p className="mt-1 font-mono text-xs text-[#00FF88]">No permission drift detected.</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
