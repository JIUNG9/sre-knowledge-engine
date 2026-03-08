"use client";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Phone, BookOpen, Calendar, Users, Clock, ArrowUpRight } from "lucide-react";

const currentOnCall = {
  primary: { name: "June Gu", team: "Platform", since: "2026-03-08T09:00:00Z", until: "2026-03-15T09:00:00Z" },
  secondary: { name: "SRE Bot", team: "Platform", since: "2026-03-08T09:00:00Z", until: "2026-03-15T09:00:00Z" },
};

const schedule = [
  { week: "Mar 1-7", primary: "Team Member A", secondary: "Team Member B" },
  { week: "Mar 8-14", primary: "June Gu", secondary: "SRE Bot" },
  { week: "Mar 15-21", primary: "Team Member C", secondary: "Team Member A" },
  { week: "Mar 22-28", primary: "Team Member B", secondary: "Team Member C" },
];

const runbooks = [
  { id: "rb-001", title: "Database Connection Pool Exhaustion", service: "payment-service", lastUsed: "2026-03-02", steps: 5, severity: "critical" },
  { id: "rb-002", title: "High Memory Usage Alert", service: "api-gateway", lastUsed: "2026-02-28", steps: 4, severity: "high" },
  { id: "rb-003", title: "Certificate Renewal Procedure", service: "infrastructure", lastUsed: "2026-02-15", steps: 6, severity: "medium" },
  { id: "rb-004", title: "Kafka Consumer Lag Remediation", service: "notification-service", lastUsed: "2026-02-20", steps: 7, severity: "high" },
  { id: "rb-005", title: "Redis Cluster Failover", service: "infrastructure", lastUsed: "2026-01-30", steps: 8, severity: "critical" },
  { id: "rb-006", title: "DNS Resolution Failure", service: "infrastructure", lastUsed: "2026-02-10", steps: 3, severity: "medium" },
];

const escalationPolicies = [
  { level: 1, target: "Primary On-Call", delay: "0 min", method: "Slack + PagerDuty" },
  { level: 2, target: "Secondary On-Call", delay: "5 min", method: "Slack + PagerDuty + Phone" },
  { level: 3, target: "Team Lead", delay: "15 min", method: "Phone + SMS" },
  { level: 4, target: "Engineering Manager", delay: "30 min", method: "Phone + SMS + Email" },
];

export default function OnCallPage() {
  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="font-mono text-2xl font-bold">On-Call & Runbooks</h1>
        <p className="mt-1 font-mono text-sm text-muted-foreground">
          Rotation schedules, escalation policies, runbook library
        </p>
      </div>

      {/* Current On-Call */}
      <div className="grid grid-cols-2 gap-4">
        <Card className="border-[#00FF88]/20 bg-[#0D0D12] p-4">
          <div className="flex items-center gap-2">
            <Phone className="h-4 w-4 text-[#00FF88]" />
            <span className="font-mono text-xs text-muted-foreground">Primary On-Call</span>
          </div>
          <p className="mt-2 font-mono text-lg font-bold">{currentOnCall.primary.name}</p>
          <p className="font-mono text-xs text-muted-foreground">
            {currentOnCall.primary.team} · Until {new Date(currentOnCall.primary.until).toLocaleDateString()}
          </p>
        </Card>
        <Card className="border-border/50 bg-[#0D0D12] p-4">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-cyan-400" />
            <span className="font-mono text-xs text-muted-foreground">Secondary On-Call</span>
          </div>
          <p className="mt-2 font-mono text-lg font-bold">{currentOnCall.secondary.name}</p>
          <p className="font-mono text-xs text-muted-foreground">
            {currentOnCall.secondary.team} · Until {new Date(currentOnCall.secondary.until).toLocaleDateString()}
          </p>
        </Card>
      </div>

      <Tabs defaultValue="runbooks">
        <TabsList className="bg-[#0D0D12]">
          <TabsTrigger value="runbooks" className="font-mono text-xs">Runbooks</TabsTrigger>
          <TabsTrigger value="schedule" className="font-mono text-xs">Schedule</TabsTrigger>
          <TabsTrigger value="escalation" className="font-mono text-xs">Escalation</TabsTrigger>
        </TabsList>

        <TabsContent value="runbooks" className="mt-4 space-y-2">
          {runbooks.map((rb) => (
            <div key={rb.id} className="flex items-center gap-3 rounded border border-border/50 bg-[#0D0D12] p-3 hover:border-[#00FF88]/30 cursor-pointer transition-colors">
              <BookOpen className="h-4 w-4 text-[#00FF88]" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-medium">{rb.title}</span>
                  <Badge variant="outline" className="font-mono text-[10px]">{rb.steps} steps</Badge>
                </div>
                <div className="mt-1 flex items-center gap-3 font-mono text-xs text-muted-foreground">
                  <span>{rb.service}</span>
                  <span>·</span>
                  <span>Last used: {rb.lastUsed}</span>
                </div>
              </div>
              <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
            </div>
          ))}
        </TabsContent>

        <TabsContent value="schedule" className="mt-4">
          <div className="space-y-2">
            {schedule.map((week, i) => (
              <div key={i} className={`flex items-center gap-3 rounded border p-3 ${week.primary === "June Gu" ? "border-[#00FF88]/30 bg-[#00FF88]/5" : "border-border/50 bg-[#0D0D12]"}`}>
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="w-24 font-mono text-sm">{week.week}</span>
                <div className="flex-1 flex items-center gap-4 font-mono text-sm">
                  <span><span className="text-xs text-muted-foreground">Primary:</span> {week.primary}</span>
                  <span><span className="text-xs text-muted-foreground">Secondary:</span> {week.secondary}</span>
                </div>
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="escalation" className="mt-4">
          <div className="space-y-2">
            {escalationPolicies.map((policy) => (
              <div key={policy.level} className="flex items-center gap-3 rounded border border-border/50 bg-[#0D0D12] p-3">
                <Badge variant="outline" className="font-mono text-xs">L{policy.level}</Badge>
                <div className="flex-1">
                  <span className="font-mono text-sm font-medium">{policy.target}</span>
                  <div className="mt-1 flex items-center gap-3 font-mono text-xs text-muted-foreground">
                    <span className="flex items-center gap-1"><Clock className="h-3 w-3" />After {policy.delay}</span>
                    <span>·</span>
                    <span>{policy.method}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
