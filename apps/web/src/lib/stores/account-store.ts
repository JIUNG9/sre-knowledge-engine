"use client"

import { create } from "zustand"

export type AccountProvider = "aws" | "gcp" | "azure" | "ncloud"
export type AccountRole = "hub" | "spoke"
export type AccountStatus = "connected" | "disconnected"

export interface ServiceAccount {
  id: string
  name: string
  alias: string
  provider: AccountProvider
  accountId: string
  region: string
  role: AccountRole
  status: AccountStatus
}

interface AccountState {
  activeAccountId: string | null // null = "All Accounts"
  accounts: ServiceAccount[]
  setActiveAccount: (id: string | null) => void
}

const mockAccounts: ServiceAccount[] = [
  {
    id: "hub",
    name: "hub",
    alias: "hub",
    provider: "aws",
    accountId: "123456789012",
    region: "ap-northeast-2",
    role: "hub",
    status: "connected",
  },
  {
    id: "shared-services",
    name: "shared-services",
    alias: "shared-services",
    provider: "aws",
    accountId: "111122223333",
    region: "ap-northeast-2",
    role: "spoke",
    status: "connected",
  },
  {
    id: "prod-a",
    name: "prod-a",
    alias: "prod-a",
    provider: "aws",
    accountId: "987654321098",
    region: "ap-northeast-2",
    role: "spoke",
    status: "connected",
  },
  {
    id: "prod-b",
    name: "prod-b",
    alias: "prod-b",
    provider: "aws",
    accountId: "000000000000",
    region: "ap-northeast-1",
    role: "spoke",
    status: "disconnected",
  },
]

export const useAccountStore = create<AccountState>((set) => ({
  activeAccountId: null,
  accounts: mockAccounts,
  setActiveAccount: (id: string | null) => set({ activeAccountId: id }),
}))

// Maps each service name to its owning account ID
export const SERVICE_TO_ACCOUNT: Record<string, string> = {
  "api-gateway": "hub",
  "deployment-controller": "hub",
  "auth-service": "shared-services",
  "user-service": "shared-services",
  "payment-service": "shared-services",
  "notification-service": "shared-services",
  "config-service": "prod-a",
  "audit-service": "prod-a",
}

// Maps account IDs to the list of services in that account
export const ACCOUNT_SERVICES: Record<string, string[]> = {
  hub: ["api-gateway", "deployment-controller"],
  "shared-services": ["auth-service", "user-service", "payment-service", "notification-service"],
  "prod-a": ["config-service", "audit-service"],
  "prod-b": [],
}

// Helper: get services filtered by account (null = all)
export function getServicesForAccount(accountId: string | null): string[] {
  if (!accountId) {
    return Object.values(ACCOUNT_SERVICES).flat()
  }
  return ACCOUNT_SERVICES[accountId] ?? []
}

// Helper: get account name by ID
export function getAccountName(accountId: string): string {
  const account = mockAccounts.find((a) => a.id === accountId)
  return account?.name ?? accountId
}
