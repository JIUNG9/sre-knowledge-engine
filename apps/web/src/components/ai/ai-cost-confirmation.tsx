"use client"

import * as React from "react"
import { AlertTriangle } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { useAIStore } from "@/lib/stores/ai-store"

interface AICostConfirmationProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  estimatedTokens: number
  estimatedCost: number
  onProceed: () => void
  onCancel: () => void
}

export function AICostConfirmation({
  open,
  onOpenChange,
  estimatedTokens,
  estimatedCost,
  onProceed,
  onCancel,
}: AICostConfirmationProps) {
  const [skipUnderThreshold, setSkipUnderThreshold] = React.useState(false)
  const { sessionCost, budget } = useAIStore()

  const formatTokens = (tokens: number): string => {
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`
    return tokens.toString()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="size-4 text-amber-400" />
            Confirm AI Operation
          </DialogTitle>
          <DialogDescription>
            Review the estimated cost before proceeding.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Estimate */}
          <div className="rounded-lg bg-muted/50 p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Estimated tokens</span>
              <span className="font-mono font-medium text-foreground">
                ~{formatTokens(estimatedTokens)}
              </span>
            </div>
            <div className="mt-1.5 flex items-center justify-between">
              <span className="text-muted-foreground">Estimated cost</span>
              <span className="font-mono font-medium text-primary">
                ~${estimatedCost.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Session budget */}
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Session total</span>
            <span className="font-mono">
              ${sessionCost.toFixed(2)} of ${budget.toFixed(2)} budget
            </span>
          </div>

          {/* Budget bar */}
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary/70 transition-all"
              style={{ width: `${Math.min((sessionCost / budget) * 100, 100)}%` }}
            />
          </div>

          {/* Threshold checkbox */}
          <label className="flex items-center gap-2.5 cursor-pointer">
            <Checkbox
              checked={skipUnderThreshold}
              onCheckedChange={(checked) =>
                setSkipUnderThreshold(checked === true)
              }
            />
            <span className="text-[13px] text-muted-foreground">
              Don&apos;t ask for operations under $0.10
            </span>
          </label>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={onProceed}>Proceed</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
