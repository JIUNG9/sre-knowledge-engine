"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Sparkles, ArrowRight, BarChart3, RefreshCw } from "lucide-react";
import type { AIRecommendation } from "@/lib/mock-data/oncall";

interface AIRecommendationsProps {
  recommendations: AIRecommendation[];
  onApply: (id: string) => void;
}

const typeConfig: Record<
  string,
  { icon: typeof Sparkles; color: string; label: string }
> = {
  assignment: {
    icon: ArrowRight,
    color: "text-[#00FF88]",
    label: "Assignment",
  },
  redistribution: {
    icon: BarChart3,
    color: "text-amber-400",
    label: "Redistribution",
  },
  handoff: {
    icon: RefreshCw,
    color: "text-cyan-400",
    label: "Handoff",
  },
};

export function AIRecommendations({
  recommendations,
  onApply,
}: AIRecommendationsProps) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-[#00FF88]" />
        <h3 className="font-mono text-lg font-medium">AI Recommendations</h3>
        <Badge
          variant="outline"
          className="font-mono text-xs text-[#00FF88] border-[#00FF88]/30"
        >
          {recommendations.length} suggestions
        </Badge>
      </div>
      <p className="font-mono text-sm text-muted-foreground">
        Generated from incident history, workload patterns, and team expertise
      </p>

      {/* Recommendation cards */}
      <div className="space-y-4">
        {recommendations.map((rec) => {
          const cfg = typeConfig[rec.type];
          const TypeIcon = cfg.icon;

          return (
            <Card key={rec.id} className="border-border/50 bg-card p-5">
              <div className="flex items-start gap-4">
                <div
                  className={`mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-muted ${cfg.color}`}
                >
                  <TypeIcon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={`font-mono text-xs ${cfg.color}`}
                    >
                      {cfg.label}
                    </Badge>
                    <span className="font-mono text-xs text-muted-foreground">
                      {rec.confidence}% confidence
                    </span>
                  </div>
                  <p className="mt-2 font-mono text-sm leading-relaxed">
                    {rec.description}
                  </p>

                  {/* Confidence bar */}
                  <div className="mt-3 flex items-center gap-2">
                    <div className="h-1.5 flex-1 rounded-full bg-muted">
                      <div
                        className={`h-full rounded-full ${rec.confidence >= 80 ? "bg-[#00FF88]" : rec.confidence >= 60 ? "bg-amber-400" : "bg-red-400"}`}
                        style={{ width: `${rec.confidence}%` }}
                      />
                    </div>
                    <Button
                      variant="outline"
                      size="xs"
                      onClick={() => onApply(rec.id)}
                    >
                      Apply
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}

        {recommendations.length === 0 && (
          <div className="rounded border border-dashed border-border/50 p-8 text-center">
            <Sparkles className="mx-auto h-8 w-8 text-muted-foreground" />
            <p className="mt-2 font-mono text-sm text-muted-foreground">
              No recommendations available. The AI engine needs more incident
              data to generate suggestions.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
