"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AccountFilter } from "@/components/account-filter";
import {
  Rocket,
  Clock,
  AlertTriangle,
  TrendingUp,
  CheckCircle2,
  XCircle,
  GitBranch,
} from "lucide-react";
import {
  SERVICE_TO_ACCOUNT,
} from "@/lib/stores/account-store";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";

const doraMetrics = {
  deploymentFrequency: { value: 4.2, unit: "deploys/day", trend: "+12%", rating: "Elite" },
  leadTime: { value: 2.3, unit: "hours", trend: "-18%", rating: "Elite" },
  changeFailureRate: { value: 4.8, unit: "%", trend: "-2.1%", rating: "High" },
  mttr: { value: 42, unit: "minutes", trend: "-15%", rating: "Elite" },
};

const recentDeployments = [
  { id: "deploy-042", service: "api-gateway", version: "v2.14.0", env: "production", status: "success", author: "junegu", duration: "3m 22s", timestamp: "2026-03-05T14:30:00Z" },
  { id: "deploy-041", service: "auth-service", version: "v1.8.3", env: "production", status: "success", author: "junegu", duration: "2m 45s", timestamp: "2026-03-05T10:15:00Z" },
  { id: "deploy-040", service: "payment-service", version: "v3.2.1", env: "production", status: "failed", author: "junegu", duration: "4m 10s", timestamp: "2026-03-04T16:45:00Z" },
  { id: "deploy-039", service: "user-service", version: "v2.5.0", env: "staging", status: "success", author: "junegu", duration: "2m 10s", timestamp: "2026-03-04T14:20:00Z" },
  { id: "deploy-038", service: "notification-service", version: "v1.12.0", env: "production", status: "success", author: "junegu", duration: "1m 55s", timestamp: "2026-03-04T09:00:00Z" },
  { id: "deploy-037", service: "api-gateway", version: "v2.13.2", env: "production", status: "rollback", author: "junegu", duration: "5m 30s", timestamp: "2026-03-03T17:00:00Z" },
];

const deployFrequencyData = Array.from({ length: 14 }, (_, i) => ({
  date: `Mar ${i + 1}`,
  deploys: Math.floor(Math.random() * 4) + 2,
}));

const leadTimeData = Array.from({ length: 14 }, (_, i) => ({
  date: `Mar ${i + 1}`,
  hours: Math.random() * 3 + 1,
}));

const statusColors: Record<string, string> = {
  success: "text-green-400 bg-green-400/10 border-green-400/30",
  failed: "text-red-400 bg-red-400/10 border-red-400/30",
  rollback: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  pending: "text-blue-400 bg-blue-400/10 border-blue-400/30",
};

const ratingColors: Record<string, string> = {
  Elite: "text-[#00FF88]",
  High: "text-cyan-400",
  Medium: "text-amber-400",
  Low: "text-red-400",
};

export default function DeploymentsPage() {
  const [accountFilter, setAccountFilter] = useState<string | null>(null);

  const filteredDeployments = recentDeployments.filter((deploy) => {
    if (!accountFilter) return true;
    return SERVICE_TO_ACCOUNT[deploy.service] === accountFilter;
  });

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="font-mono text-2xl font-bold">Deployment Tracker</h1>
        <p className="mt-1 font-mono text-sm text-muted-foreground">
          DORA metrics, deployment timeline, change failure rate
        </p>
      </div>

      {/* Account filter chips — below title */}
      <AccountFilter value={accountFilter} onChange={setAccountFilter} />

      {/* DORA Metrics */}
      <div className="grid grid-cols-2 gap-5 lg:grid-cols-4">
        {Object.entries(doraMetrics).map(([key, metric]) => (
          <Card key={key} className="border-border/50 bg-card p-6">
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm text-muted-foreground">
                {key.replace(/([A-Z])/g, " $1").trim()}
              </span>
              <Badge variant="outline" className={`font-mono text-xs ${ratingColors[metric.rating]}`}>
                {metric.rating}
              </Badge>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="font-mono text-3xl font-bold">{metric.value}</span>
              <span className="font-mono text-sm text-muted-foreground">{metric.unit}</span>
            </div>
            <span className={`font-mono text-sm ${metric.trend.startsWith("-") ? "text-[#00FF88]" : "text-amber-400"}`}>
              {metric.trend} vs last month
            </span>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="timeline">
        <TabsList className="bg-card">
          <TabsTrigger value="timeline" className="font-mono text-sm">Timeline</TabsTrigger>
          <TabsTrigger value="frequency" className="font-mono text-sm">Frequency</TabsTrigger>
          <TabsTrigger value="lead-time" className="font-mono text-sm">Lead Time</TabsTrigger>
        </TabsList>

        <TabsContent value="timeline" className="mt-4 space-y-3">
          {filteredDeployments.map((deploy) => (
            <div key={deploy.id} className="flex items-center gap-4 rounded border border-border/50 bg-card p-4">
              <div className="flex items-center gap-2">
                {deploy.status === "success" ? (
                  <CheckCircle2 className="h-5 w-5 text-green-400" />
                ) : deploy.status === "failed" ? (
                  <XCircle className="h-5 w-5 text-red-400" />
                ) : (
                  <AlertTriangle className="h-5 w-5 text-amber-400" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-base font-medium">{deploy.service}</span>
                  <Badge variant="outline" className="font-mono text-xs">{deploy.version}</Badge>
                  <Badge variant="outline" className={`font-mono text-xs ${statusColors[deploy.status]}`}>
                    {deploy.status}
                  </Badge>
                </div>
                <div className="mt-1.5 flex items-center gap-3 font-mono text-sm text-muted-foreground">
                  <span className="flex items-center gap-1"><GitBranch className="h-4 w-4" />{deploy.env}</span>
                  <span className="flex items-center gap-1"><Clock className="h-4 w-4" />{deploy.duration}</span>
                  <span>{deploy.author}</span>
                  <span>{new Date(deploy.timestamp).toLocaleDateString()}</span>
                </div>
              </div>
            </div>
          ))}
        </TabsContent>

        <TabsContent value="frequency" className="mt-4">
          <Card className="border-border/50 bg-card p-5">
            <h3 className="mb-4 font-mono text-lg font-medium">Deployments per Day</h3>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={deployFrequencyData}>
                <XAxis dataKey="date" tick={{ fill: "#666", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                <YAxis tick={{ fill: "#666", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                <Tooltip contentStyle={{ background: "#0D0D12", border: "1px solid #333", fontFamily: "JetBrains Mono", fontSize: 11 }} />
                <Bar dataKey="deploys" fill="#00FF88" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </TabsContent>

        <TabsContent value="lead-time" className="mt-4">
          <Card className="border-border/50 bg-card p-5">
            <h3 className="mb-4 font-mono text-lg font-medium">Lead Time for Changes (hours)</h3>
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={leadTimeData}>
                <XAxis dataKey="date" tick={{ fill: "#666", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                <YAxis tick={{ fill: "#666", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                <Tooltip contentStyle={{ background: "#0D0D12", border: "1px solid #333", fontFamily: "JetBrains Mono", fontSize: 11 }} />
                <Area type="monotone" dataKey="hours" stroke="#00BFFF" fill="#00BFFF" fillOpacity={0.1} />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
