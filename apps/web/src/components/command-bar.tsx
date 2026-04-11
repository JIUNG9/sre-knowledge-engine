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

      {/* Right: Search + Language + Notifications + User */}
      <div className="flex items-center gap-1.5">
        {/* Search trigger */}
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon"
                className="text-muted-foreground hover:text-foreground"
              />
            }
          >
            <Search className="size-[18px]" />
            <span className="sr-only">Search</span>
          </TooltipTrigger>
          <TooltipContent>
            Search
            <kbd className="ml-1.5 rounded border border-border bg-muted px-1 font-mono text-[10px]">
              &#8984;K
            </kbd>
          </TooltipContent>
        </Tooltip>

        {/* Language Switcher */}
        <LanguageSwitcher />

        {/* Notifications */}
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon"
                className="relative text-muted-foreground hover:text-foreground"
              />
            }
          >
            <Bell className="size-[18px]" />
            {/* Notification badge */}
            <span className="absolute top-1 right-1 flex size-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white">
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
          className="text-muted-foreground hover:text-foreground"
        >
          <User className="size-[18px]" />
          <span className="sr-only">User menu</span>
        </Button>
      </div>
    </header>
  )
}
