"use client"

import * as React from "react"
import { ChevronDown, Globe } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import {
  useAccountStore,
  type AccountProvider,
} from "@/lib/stores/account-store"

const providerLabels: Record<AccountProvider, string> = {
  aws: "AWS",
  gcp: "GCP",
  azure: "AZ",
  ncloud: "NC",
}

const providerColors: Record<AccountProvider, string> = {
  aws: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  gcp: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  azure: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  ncloud: "bg-green-500/20 text-green-400 border-green-500/30",
}

function ProviderBadge({ provider }: { provider: AccountProvider }) {
  return (
    <span
      className={cn(
        "inline-flex h-5 w-8 shrink-0 items-center justify-center rounded border font-mono text-[10px] font-bold",
        providerColors[provider]
      )}
    >
      {providerLabels[provider]}
    </span>
  )
}

function StatusDot({ status }: { status: "connected" | "disconnected" }) {
  return (
    <span
      className={cn(
        "inline-block size-2 shrink-0 rounded-full",
        status === "connected" ? "bg-emerald-500" : "bg-red-500"
      )}
    />
  )
}

export function AccountSwitcher() {
  const { activeAccountId, accounts, setActiveAccount } = useAccountStore()

  const activeAccount = activeAccountId
    ? accounts.find((a) => a.id === activeAccountId)
    : null

  // Group accounts by provider
  const grouped = accounts.reduce<Record<AccountProvider, typeof accounts>>(
    (acc, account) => {
      if (!acc[account.provider]) {
        acc[account.provider] = []
      }
      acc[account.provider].push(account)
      return acc
    },
    {} as Record<AccountProvider, typeof accounts>
  )

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="outline"
            className="h-8 gap-2 border-border/60 bg-muted/30 px-3 font-mono text-sm text-foreground hover:bg-muted/50"
          />
        }
      >
        {activeAccount ? (
          <>
            <ProviderBadge provider={activeAccount.provider} />
            <span className="max-w-[120px] truncate">{activeAccount.name}</span>
            <StatusDot status={activeAccount.status} />
          </>
        ) : (
          <>
            <Globe className="size-4 text-muted-foreground" />
            <span>All Accounts</span>
          </>
        )}
        <ChevronDown className="ml-0.5 size-3.5 text-muted-foreground" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="start" sideOffset={6} className="w-64">
        {/* All Accounts option */}
        <DropdownMenuItem
          className={cn(
            "gap-2.5 px-2.5 py-2 font-mono",
            !activeAccountId && "bg-primary/10 text-primary"
          )}
          onClick={() => setActiveAccount(null)}
        >
          <Globe className="size-4" />
          <span className="text-sm font-medium">All Accounts</span>
          {!activeAccountId && (
            <span className="ml-auto text-xs text-primary">Active</span>
          )}
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        {/* Grouped by provider */}
        {(Object.entries(grouped) as [AccountProvider, typeof accounts][]).map(
          ([provider, providerAccounts]) => (
            <DropdownMenuGroup key={provider}>
              <DropdownMenuLabel className="flex items-center gap-2 px-2.5 py-1.5 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                <ProviderBadge provider={provider} />
                {provider === "aws"
                  ? "Amazon Web Services"
                  : provider === "gcp"
                    ? "Google Cloud Platform"
                    : provider === "azure"
                      ? "Microsoft Azure"
                      : "Other Cloud"}
              </DropdownMenuLabel>
              {providerAccounts.map((account) => (
                <DropdownMenuItem
                  key={account.id}
                  className={cn(
                    "gap-2.5 px-2.5 py-2 font-mono",
                    activeAccountId === account.id &&
                      "bg-primary/10 text-primary"
                  )}
                  onClick={() => setActiveAccount(account.id)}
                >
                  <StatusDot status={account.status} />
                  <div className="flex flex-1 flex-col">
                    <span className="text-sm font-medium">
                      {account.name}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {account.accountId} &middot; {account.region}
                    </span>
                  </div>
                  <span className="rounded bg-muted/50 px-1.5 py-0.5 text-[10px] uppercase text-muted-foreground">
                    {account.role}
                  </span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
          )
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
