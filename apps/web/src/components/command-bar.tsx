"use client"

import * as React from "react"
import { usePathname } from "next/navigation"
import { Shield, User, Search, Bell } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { LanguageSwitcher } from "@/components/language-switcher"

const pageTitles: Record<string, string> = {
  "/logs": "Log Explorer",
  "/slo": "SLO Dashboard",
  "/finops": "FinOps",
  "/incidents": "Incidents",
  "/security": "Security",
  "/iam": "IAM Audit",
  "/deployments": "Deployments",
  "/oncall": "On-Call",
  "/services": "Service Catalog",
  "/settings": "Settings",
  "/accounts": "Account Management",
}

export function CommandBar() {
  const pathname = usePathname()

  const pageTitle = pageTitles[pathname] || "Dashboard"

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-sm">
      {/* Left: Mobile logo + Page title */}
      <div className="flex items-center gap-4">
        {/* Mobile logo (hidden on md+) */}
        <div className="flex items-center gap-2 md:hidden">
          <div className="flex size-7 items-center justify-center rounded-md bg-primary/10">
            <Shield className="size-4 text-primary" />
          </div>
          <span className="font-heading text-sm font-semibold tracking-wider text-foreground">
            AEGIS
          </span>
        </div>

        {/* Page title */}
        <h1 className="hidden text-[22px] font-bold text-foreground md:block">
          {pageTitle}
        </h1>
      </div>

      {/* Right: Search + Language + Notifications + User — BIGGER with spacing */}
      <div className="flex items-center gap-4">
        {/* Search trigger */}
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon"
                className="size-10 text-muted-foreground hover:text-foreground"
              />
            }
          >
            <Search className="size-5" />
            <span className="sr-only">Search</span>
          </TooltipTrigger>
          <TooltipContent>
            Search
            <kbd className="ml-1.5 rounded border border-border bg-muted px-1.5 font-mono text-xs">
              &#8984;K
            </kbd>
          </TooltipContent>
        </Tooltip>

        <div className="h-6 w-px bg-border" />

        {/* Language Switcher */}
        <LanguageSwitcher />

        <div className="h-6 w-px bg-border" />

        {/* Notifications */}
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon"
                className="relative size-10 text-muted-foreground hover:text-foreground"
              />
            }
          >
            <Bell className="size-5" />
            {/* Notification badge */}
            <span className="absolute top-0.5 right-0.5 flex size-5 items-center justify-center rounded-full bg-red-500 text-[11px] font-bold text-white">
              3
            </span>
            <span className="sr-only">Notifications</span>
          </TooltipTrigger>
          <TooltipContent>Notifications</TooltipContent>
        </Tooltip>

        {/* User avatar */}
        <Button
          variant="ghost"
          size="icon"
          className="size-10 rounded-full bg-muted/50 text-muted-foreground hover:text-foreground"
        >
          <User className="size-5" />
          <span className="sr-only">User menu</span>
        </Button>
      </div>
    </header>
  )
}
