"use client"

import * as React from "react"
import { Sparkles } from "lucide-react"
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
  const { togglePanel, openPanel } = useAIStore()

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

      {/* Floating AI button */}
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={openPanel}
          className="flex items-center gap-3 rounded-2xl bg-primary px-6 py-4 shadow-lg transition-shadow hover:shadow-xl"
          style={{ boxShadow: "0 4px 30px rgba(0,255,136,0.3)" }}
        >
          <Sparkles className="size-[22px] text-primary-foreground" />
          <span className="text-base font-bold text-primary-foreground">
            Ask AI
          </span>
          <kbd className="rounded bg-black/20 px-1.5 py-0.5 font-mono text-xs text-primary-foreground/80">
            &#8984;J
          </kbd>
        </button>
      </div>

      {/* AI Assistant slide-in panel */}
      <AIAssistantPanel />
    </div>
  )
}
