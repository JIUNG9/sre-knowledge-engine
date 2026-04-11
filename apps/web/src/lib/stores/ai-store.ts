"use client"

import { create } from "zustand"
import { type ChatMessage, mockMessages } from "@/lib/mock-data/ai-chat"

export type AIMode = "eco" | "standard" | "deep"

interface AIState {
  isOpen: boolean
  messages: ChatMessage[]
  currentModule: string
  sessionTokens: number
  sessionCost: number
  budget: number
  isLoading: boolean
  aiMode: AIMode
  monthlyBudget: number
  monthlySpent: number
  autoDowngradeThreshold: number
  notificationThresholds: number[]
  togglePanel: () => void
  openPanel: () => void
  closePanel: () => void
  sendMessage: (message: string) => void
  setModule: (module: string) => void
  setAIMode: (mode: AIMode) => void
  setMonthlyBudget: (budget: number) => void
  setAutoDowngradeThreshold: (threshold: number) => void
  toggleNotificationThreshold: (threshold: number) => void
}

export const useAIStore = create<AIState>((set, get) => ({
  isOpen: false,
  messages: mockMessages,
  currentModule: "Dashboard",
  sessionTokens: 12400,
  sessionCost: 0.05,
  budget: 5.0,
  isLoading: false,
  aiMode: "standard",
  monthlyBudget: 10.0,
  monthlySpent: 4.82,
  autoDowngradeThreshold: 80,
  notificationThresholds: [50, 80, 100],

  togglePanel: () => set((state) => ({ isOpen: !state.isOpen })),
  openPanel: () => set({ isOpen: true }),
  closePanel: () => set({ isOpen: false }),

  sendMessage: (content: string) => {
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content,
      timestamp: new Date().toISOString(),
    }

    set((state) => ({
      messages: [...state.messages, userMessage],
      isLoading: true,
    }))

    // Simulate AI response after a delay
    setTimeout(() => {
      const aiMessage: ChatMessage = {
        id: `msg-${Date.now()}-ai`,
        role: "assistant",
        content:
          "I'm analyzing your request. This is a mock response — in production, this would connect to the Claude API via your configured endpoint.",
        timestamp: new Date().toISOString(),
        toolCalls: [
          {
            id: `tc-${Date.now()}`,
            toolName: "query_metrics",
            status: "success",
            durationMs: 340,
            result: JSON.stringify({ status: "mock_response", note: "Connect API for live data" }, null, 2),
          },
        ],
      }

      set((state) => ({
        messages: [...state.messages, aiMessage],
        isLoading: false,
        sessionTokens: state.sessionTokens + 1800,
        sessionCost: state.sessionCost + 0.01,
      }))
    }, 1500)
  },

  setModule: (module: string) => set({ currentModule: module }),
  setAIMode: (mode: AIMode) => set({ aiMode: mode }),
  setMonthlyBudget: (budget: number) => set({ monthlyBudget: budget }),
  setAutoDowngradeThreshold: (threshold: number) =>
    set({ autoDowngradeThreshold: threshold }),
  toggleNotificationThreshold: (threshold: number) =>
    set((state) => {
      const current = state.notificationThresholds
      if (current.includes(threshold)) {
        return { notificationThresholds: current.filter((t) => t !== threshold) }
      }
      return {
        notificationThresholds: [...current, threshold].sort((a, b) => a - b),
      }
    }),
}))
