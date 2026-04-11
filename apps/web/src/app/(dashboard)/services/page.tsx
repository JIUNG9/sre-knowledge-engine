"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Server,
  GitBranch,
  Users,
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Building2,
} from "lucide-react";
import {
  useAccountStore,
  SERVICE_TO_ACCOUNT,
  getAccountName,
} from "@/lib/stores/account-store";

const services = [
  { name: "api-gateway", team: "Platform", status: "healthy", sloMeeting: 2, sloTotal: 2, language: "Go", deploys: "4.2/day", dependencies: ["auth-service", "user-service", "payment-service"] },
  { name: "auth-service", team: "Identity", status: "degraded", sloMeeting: 1, sloTotal: 2, language: "Go", deploys: "2.1/day", dependencies: ["user-service"] },
  { name: "user-service", team: "Platform", status: "healthy", sloMeeting: 1, sloTotal: 1, language: "Go", deploys: "1.5/day", dependencies: [] },
  { name: "payment-service", team: "Payments", status: "healthy", sloMeeting: 2, sloTotal: 2, language: "Java", deploys: "0.8/day", dependencies: ["auth-service"] },
  { name: "notification-service", team: "Messaging", status: "down", sloMeeting: 0, sloTotal: 2, language: "Python", deploys: "1.2/day", dependencies: ["user-service"] },
  { name: "deployment-controller", team: "Platform", status: "healthy", sloMeeting: 1, sloTotal: 1, language: "Go", deploys: "0.3/day", dependencies: [] },
];

const statusConfig: Record<string, { icon: React.ReactNode; color: string; border: string }> = {
  healthy: { icon: <CheckCircle2 className="h-5 w-5 text-green-400" />, color: "text-green-400", border: "border-green-400/20" },
  degraded: { icon: <AlertTriangle className="h-5 w-5 text-amber-400" />, color: "text-amber-400", border: "border-amber-400/20" },
  down: { icon: <XCircle className="h-5 w-5 text-red-400" />, color: "text-red-400", border: "border-red-400/20" },
};

export default function ServicesPage() {
  const { accounts } = useAccountStore();
  const [accountFilter, setAccountFilter] = useState<string | null>(null);

  const filteredServices = services.filter((s) => {
    if (!accountFilter) return true;
    return SERVICE_TO_ACCOUNT[s.name] === accountFilter;
  });

  const healthyCount = filteredServices.filter((s) => s.status === "healthy").length;
  const degradedCount = filteredServices.filter((s) => s.status === "degraded").length;
  const downCount = filteredServices.filter((s) => s.status === "down").length;

  return (
    <div className="space-y-6 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-2xl font-bold">Service Catalog</h1>
          <p className="mt-1 font-mono text-sm text-muted-foreground">
            Service registry, dependencies, health scorecards
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Select
            value={accountFilter ?? "all"}
            onValueChange={(v) => {
              if (v) setAccountFilter(v === "all" ? null : v);
            }}
          >
            <SelectTrigger className="h-10 font-mono text-sm">
              <Building2 className="size-4 text-[#A855F7]" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Accounts</SelectItem>
              {accounts.map((acct) => (
                <SelectItem key={acct.id} value={acct.id}>
                  <span className="flex items-center gap-2">
                    {acct.name}
                    <span className="rounded bg-muted/50 px-1.5 py-0.5 font-mono text-xs uppercase text-muted-foreground/60">
                      {acct.provider}
                    </span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex items-center gap-4 font-mono text-sm">
            <span className="flex items-center gap-1.5 text-green-400">
              <CheckCircle2 className="h-4 w-4" /> {healthyCount} healthy
            </span>
            <span className="flex items-center gap-1.5 text-amber-400">
              <AlertTriangle className="h-4 w-4" /> {degradedCount} degraded
            </span>
            <span className="flex items-center gap-1.5 text-red-400">
              <XCircle className="h-4 w-4" /> {downCount} down
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-5">
        {filteredServices.map((service) => {
          const config = statusConfig[service.status];
          return (
            <Card
              key={service.name}
              className={`border-border/50 ${config.border} bg-card p-6 hover:border-[#00FF88]/30 cursor-pointer transition-colors`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <Server className="h-5 w-5 text-[#00FF88]" />
                  <span className="font-mono text-base font-bold">{service.name}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  {config.icon}
                  <span className={`font-mono text-sm ${config.color}`}>{service.status}</span>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="flex items-center gap-2 font-mono text-sm text-muted-foreground">
                  <Users className="h-4 w-4" /> {service.team}
                </div>
                <div className="flex items-center gap-2 font-mono text-sm text-muted-foreground">
                  <GitBranch className="h-4 w-4" /> {service.language}
                </div>
                <div className="flex items-center gap-2 font-mono text-sm text-muted-foreground">
                  <Activity className="h-4 w-4" /> {service.deploys}
                </div>
                <div className="font-mono text-sm">
                  SLO: <span className={service.sloMeeting === service.sloTotal ? "text-green-400" : "text-amber-400"}>
                    {service.sloMeeting}/{service.sloTotal}
                  </span>
                </div>
              </div>

              {service.dependencies.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  <span className="font-mono text-xs text-muted-foreground">deps:</span>
                  {service.dependencies.map((dep) => (
                    <Badge key={dep} variant="outline" className="font-mono text-xs">
                      {dep}
                    </Badge>
                  ))}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
