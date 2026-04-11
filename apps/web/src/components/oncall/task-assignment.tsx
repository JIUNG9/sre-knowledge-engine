"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Filter } from "lucide-react";
import type {
  OnCallTask,
  TaskPriority,
  TaskStatus,
  TeamMember,
} from "@/lib/mock-data/oncall";
import { getMemberName } from "@/lib/mock-data/oncall";

interface TaskAssignmentProps {
  tasks: OnCallTask[];
  members: TeamMember[];
  onChange: (tasks: OnCallTask[]) => void;
}

const PRIORITIES: TaskPriority[] = ["P0", "P1", "P2", "P3"];
const STATUSES: TaskStatus[] = ["open", "in-progress", "done"];

const priorityColor: Record<TaskPriority, string> = {
  P0: "text-red-400 bg-red-400/10 border-red-400/30",
  P1: "text-orange-400 bg-orange-400/10 border-orange-400/30",
  P2: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  P3: "text-blue-400 bg-blue-400/10 border-blue-400/30",
};

const statusColor: Record<TaskStatus, string> = {
  open: "text-amber-400",
  "in-progress": "text-cyan-400",
  done: "text-[#00FF88]",
};

let nextTaskId = 100;

export function TaskAssignment({
  tasks,
  members,
  onChange,
}: TaskAssignmentProps) {
  const [filterAssignee, setFilterAssignee] = useState("all");
  const [filterPriority, setFilterPriority] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");

  function handleFilterAssignee(val: string | null) {
    setFilterAssignee(val ?? "all");
  }
  function handleFilterPriority(val: string | null) {
    setFilterPriority(val ?? "all");
  }
  function handleFilterStatus(val: string | null) {
    setFilterStatus(val ?? "all");
  }
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newAssignee, setNewAssignee] = useState("");
  const [newPriority, setNewPriority] = useState<TaskPriority>("P2");

  const filtered = tasks.filter((t) => {
    if (filterAssignee !== "all" && t.assignee !== filterAssignee) return false;
    if (filterPriority !== "all" && t.priority !== filterPriority) return false;
    if (filterStatus !== "all" && t.status !== filterStatus) return false;
    return true;
  });

  function updateAssignee(taskId: string, assignee: string) {
    onChange(tasks.map((t) => (t.id === taskId ? { ...t, assignee } : t)));
  }

  function updateStatus(taskId: string, status: TaskStatus) {
    onChange(tasks.map((t) => (t.id === taskId ? { ...t, status } : t)));
  }

  function addTask() {
    if (!newTitle.trim() || !newAssignee) return;
    onChange([
      ...tasks,
      {
        id: `task-${++nextTaskId}`,
        title: newTitle.trim(),
        assignee: newAssignee,
        priority: newPriority,
        status: "open",
        createdAt: new Date().toISOString(),
      },
    ]);
    setNewTitle("");
    setNewAssignee("");
    setNewPriority("P2");
    setShowAddForm(false);
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <Select value={filterAssignee} onValueChange={handleFilterAssignee}>
          <SelectTrigger className="w-40 font-mono text-sm">
            <SelectValue placeholder="Assignee" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Assignees</SelectItem>
            {members.map((m) => (
              <SelectItem key={m.id} value={m.id}>
                {m.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={filterPriority} onValueChange={handleFilterPriority}>
          <SelectTrigger className="w-28 font-mono text-sm">
            <SelectValue placeholder="Priority" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            {PRIORITIES.map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={filterStatus} onValueChange={handleFilterStatus}>
          <SelectTrigger className="w-36 font-mono text-sm">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            {STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="flex-1" />
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowAddForm(!showAddForm)}
        >
          <Plus data-icon="inline-start" />
          Add Task
        </Button>
      </div>

      {/* Add form */}
      {showAddForm && (
        <Card className="border-[#00FF88]/20 bg-card p-4">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="font-mono text-sm text-muted-foreground">
                Title
              </label>
              <Input
                className="mt-1 font-mono text-sm"
                placeholder="Task title..."
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addTask()}
              />
            </div>
            <div className="w-40">
              <label className="font-mono text-sm text-muted-foreground">
                Assignee
              </label>
              <Select value={newAssignee} onValueChange={(v: string | null) => { if (v) setNewAssignee(v) }}>
                <SelectTrigger className="mt-1 font-mono text-sm">
                  <SelectValue placeholder="Select..." />
                </SelectTrigger>
                <SelectContent>
                  {members.map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-24">
              <label className="font-mono text-sm text-muted-foreground">
                Priority
              </label>
              <Select
                value={newPriority}
                onValueChange={(val) => { if (val) setNewPriority(val as TaskPriority) }}
              >
                <SelectTrigger className="mt-1 font-mono text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PRIORITIES.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              size="sm"
              onClick={addTask}
              disabled={!newTitle.trim() || !newAssignee}
            >
              Add
            </Button>
          </div>
        </Card>
      )}

      {/* Task list */}
      <div className="space-y-3">
        {filtered.map((task) => (
          <div
            key={task.id}
            className="flex items-center gap-4 rounded border border-border/50 bg-card p-4"
          >
            {/* Priority */}
            <Badge
              variant="outline"
              className={`font-mono text-xs ${priorityColor[task.priority]}`}
            >
              {task.priority}
            </Badge>

            {/* Title + linked items */}
            <div className="flex-1 min-w-0">
              <p className="truncate font-mono text-sm font-medium">
                {task.title}
              </p>
              <div className="mt-1.5 flex items-center gap-2">
                {task.linkedIncident && (
                  <Badge
                    variant="outline"
                    className="font-mono text-xs text-red-400 border-red-400/30 bg-red-400/10"
                  >
                    {task.linkedIncident}
                  </Badge>
                )}
                {task.linkedRunbook && (
                  <Badge
                    variant="outline"
                    className="font-mono text-xs text-cyan-400 border-cyan-400/30 bg-cyan-400/10"
                  >
                    {task.linkedRunbook.toUpperCase()}
                  </Badge>
                )}
              </div>
            </div>

            {/* Assignee dropdown */}
            <Select
              value={task.assignee}
              onValueChange={(val) => { if (val) updateAssignee(task.id, val) }}
            >
              <SelectTrigger className="w-36 font-mono text-xs">
                <SelectValue>
                  {getMemberName(task.assignee)}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {members.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Status dropdown */}
            <Select
              value={task.status}
              onValueChange={(val) => {
                if (val) updateStatus(task.id, val as TaskStatus)
              }}
            >
              <SelectTrigger className="w-32 font-mono text-xs">
                <SelectValue>
                  <span className={statusColor[task.status]}>
                    {task.status}
                  </span>
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="rounded border border-dashed border-border/50 p-8 text-center">
            <p className="font-mono text-sm text-muted-foreground">
              No tasks match the current filters.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
