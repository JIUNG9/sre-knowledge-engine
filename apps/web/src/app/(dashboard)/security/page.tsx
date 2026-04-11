"use client";

import { useState } from "react";
import { Shield, AlertTriangle, Lock, Bug, Eye } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SeverityOverrideDialog } from "@/components/security/severity-override-dialog";
import { ComplianceEditor } from "@/components/security/compliance-editor";
import { LogSourceManager } from "@/components/security/log-source-manager";
import {
  VULNERABILITIES,
  COMPLIANCE_CHECKS,
  LOG_SOURCES,
  SEVERITY_COLORS,
} from "@/lib/mock-data/security";
import type {
  Vulnerability,
  ComplianceCheck,
  LogSource,
  SeverityOverride,
} from "@/lib/mock-data/security";

export default function SecurityPage() {
  const [complianceChecks, setComplianceChecks] =
    useState<ComplianceCheck[]>(COMPLIANCE_CHECKS);
  const [logSources, setLogSources] = useState<LogSource[]>(LOG_SOURCES);
  const [overrides, setOverrides] = useState<SeverityOverride[]>([]);
  const [selectedVuln, setSelectedVuln] = useState<Vulnerability | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  function getEffectiveSeverity(vuln: Vulnerability) {
    const override = overrides.find((o) => o.cveId === vuln.id);
    return override ? override.newSeverity : vuln.severity;
  }

  function handleOverrideSave(
    data: Omit<SeverityOverride, "id" | "createdAt">
  ) {
    setOverrides((prev) => {
      const filtered = prev.filter((o) => o.cveId !== data.cveId);
      return [
        ...filtered,
        {
          ...data,
          id: `so-${Date.now()}`,
          createdAt: new Date().toISOString(),
        },
      ];
    });
  }

  const criticalCount = VULNERABILITIES.filter(
    (v) => getEffectiveSeverity(v) === "critical"
  ).length;
  const highCount = VULNERABILITIES.filter(
    (v) => getEffectiveSeverity(v) === "high"
  ).length;
  const passCount = complianceChecks.filter(
    (c) => c.status === "pass"
  ).length;
  const complianceScore =
    complianceChecks.length > 0
      ? Math.round((passCount / complianceChecks.length) * 100)
      : 0;

  return (
    <div className="space-y-6 p-8">
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
      <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
        <Card className="border-border/50 bg-card p-6">
          <div className="flex items-center gap-2">
            <Bug className="h-5 w-5 text-red-400" />
            <span className="font-mono text-sm text-muted-foreground">
              Critical
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-red-400">
            {criticalCount}
          </p>
        </Card>
        <Card className="border-border/50 bg-card p-6">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-400" />
            <span className="font-mono text-sm text-muted-foreground">
              High
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-orange-400">
            {highCount}
          </p>
        </Card>
        <Card className="border-border/50 bg-card p-6">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-[#00FF88]" />
            <span className="font-mono text-sm text-muted-foreground">
              Compliance
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold text-[#00FF88]">
            {complianceScore}%
          </p>
        </Card>
        <Card className="border-border/50 bg-card p-6">
          <div className="flex items-center gap-2">
            <Lock className="h-5 w-5 text-cyan-400" />
            <span className="font-mono text-sm text-muted-foreground">
              Total Vulns
            </span>
          </div>
          <p className="mt-3 font-mono text-3xl font-bold">
            {VULNERABILITIES.length}
          </p>
        </Card>
      </div>

      <Tabs defaultValue="vulnerabilities">
        <TabsList className="bg-card">
          <TabsTrigger value="vulnerabilities" className="font-mono text-sm">
            Vulnerabilities
          </TabsTrigger>
          <TabsTrigger value="compliance" className="font-mono text-sm">
            Compliance
          </TabsTrigger>
          <TabsTrigger value="logsources" className="font-mono text-sm">
            Log Sources
          </TabsTrigger>
        </TabsList>

        {/* Vulnerabilities tab */}
        <TabsContent value="vulnerabilities" className="mt-4 space-y-3">
          {overrides.length > 0 && (
            <div className="rounded border border-amber-400/20 bg-amber-400/5 p-3">
              <p className="font-mono text-xs text-amber-400">
                {overrides.length} severity override(s) active. Click a severity
                badge to edit.
              </p>
            </div>
          )}
          {VULNERABILITIES.map((vuln) => {
            const effective = getEffectiveSeverity(vuln);
            const hasOverride = overrides.some((o) => o.cveId === vuln.id);

            return (
              <div
                key={vuln.id}
                className="flex items-center gap-4 rounded border border-border/50 bg-card p-4"
              >
                <button
                  type="button"
                  onClick={() => {
                    setSelectedVuln(vuln);
                    setDialogOpen(true);
                  }}
                  className="flex-shrink-0"
                  title="Click to override severity"
                >
                  <Badge
                    variant="outline"
                    className={`cursor-pointer font-mono text-xs transition-colors hover:ring-1 hover:ring-white/20 ${SEVERITY_COLORS[effective]}`}
                  >
                    {hasOverride && (
                      <span className="mr-1 line-through opacity-50">
                        {vuln.severity.toUpperCase()}
                      </span>
                    )}
                    {effective.toUpperCase()}
                  </Badge>
                </button>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium">
                      {vuln.id}
                    </span>
                    <span className="truncate text-sm text-muted-foreground">
                      {vuln.title}
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center gap-3 font-mono text-sm text-muted-foreground">
                    <span>
                      {vuln.package}@{vuln.version}
                    </span>
                    <span>-&gt; {vuln.fixedVersion}</span>
                    <span>&middot;</span>
                    <span>{vuln.service}</span>
                    <span>&middot;</span>
                    <span>{vuln.scanner}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </TabsContent>

        {/* Compliance tab */}
        <TabsContent value="compliance" className="mt-4">
          <ComplianceEditor
            checks={complianceChecks}
            onChange={setComplianceChecks}
          />
        </TabsContent>

        {/* Log Sources tab */}
        <TabsContent value="logsources" className="mt-4">
          <LogSourceManager sources={logSources} onChange={setLogSources} />
        </TabsContent>
      </Tabs>

      {/* Override dialog */}
      <SeverityOverrideDialog
        vulnerability={selectedVuln}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSave={handleOverrideSave}
      />
    </div>
  );
}
