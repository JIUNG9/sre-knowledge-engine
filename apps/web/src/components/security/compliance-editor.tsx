"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Plus, Trash2, FileDown } from "lucide-react";
import type { ComplianceCheck } from "@/lib/mock-data/security";
import { CIS_TEMPLATE, SOC2_TEMPLATE } from "@/lib/mock-data/security";

interface ComplianceEditorProps {
  checks: ComplianceCheck[];
  onChange: (checks: ComplianceCheck[]) => void;
}

const STATUS_CYCLE: ComplianceCheck["status"][] = ["pass", "fail", "warn"];

const statusDot: Record<string, string> = {
  pass: "bg-green-400",
  fail: "bg-red-400",
  warn: "bg-amber-400",
};

const statusText: Record<string, string> = {
  pass: "text-green-400",
  fail: "text-red-400",
  warn: "text-amber-400",
};

let nextId = 100;

export function ComplianceEditor({ checks, onChange }: ComplianceEditorProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCategory, setNewCategory] = useState("CIS");

  const passCount = checks.filter((c) => c.status === "pass").length;
  const complianceScore =
    checks.length > 0 ? Math.round((passCount / checks.length) * 100) : 0;

  function cycleStatus(id: string) {
    onChange(
      checks.map((c) => {
        if (c.id !== id) return c;
        const idx = STATUS_CYCLE.indexOf(c.status);
        return { ...c, status: STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length] };
      })
    );
  }

  function updateName(id: string, name: string) {
    onChange(checks.map((c) => (c.id === id ? { ...c, name } : c)));
  }

  function updateNotes(id: string, notes: string) {
    onChange(checks.map((c) => (c.id === id ? { ...c, notes } : c)));
  }

  function removeCheck(id: string) {
    onChange(checks.filter((c) => c.id !== id));
  }

  function addCheck() {
    if (!newName.trim()) return;
    onChange([
      ...checks,
      {
        id: `cc-${++nextId}`,
        name: newName.trim(),
        status: "warn",
        category: newCategory,
        notes: "",
      },
    ]);
    setNewName("");
    setNewCategory("CIS");
    setShowAddForm(false);
  }

  function loadTemplate(template: Omit<ComplianceCheck, "id">[]) {
    const newChecks = template.map((t) => ({
      ...t,
      id: `cc-${++nextId}`,
    }));
    onChange(newChecks);
  }

  return (
    <div className="space-y-4">
      {/* Score bar */}
      <div className="mb-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="font-mono text-base">Overall Compliance Score</span>
          <span className="font-mono text-base font-bold text-[#00FF88]">
            {complianceScore}%
          </span>
        </div>
        <Progress value={complianceScore} className="h-3" />
      </div>

      {/* Template buttons */}
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => loadTemplate(CIS_TEMPLATE)}
        >
          <FileDown data-icon="inline-start" />
          Load CIS Template
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => loadTemplate(SOC2_TEMPLATE)}
        >
          <FileDown data-icon="inline-start" />
          Load SOC2 Template
        </Button>
        <div className="flex-1" />
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowAddForm(!showAddForm)}
        >
          <Plus data-icon="inline-start" />
          Add Check
        </Button>
      </div>

      {/* Add form */}
      {showAddForm && (
        <Card className="border-[#00FF88]/20 bg-card p-4">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="font-mono text-sm text-muted-foreground">
                Check Name
              </label>
              <Input
                className="mt-1 font-mono text-sm"
                placeholder="e.g. Pod security standards enforced"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addCheck()}
              />
            </div>
            <div className="w-32">
              <label className="font-mono text-sm text-muted-foreground">
                Category
              </label>
              <Input
                className="mt-1 font-mono text-sm"
                placeholder="CIS"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
              />
            </div>
            <Button size="sm" onClick={addCheck} disabled={!newName.trim()}>
              Add
            </Button>
          </div>
        </Card>
      )}

      {/* Check list */}
      <div className="space-y-3">
        {checks.map((check) => (
          <div
            key={check.id}
            className="flex items-center gap-4 rounded border border-border/50 bg-card p-4"
          >
            {/* Status toggle */}
            <button
              type="button"
              onClick={() => cycleStatus(check.id)}
              className="group flex-shrink-0"
              title="Click to cycle status"
            >
              <div
                className={`h-3 w-3 rounded-full transition-colors ${statusDot[check.status]} group-hover:ring-2 group-hover:ring-white/20`}
              />
            </button>

            {/* Editable name */}
            <Input
              className="flex-1 border-none bg-transparent font-mono text-sm shadow-none focus-visible:ring-0"
              value={check.name}
              onChange={(e) => updateName(check.id, e.target.value)}
            />

            {/* Category badge */}
            <Badge variant="outline" className="font-mono text-xs">
              {check.category}
            </Badge>

            {/* Notes */}
            <Input
              className="w-48 border-none bg-transparent font-mono text-xs text-muted-foreground shadow-none placeholder:text-muted-foreground/50 focus-visible:ring-0"
              placeholder="Add notes..."
              value={check.notes}
              onChange={(e) => updateNotes(check.id, e.target.value)}
            />

            {/* Status label */}
            <span
              className={`w-10 text-right font-mono text-xs ${statusText[check.status]}`}
            >
              {check.status.toUpperCase()}
            </span>

            {/* Remove */}
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => removeCheck(check.id)}
            >
              <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
