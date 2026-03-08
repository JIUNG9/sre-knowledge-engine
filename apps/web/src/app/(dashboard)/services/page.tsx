"use client";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Server,
  GitBranch,
  Users,
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
} from "lucide-react";

const services = [
  { name: "api-gateway", team: "Platform", status: "healthy", sloMeeting: 2, sloTotal: 2, language: "Go", deploys: "4.2/day", dependencies: ["auth-service", "user-service", "payment-service"] },
  { name: "auth-service", team: "Identity", status: "degraded", sloMeeting: 1, sloTotal: 2, language: "Go", deploys: "2.1/day", dependencies: ["user-service"] },
  { name: "user-service", team: "Platform", status: "healthy", sloMeeting: 1, sloTotal: 1, language: "Go", deploys: "1.5/day", dependencies: [] },
  { name: "payment-service", team: "Payments", status: "healthy", sloMeeting: 2, sloTotal: 2, language: "Java", deploys: "0.8/day", dependencies: ["auth-service"] },
  { name: "notification-service", team: "Messaging", status: "down", sloMeeting: 0, sloTotal: 2, language: "Python", deploys: "1.2/day", dependencies: ["user-service"] },
  { name: "deployment-controller", team: "Platform", status: "healthy", sloMeeting: 1, sloTotal: 1, language: "Go", deploys: "0.3/day", dependencies: [] },
];

const statusConfig: Record<string, { icon: React.ReactNode; color: string; border: string }> = {
  healthy: { icon: <CheckCircle2 className="h-4 w-4 text-green-400" />, color: "text-green-400", border: "border-green-400/20" },
  degraded: { icon: <AlertTriangle className="h-4 w-4 text-amber-400" />, color: "text-amber-400", border: "border-amber-400/20" },
  down: { icon: <XCircle className="h-4 w-4 text-red-400" />, color: "text-red-400", border: "border-red-400/20" },
};

export default function ServicesPage() {
  const healthyCount = services.filter((s) => s.status === "healthy").length;
  const degradedCount = services.filter((s) => s.status === "degraded").length;
  const downCount = services.filter((s) => s.status === "down").length;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-2xl font-bold">Service Catalog</h1>
          <p className="mt-1 font-mono text-sm text-muted-foreground">
            Service registry, dependencies, health scorecards
          </p>
        </div>
        <div className="flex items-center gap-3 font-mono text-sm">
          <span className="flex items-center gap-1 text-green-400">
            <CheckCircle2 className="h-3 w-3" /> {healthyCount} healthy
          </span>
          <span className="flex items-center gap-1 text-amber-400">
            <AlertTriangle className="h-3 w-3" /> {degradedCount} degraded
          </span>
          <span className="flex items-center gap-1 text-red-400">
            <XCircle className="h-3 w-3" /> {downCount} down
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {services.map((service) => {
          const config = statusConfig[service.status];
          return (
            <Card
              key={service.name}
              className={`border-border/50 ${config.border} bg-[#0D0D12] p-4 hover:border-[#00FF88]/30 cursor-pointer transition-colors`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <Server className="h-4 w-4 text-[#00FF88]" />
                  <span className="font-mono text-sm font-bold">{service.name}</span>
                </div>
                <div className="flex items-center gap-1">
                  {config.icon}
                  <span className={`font-mono text-xs ${config.color}`}>{service.status}</span>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-2">
                <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                  <Users className="h-3 w-3" /> {service.team}
                </div>
                <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                  <GitBranch className="h-3 w-3" /> {service.language}
                </div>
                <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                  <Activity className="h-3 w-3" /> {service.deploys}
                </div>
                <div className="font-mono text-xs">
                  SLO: <span className={service.sloMeeting === service.sloTotal ? "text-green-400" : "text-amber-400"}>
                    {service.sloMeeting}/{service.sloTotal}
                  </span>
                </div>
              </div>

              {service.dependencies.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  <span className="font-mono text-[10px] text-muted-foreground">deps:</span>
                  {service.dependencies.map((dep) => (
                    <Badge key={dep} variant="outline" className="font-mono text-[10px]">
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
