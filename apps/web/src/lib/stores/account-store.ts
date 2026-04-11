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
    id: "nx",
    name: "nexus",
    alias: "nx",
    provider: "aws",
    accountId: "444444444444",
    region: "ap-northeast-2",
    role: "hub",
    status: "connected",
  },
  {
    id: "shared",
    name: "shared",
    alias: "shared",
    provider: "aws",
    accountId: "222222222222",
    region: "ap-northeast-2",
    role: "spoke",
    status: "connected",
  },
  {
    id: "nw",
    name: "prod-a",
    alias: "nw",
    provider: "aws",
    accountId: "111111111111",
    region: "ap-northeast-2",
    role: "spoke",
    status: "connected",
  },
  {
    id: "dp",
    name: "prod-b",
    alias: "dp",
    provider: "aws",
    accountId: "333333333333",
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
