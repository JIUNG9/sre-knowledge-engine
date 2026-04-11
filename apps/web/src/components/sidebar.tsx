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
  KeyRound,
  Rocket,
  Phone,
  BookOpen,
  Settings,
  Users,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

const mainNavItems = [
  { label: "Log Explorer", icon: Search, href: "/logs" },
  { label: "SLO Dashboard", icon: BarChart3, href: "/slo" },
  { label: "FinOps", icon: DollarSign, href: "/finops" },
  { label: "Incidents", icon: AlertTriangle, href: "/incidents", badge: 2 },
  { label: "Security", icon: ShieldCheck, href: "/security" },
  { label: "IAM Audit", icon: KeyRound, href: "/iam" },
  { label: "Deployments", icon: Rocket, href: "/deployments" },
  { label: "On-Call", icon: Phone, href: "/oncall" },
  { label: "Services", icon: BookOpen, href: "/services" },
] as const

const bottomNavItems = [
  { label: "Account Mgmt", icon: Users, href: "/accounts" },
  { label: "Settings", icon: Settings, href: "/settings" },
] as const

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname()

  function renderNavItem(
    item: { label: string; icon: React.ElementType; href: string; badge?: number },
    isActive: boolean
  ) {
    const linkContent = (
      <Link
        key={item.href}
        href={item.href}
        className={cn(
          "group relative flex w-full items-center gap-3 rounded-md px-4 py-3.5 text-[15px] font-medium transition-all duration-150 outline-none",
          "hover:bg-surface-hover hover:text-foreground",
          isActive
            ? "border-l-2 border-primary bg-primary/10 text-primary"
            : "border-l-2 border-transparent text-muted-foreground"
        )}
      >
        <item.icon
          className={cn(
            "size-5 shrink-0 transition-colors",
            isActive
              ? "text-primary"
              : "text-muted-foreground group-hover:text-foreground"
          )}
        />
        {!collapsed && (
          <span className="truncate">{item.label}</span>
        )}
        {!collapsed && item.badge && item.badge > 0 && (
          <span className="ml-auto flex size-5 items-center justify-center rounded-full bg-red-500 text-[11px] font-bold text-white">
            {item.badge}
          </span>
        )}
      </Link>
    )

    if (collapsed) {
      return (
        <Tooltip key={item.href}>
          <TooltipTrigger render={linkContent} />
          <TooltipContent side="right">
            {item.label}
            {item.badge && item.badge > 0 && (
              <span className="ml-1.5 rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
                {item.badge}
              </span>
            )}
          </TooltipContent>
        </Tooltip>
      )
    }

    return linkContent
  }

  return (
    <aside
      className={cn(
        "relative flex h-full flex-col border-r border-border bg-sidebar transition-all duration-300 ease-in-out",
        collapsed ? "w-[56px]" : "w-64"
      )}
    >
      {/* Logo row */}
      <div className="flex h-14 items-center gap-2.5 px-3">
        <div className="flex size-8 shrink-0 items-center justify-center">
          <Shield className="size-6 text-primary" />
        </div>
        {!collapsed && (
          <span className="font-heading text-lg font-bold tracking-wider text-foreground">
            AEGIS
          </span>
        )}
        <div className="ml-auto">
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
      </div>

      <Separator />

      {/* Main Navigation — fills all available space */}
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-2">
        {mainNavItems.map((item) => {
          const isActive = pathname === item.href
          return renderNavItem(item, isActive)
        })}
      </nav>

      <Separator />

      {/* Bottom section — Account Mgmt + Settings */}
      <div className="flex flex-col gap-0.5 px-2 py-2">
        {bottomNavItems.map((item) => {
          const isActive = pathname === item.href
          return renderNavItem(item, isActive)
        })}
      </div>

      {/* Version */}
      {!collapsed && (
        <div className="px-4 pb-3">
          <span className="font-mono text-[11px] text-muted-foreground/40">
            v2.0.0
          </span>
        </div>
      )}
    </aside>
  )
}
