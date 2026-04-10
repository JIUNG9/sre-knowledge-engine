"use client"

import { create } from "zustand"

export interface CloudAccount {
  id: string
  provider: "aws" | "gcp" | "azure" | "ncloud" | "custom"
  name: string
  alias: string
  accountId: string
  region: string
  role: "hub" | "spoke" | "standalone"
  connectionMethod: "access-key" | "assume-role"
  connectionValue: string
  status: "connected" | "error" | "pending"
}

export interface Integration {
  id: string
  name: string
  category: "monitoring" | "deployment" | "notification" | "ticketing" | "security"
  status: "not-configured" | "connected" | "error"
  config: Record<string, string>
}

export interface TeamMember {
  id: string
  name: string
  email: string
  role: "admin" | "member" | "viewer"
}

export interface KeycloakConfig {
  url: string
  realm: string
  clientId: string
  clientSecret: string
}

interface SetupState {
  currentStep: number
  claudeApiKey: string
  claudeKeyTested: boolean
  accounts: CloudAccount[]
  integrations: Integration[]
  teamName: string
  members: TeamMember[]
  keycloakEnabled: boolean
  keycloakConfig: KeycloakConfig | null
  analysisComplete: boolean

  setStep: (step: number) => void
  setClaudeApiKey: (key: string) => void
  setClaudeKeyTested: (tested: boolean) => void
  addAccount: (account: CloudAccount) => void
  removeAccount: (id: string) => void
  updateAccountStatus: (id: string, status: CloudAccount["status"]) => void
  updateIntegration: (id: string, config: Record<string, string>, status: Integration["status"]) => void
  setTeamName: (name: string) => void
  addMember: (member: TeamMember) => void
  removeMember: (id: string) => void
  setKeycloakEnabled: (enabled: boolean) => void
  setKeycloakConfig: (config: KeycloakConfig | null) => void
  setAnalysisComplete: (complete: boolean) => void
  completeSetup: () => void
}

const defaultIntegrations: Integration[] = [
  { id: "signoz", name: "SigNoz", category: "monitoring", status: "not-configured", config: {} },
  { id: "datadog", name: "Datadog", category: "monitoring", status: "not-configured", config: {} },
  { id: "prometheus", name: "Prometheus", category: "monitoring", status: "not-configured", config: {} },
  { id: "slack", name: "Slack", category: "notification", status: "not-configured", config: {} },
  { id: "jira", name: "JIRA", category: "ticketing", status: "not-configured", config: {} },
  { id: "github", name: "GitHub", category: "ticketing", status: "not-configured", config: {} },
  { id: "argocd", name: "ArgoCD", category: "deployment", status: "not-configured", config: {} },
  { id: "trivy", name: "Trivy", category: "security", status: "not-configured", config: {} },
]

export const useSetupStore = create<SetupState>((set) => ({
  currentStep: 0,
  claudeApiKey: "",
  claudeKeyTested: false,
  accounts: [],
  integrations: defaultIntegrations,
  teamName: "",
  members: [],
  keycloakEnabled: false,
  keycloakConfig: null,
  analysisComplete: false,

  setStep: (step) => set({ currentStep: step }),
  setClaudeApiKey: (key) => set({ claudeApiKey: key, claudeKeyTested: false }),
  setClaudeKeyTested: (tested) => set({ claudeKeyTested: tested }),

  addAccount: (account) =>
    set((state) => ({ accounts: [...state.accounts, account] })),
  removeAccount: (id) =>
    set((state) => ({ accounts: state.accounts.filter((a) => a.id !== id) })),
  updateAccountStatus: (id, status) =>
    set((state) => ({
      accounts: state.accounts.map((a) => (a.id === id ? { ...a, status } : a)),
    })),

  updateIntegration: (id, config, status) =>
    set((state) => ({
      integrations: state.integrations.map((i) =>
        i.id === id ? { ...i, config, status } : i
      ),
    })),

  setTeamName: (name) => set({ teamName: name }),
  addMember: (member) =>
    set((state) => ({ members: [...state.members, member] })),
  removeMember: (id) =>
    set((state) => ({ members: state.members.filter((m) => m.id !== id) })),

  setKeycloakEnabled: (enabled) => set({ keycloakEnabled: enabled }),
  setKeycloakConfig: (config) => set({ keycloakConfig: config }),
  setAnalysisComplete: (complete) => set({ analysisComplete: complete }),

  completeSetup: () => {
    if (typeof window !== "undefined") {
      localStorage.setItem("aegis_setup_complete", "true")
    }
  },
}))
