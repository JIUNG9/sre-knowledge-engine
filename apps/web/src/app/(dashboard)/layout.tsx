"use client"

import * as React from "react"
import { Sidebar } from "@/components/sidebar"
import { CommandBar } from "@/components/command-bar"
import { AIAssistantPanel } from "@/components/ai/ai-assistant-panel"
import { useAIStore } from "@/lib/stores/ai-store"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false)
  const togglePanel = useAIStore((s) => s.togglePanel)

  // Register Cmd+J keyboard shortcut
  React.useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "j") {
        e.preventDefault()
        togglePanel()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [togglePanel])

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar -- hidden on mobile, visible on md+ */}
      <div className="hidden md:flex">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      </div>

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <CommandBar />

        {/* Content */}
        <main className="flex flex-1 flex-col overflow-hidden">
          {children}
        </main>
      </div>

      {/* AI Assistant slide-in panel */}
      <AIAssistantPanel />
    </div>
  )
}
