"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MemberManager } from "@/components/oncall/member-manager";
import { TaskAssignment } from "@/components/oncall/task-assignment";
import { AIRecommendations } from "@/components/oncall/ai-recommendations";
import {
  Phone,
  BookOpen,
  Calendar,
  Users,
  Clock,
  ArrowUpRight,
} from "lucide-react";
import {
  CURRENT_ON_CALL,
  SCHEDULE,
  RUNBOOKS,
  ESCALATION_POLICIES,
  TEAM_MEMBERS,
  TASKS,
  AI_RECOMMENDATIONS,
} from "@/lib/mock-data/oncall";
import type { TeamMember, OnCallTask } from "@/lib/mock-data/oncall";

export default function OnCallPage() {
  const [members, setMembers] = useState<TeamMember[]>(TEAM_MEMBERS);
  const [tasks, setTasks] = useState<OnCallTask[]>(TASKS);

  function handleApplyRecommendation(id: string) {
    // Mock: just show the recommendation was applied
    console.log(`Applied recommendation: ${id}`);
  }

  return (
    <div className="space-y-6 p-8">
      <div>
        <h1 className="font-mono text-2xl font-bold">On-Call & Runbooks</h1>
        <p className="mt-1 font-mono text-sm text-muted-foreground">
          Rotation schedules, escalation policies, runbook library
        </p>
      </div>

      {/* Current On-Call */}
      <div className="grid grid-cols-2 gap-5">
        <Card className="border-[#00FF88]/20 bg-card p-6">
          <div className="flex items-center gap-2">
            <Phone className="h-5 w-5 text-[#00FF88]" />
            <span className="font-mono text-sm text-muted-foreground">
              Primary On-Call
            </span>
          </div>
          <p className="mt-3 font-mono text-2xl font-bold">
            {CURRENT_ON_CALL.primary.name}
          </p>
          <p className="mt-1 font-mono text-sm text-muted-foreground">
            {CURRENT_ON_CALL.primary.team} &middot; Until{" "}
            {new Date(CURRENT_ON_CALL.primary.until).toLocaleDateString()}
          </p>
        </Card>
        <Card className="border-border/50 bg-card p-6">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-cyan-400" />
            <span className="font-mono text-sm text-muted-foreground">
              Secondary On-Call
            </span>
          </div>
          <p className="mt-3 font-mono text-2xl font-bold">
            {CURRENT_ON_CALL.secondary.name}
          </p>
          <p className="mt-1 font-mono text-sm text-muted-foreground">
            {CURRENT_ON_CALL.secondary.team} &middot; Until{" "}
            {new Date(CURRENT_ON_CALL.secondary.until).toLocaleDateString()}
          </p>
        </Card>
      </div>

      <Tabs defaultValue="schedule">
        <TabsList className="bg-card">
          <TabsTrigger value="schedule" className="font-mono text-sm">
            Schedule
          </TabsTrigger>
          <TabsTrigger value="runbooks" className="font-mono text-sm">
            Runbooks
          </TabsTrigger>
          <TabsTrigger value="team" className="font-mono text-sm">
            Team
          </TabsTrigger>
          <TabsTrigger value="tasks" className="font-mono text-sm">
            Tasks
          </TabsTrigger>
          <TabsTrigger value="ai" className="font-mono text-sm">
            AI
          </TabsTrigger>
        </TabsList>

        {/* Schedule tab */}
        <TabsContent value="schedule" className="mt-4">
          <div className="space-y-3">
            {SCHEDULE.map((week, i) => (
              <div
                key={i}
                className={`flex items-center gap-4 rounded border p-4 ${week.primary === "June Gu" ? "border-[#00FF88]/30 bg-[#00FF88]/5" : "border-border/50 bg-card"}`}
              >
                <Calendar className="h-5 w-5 text-muted-foreground" />
                <span className="w-28 font-mono text-base">{week.week}</span>
                <div className="flex flex-1 items-center gap-4 font-mono text-base">
                  <span>
                    <span className="text-sm text-muted-foreground">
                      Primary:
                    </span>{" "}
                    {week.primary}
                  </span>
                  <span>
                    <span className="text-sm text-muted-foreground">
                      Secondary:
                    </span>{" "}
                    {week.secondary}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Escalation policies */}
          <h3 className="mt-6 font-mono text-lg font-medium">
            Escalation Policy
          </h3>
          <div className="mt-3 space-y-3">
            {ESCALATION_POLICIES.map((policy) => (
              <div
                key={policy.level}
                className="flex items-center gap-4 rounded border border-border/50 bg-card p-4"
              >
                <Badge variant="outline" className="font-mono text-sm">
                  L{policy.level}
                </Badge>
                <div className="flex-1">
                  <span className="font-mono text-base font-medium">
                    {policy.target}
                  </span>
                  <div className="mt-1.5 flex items-center gap-3 font-mono text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      After {policy.delay}
                    </span>
                    <span>&middot;</span>
                    <span>{policy.method}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </TabsContent>

        {/* Runbooks tab */}
        <TabsContent value="runbooks" className="mt-4 space-y-3">
          {RUNBOOKS.map((rb) => (
            <div
              key={rb.id}
              className="flex cursor-pointer items-center gap-4 rounded border border-border/50 bg-card p-4 transition-colors hover:border-[#00FF88]/30"
            >
              <BookOpen className="h-5 w-5 text-[#00FF88]" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-base font-medium">
                    {rb.title}
                  </span>
                  <Badge variant="outline" className="font-mono text-xs">
                    {rb.steps} steps
                  </Badge>
                </div>
                <div className="mt-1.5 flex items-center gap-3 font-mono text-sm text-muted-foreground">
                  <span>{rb.service}</span>
                  <span>&middot;</span>
                  <span>Last used: {rb.lastUsed}</span>
                </div>
              </div>
              <ArrowUpRight className="h-5 w-5 text-muted-foreground" />
            </div>
          ))}
        </TabsContent>

        {/* Team tab */}
        <TabsContent value="team" className="mt-4">
          <MemberManager members={members} onChange={setMembers} />
        </TabsContent>

        {/* Tasks tab */}
        <TabsContent value="tasks" className="mt-4">
          <TaskAssignment
            tasks={tasks}
            members={members}
            onChange={setTasks}
          />
        </TabsContent>

        {/* AI tab */}
        <TabsContent value="ai" className="mt-4">
          <AIRecommendations
            recommendations={AI_RECOMMENDATIONS}
            onApply={handleApplyRecommendation}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
