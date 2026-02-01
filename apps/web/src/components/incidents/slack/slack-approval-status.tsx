"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  MessageSquare,
  CheckCircle2,
  XCircle,
  Clock,
  Send,
} from "lucide-react";

interface ApprovalStep {
  id: string;
  description: string;
  command: string;
  riskLevel: "low" | "medium" | "high";
  status: "pending" | "approved" | "rejected";
  approvedBy?: string;
  approvedAt?: string;
}

interface SlackApprovalStatusProps {
  incidentId: string;
  steps: ApprovalStep[];
  slackChannel: string;
  onResend?: () => void;
}

const riskColors = {
  low: "text-green-400 border-green-400/30 bg-green-400/10",
  medium: "text-amber-400 border-amber-400/30 bg-amber-400/10",
  high: "text-red-400 border-red-400/30 bg-red-400/10",
};

const statusIcons = {
  pending: <Clock className="h-4 w-4 text-muted-foreground animate-pulse" />,
  approved: <CheckCircle2 className="h-4 w-4 text-green-400" />,
  rejected: <XCircle className="h-4 w-4 text-red-400" />,
};

export function SlackApprovalStatus({
  incidentId,
  steps,
  slackChannel,
  onResend,
}: SlackApprovalStatusProps) {
  const approvedCount = steps.filter((s) => s.status === "approved").length;
  const rejectedCount = steps.filter((s) => s.status === "rejected").length;
  const pendingCount = steps.filter((s) => s.status === "pending").length;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-[#00FF88]" />
          <span className="font-mono text-sm font-medium">
            Slack Approval — #{slackChannel}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="text-green-400">{approvedCount} approved</span>
          <span>·</span>
          <span className="text-red-400">{rejectedCount} rejected</span>
          <span>·</span>
          <span>{pendingCount} pending</span>
        </div>
      </div>

      <div className="space-y-2">
        {steps.map((step) => (
          <div
            key={step.id}
            className="flex items-center gap-3 rounded border border-border/50 bg-[#0D0D12] p-3 font-mono text-xs"
          >
            {statusIcons[step.status]}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate">{step.description}</span>
                <Badge
                  variant="outline"
                  className={`text-[10px] ${riskColors[step.riskLevel]}`}
                >
                  {step.riskLevel}
                </Badge>
              </div>
              <code className="mt-1 block truncate text-muted-foreground">
                {step.command}
              </code>
            </div>
            <div className="text-right text-muted-foreground">
              {step.status === "approved" && step.approvedBy && (
                <span>by {step.approvedBy}</span>
              )}
              {step.status === "pending" && (
                <span className="animate-pulse">awaiting...</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {pendingCount > 0 && (
        <Button
          variant="outline"
          size="sm"
          className="w-full font-mono text-xs"
          onClick={onResend}
        >
          <Send className="mr-2 h-3 w-3" />
          Resend to #{slackChannel}
        </Button>
      )}
    </div>
  );
}
