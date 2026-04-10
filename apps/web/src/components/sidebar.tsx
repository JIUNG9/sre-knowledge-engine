"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Shield,
  Search,
  BarChart3,
  DollarSign,
  AlertTriangle,
  ShieldCheck,
  Rocket,
  Phone,
  BookOpen,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { LanguageSwitcher } from "@/components/language-switcher"

const navItems = [
  { label: "Log Explorer", icon: Search, href: "/logs" },
  { label: "SLO/SLI Dashboard", icon: BarChart3, href: "/slo" },
  { label: "FinOps", icon: DollarSign, href: "/finops" },
  { label: "Incidents", icon: AlertTriangle, href: "/incidents" },
  { label: "Security", icon: ShieldCheck, href: "/security" },
  { label: "Deployments", icon: Rocket, href: "/deployments" },
  { label: "On-Call", icon: Phone, href: "/oncall" },
  { label: "Service Catalog", icon: BookOpen, href: "/catalog" },
] as const

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname()

  return (
    <aside
      className={cn(
        "relative flex h-full flex-col border-r border-border bg-sidebar transition-all duration-300 ease-in-out",
        collapsed ? "w-[52px]" : "w-[220px]"
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 px-3">
        <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary/10">
          <Shield className="size-4 text-primary" />
        </div>
        {!collapsed && (
          <span className="font-heading text-sm font-semibold tracking-wider text-foreground">
            AEGIS
          </span>
        )}
      </div>

      <Separator />

      {/* Navigation */}
      <ScrollArea className="flex-1 py-2">
        <nav className="flex flex-col gap-0.5 px-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href
            const linkContent = (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-sm font-medium transition-all duration-150 outline-none",
                  "hover:bg-surface-hover hover:text-foreground",
                  isActive
                    ? "bg-primary/10 text-primary glow-matrix"
                    : "text-muted-foreground"
                )}
              >
                <item.icon
                  className={cn(
                    "size-4 shrink-0 transition-colors",
                    isActive
                      ? "text-primary"
                      : "text-muted-foreground group-hover:text-foreground"
                  )}
                />
                {!collapsed && (
                  <span className="truncate">{item.label}</span>
                )}
              </Link>
            )

            if (collapsed) {
              return (
                <Tooltip key={item.href}>
                  <TooltipTrigger render={linkContent} />
                  <TooltipContent side="right">
                    {item.label}
                  </TooltipContent>
                </Tooltip>
              )
            }

            return linkContent
          })}
        </nav>
      </ScrollArea>

      <Separator />

      {/* Collapse toggle */}
      <div className="flex items-center justify-center py-2">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onToggle}
          className="text-muted-foreground hover:text-foreground"
        >
          {collapsed ? (
            <ChevronRight className="size-4" />
          ) : (
            <ChevronLeft className="size-4" />
          )}
        </Button>
      </div>

      {/* Language switcher */}
      <div className="px-2 py-1">
        <LanguageSwitcher collapsed={collapsed} />
      </div>

      {/* Version footer */}
      {!collapsed && (
        <div className="px-3 pb-2">
          <span className="font-mono text-xs text-muted-foreground/50">
            v0.1.0
          </span>
        </div>
      )}
    </aside>
  )
}
