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
  ChevronDown,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  useAccountStore,
  type AccountProvider,
} from "@/lib/stores/account-store"

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
  const { activeAccountId, accounts, setActiveAccount } = useAccountStore()
  const [accountDropdownOpen, setAccountDropdownOpen] = React.useState(false)

  const activeAccount = activeAccountId
    ? accounts.find((a) => a.id === activeAccountId)
    : null

  // Count accounts by provider
  const providerCounts = accounts.reduce<Record<string, number>>(
    (acc, account) => {
      acc[account.provider] = (acc[account.provider] || 0) + 1
      return acc
    },
    {}
  )

  const awsCount = providerCounts["aws"] || 0
  const gcpCount = providerCounts["gcp"] || 0
  const azureCount = providerCounts["azure"] || 0

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

      {/* Service Account Card — INTERACTIVE DROPDOWN */}
      {!collapsed && (
        <div className="px-3 pb-2">
          <div className="group relative">
            <button
              onClick={() => setAccountDropdownOpen(!accountDropdownOpen)}
              className="w-full rounded-lg border border-primary/20 bg-primary/5 px-4 py-3 text-left transition-colors hover:bg-primary/10 hover:border-primary/40"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Service Account
                </span>
                <ChevronDown className={cn("size-4 text-primary transition-transform", accountDropdownOpen && "rotate-180")} />
              </div>
              <div className="mt-1.5 flex items-center gap-2">
                <span className="size-2.5 rounded-full bg-emerald-500" />
                <span className="text-base font-bold text-foreground">
                  {activeAccount ? activeAccount.name : "All Accounts"}
                </span>
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                {awsCount} AWS &middot; {gcpCount} GCP &middot; {azureCount} Azure
              </div>
            </button>

            {/* Dropdown */}
            {accountDropdownOpen && (
              <div className="absolute left-0 right-0 top-full z-50 mt-1 rounded-lg border border-border bg-card p-1.5 shadow-xl">
                <button
                  onClick={() => { setActiveAccount(null); setAccountDropdownOpen(false) }}
                  className={cn(
                    "flex w-full items-center gap-2.5 rounded-md px-3 py-2.5 text-left transition-colors hover:bg-surface-hover",
                    !activeAccountId && "bg-primary/10"
                  )}
                >
                  <span className="size-2.5 rounded-full bg-emerald-500" />
                  <span className={cn("text-sm font-medium", !activeAccountId ? "text-primary" : "text-foreground")}>
                    All Accounts
                  </span>
                  <span className="ml-auto text-xs text-muted-foreground">{accounts.length}</span>
                </button>
                <div className="my-1 h-px bg-border" />
                {accounts.map((acc) => (
                  <button
                    key={acc.id}
                    onClick={() => { setActiveAccount(acc.id); setAccountDropdownOpen(false) }}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-md px-3 py-2.5 text-left transition-colors hover:bg-surface-hover",
                      activeAccountId === acc.id && "bg-primary/10"
                    )}
                  >
                    <span className={cn("size-2.5 rounded-full", acc.status === "connected" ? "bg-emerald-500" : "bg-red-400")} />
                    <div className="flex-1 min-w-0">
                      <span className={cn("text-sm font-medium", activeAccountId === acc.id ? "text-primary" : "text-foreground")}>
                        {acc.name}
                      </span>
                      <span className="ml-2 text-xs text-muted-foreground">{acc.alias}</span>
                    </div>
                    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-bold text-muted-foreground uppercase">
                      {acc.provider}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <Separator />

      {/* Main Navigation */}
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-2">
        {mainNavItems.map((item) => {
          const isActive = pathname === item.href
          return renderNavItem(item, isActive)
        })}
      </nav>

      <Separator />

      {/* Bottom section */}
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
