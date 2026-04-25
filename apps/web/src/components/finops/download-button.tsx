"use client"

// DownloadButton — P2.3 FinOps CSV / Excel export trigger.
//
// Small dropdown that kicks off a browser download against the Go API's
// /api/v1/finops/export/* endpoints. The current UI filters (date range,
// account, group_by, etc.) are passed through as query params so the
// exported spreadsheet matches what the user is looking at.
//
// Toasts aren't available in this app yet, so errors surface through an
// inline badge that auto-clears after a few seconds.

import * as React from "react"
import { Download, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"

// API base — override via NEXT_PUBLIC_API_URL when the Go API lives on a
// different host. Defaults to local Fiber dev port.
const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8080"

export type ExportView = "costs" | "budgets" | "anomalies" | "k8s"
export type ExportFormat = "csv" | "xlsx"

export interface DownloadButtonProps {
  /** Which FinOps export endpoint to hit. */
  view: ExportView
  /**
   * Additional query params to pass through (account, start, end, group_by,
   * lookback, aggregate, window, ...). `undefined`/empty-string values are
   * skipped so we don't send blank filters.
   */
  params?: Record<string, string | number | null | undefined>
  /** Optional label override. */
  label?: string
  /** Visual variant to match surrounding controls. */
  variant?: "outline" | "ghost"
  /** Size to match surrounding controls. */
  size?: "xs" | "sm"
  /** Extra classes to stick on the trigger button. */
  className?: string
}

/**
 * Build the export URL with current filters. Exported for tests and so card
 * headers can show the effective endpoint in dev tools.
 */
export function buildExportUrl(
  view: ExportView,
  format: ExportFormat,
  params: DownloadButtonProps["params"] = {}
): string {
  const url = new URL(`${API_BASE}/api/v1/finops/export/${view}`)
  url.searchParams.set("format", format)
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null) continue
    const s = String(v).trim()
    if (s === "") continue
    url.searchParams.set(k, s)
  }
  return url.toString()
}

export function DownloadButton({
  view,
  params,
  label = "Download",
  variant = "outline",
  size = "sm",
  className,
}: DownloadButtonProps) {
  const [state, setState] = React.useState<"idle" | "loading" | "error">(
    "idle"
  )
  const [errorMsg, setErrorMsg] = React.useState<string>("")

  // Clear the error badge after 4s so it doesn't linger.
  React.useEffect(() => {
    if (state !== "error") return
    const t = window.setTimeout(() => {
      setState("idle")
      setErrorMsg("")
    }, 4000)
    return () => window.clearTimeout(t)
  }, [state])

  const triggerDownload = React.useCallback(
    async (format: ExportFormat) => {
      const url = buildExportUrl(view, format, params)
      setState("loading")
      try {
        const res = await fetch(url, {
          method: "GET",
          credentials: "include",
        })
        if (!res.ok) {
          const text = await res.text().catch(() => "")
          throw new Error(
            `Export failed (${res.status}) ${text ? `— ${text.slice(0, 160)}` : ""}`
          )
        }
        // Prefer the server-provided filename when present.
        const cd = res.headers.get("Content-Disposition") ?? ""
        const match = cd.match(/filename="?([^";]+)"?/i)
        const fallback = `aegis-finops-${view}-${new Date()
          .toISOString()
          .slice(0, 10)}.${format}`
        const filename = match?.[1] ?? fallback

        const blob = await res.blob()
        const href = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = href
        a.download = filename
        document.body.appendChild(a)
        a.click()
        a.remove()
        // Free the blob URL on the next tick so Safari has time to start
        // the download.
        window.setTimeout(() => URL.revokeObjectURL(href), 1000)
        setState("idle")
      } catch (err) {
        setState("error")
        setErrorMsg(
          err instanceof Error ? err.message : "Unknown download error"
        )
      }
    },
    [view, params]
  )

  return (
    <div className="flex items-center gap-2">
      {state === "error" && (
        <span
          role="status"
          className="font-mono text-[10px] text-[#FF4444]"
          title={errorMsg}
        >
          Export failed
        </span>
      )}
      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button
              variant={variant}
              size={size}
              className={cn("gap-1.5 font-mono text-xs", className)}
              disabled={state === "loading"}
              aria-label="Download data"
            >
              {state === "loading" ? (
                <Loader2 className="size-3 animate-spin" />
              ) : (
                <Download className="size-3" />
              )}
              {label}
            </Button>
          }
        />
        <DropdownMenuContent align="end" className="w-40">
          <DropdownMenuItem
            onClick={() => {
              void triggerDownload("csv")
            }}
            className="font-mono text-xs"
          >
            <Download className="size-3" />
            CSV (.csv)
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => {
              void triggerDownload("xlsx")
            }}
            className="font-mono text-xs"
          >
            <Download className="size-3" />
            Excel (.xlsx)
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
