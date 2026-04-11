"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  Vulnerability,
  VulnerabilitySeverity,
  SeverityOverride,
} from "@/lib/mock-data/security";
import { SEVERITY_COLORS } from "@/lib/mock-data/security";

interface SeverityOverrideDialogProps {
  vulnerability: Vulnerability | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (override: Omit<SeverityOverride, "id" | "createdAt">) => void;
}

const SEVERITY_OPTIONS: VulnerabilitySeverity[] = [
  "critical",
  "high",
  "medium",
  "low",
];

export function SeverityOverrideDialog({
  vulnerability,
  open,
  onOpenChange,
  onSave,
}: SeverityOverrideDialogProps) {
  const [newSeverity, setNewSeverity] =
    useState<VulnerabilitySeverity>("medium");
  const [justification, setJustification] = useState("");
  const [expiryDate, setExpiryDate] = useState("");

  function handleSave() {
    if (!vulnerability || !justification.trim()) return;
    onSave({
      cveId: vulnerability.id,
      originalSeverity: vulnerability.severity,
      newSeverity,
      justification: justification.trim(),
      expiryDate: expiryDate || undefined,
    });
    setJustification("");
    setExpiryDate("");
    onOpenChange(false);
  }

  if (!vulnerability) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-mono">
            Override Severity
          </DialogTitle>
          <DialogDescription>
            Override the severity classification for{" "}
            <span className="font-mono font-medium text-foreground">
              {vulnerability.id}
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* CVE Info */}
          <div className="rounded border border-border/50 bg-muted/30 p-3">
            <p className="font-mono text-sm font-medium">
              {vulnerability.title}
            </p>
            <p className="mt-1 font-mono text-sm text-muted-foreground">
              {vulnerability.package}@{vulnerability.version}
            </p>
          </div>

          {/* Current vs New severity */}
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <Label className="font-mono text-sm text-muted-foreground">
                Current
              </Label>
              <div className="mt-1.5">
                <Badge
                  variant="outline"
                  className={`font-mono text-xs line-through ${SEVERITY_COLORS[vulnerability.severity]}`}
                >
                  {vulnerability.severity.toUpperCase()}
                </Badge>
              </div>
            </div>
            <span className="mt-5 font-mono text-muted-foreground">-&gt;</span>
            <div className="flex-1">
              <Label className="font-mono text-sm text-muted-foreground">
                New
              </Label>
              <div className="mt-1.5">
                <Select
                  value={newSeverity}
                  onValueChange={(val) => {
                    if (val) setNewSeverity(val as VulnerabilitySeverity)
                  }}
                >
                  <SelectTrigger className="font-mono text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SEVERITY_OPTIONS.filter(
                      (s) => s !== vulnerability.severity
                    ).map((s) => (
                      <SelectItem key={s} value={s}>
                        <span
                          className={`font-mono ${SEVERITY_COLORS[s].split(" ")[0]}`}
                        >
                          {s.toUpperCase()}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Justification */}
          <div>
            <Label className="font-mono text-sm">Justification</Label>
            <Textarea
              className="mt-1.5 font-mono text-sm"
              placeholder="Explain why the severity should be changed..."
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              rows={3}
            />
          </div>

          {/* Expiry date */}
          <div>
            <Label className="font-mono text-sm">
              Expiry Date{" "}
              <span className="text-muted-foreground">(optional)</span>
            </Label>
            <Input
              type="date"
              className="mt-1.5 font-mono text-sm"
              value={expiryDate}
              onChange={(e) => setExpiryDate(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <DialogClose render={<Button variant="outline" />}>
            Cancel
          </DialogClose>
          <Button
            onClick={handleSave}
            disabled={!justification.trim()}
          >
            Save Override
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
