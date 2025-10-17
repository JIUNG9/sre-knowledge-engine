"use client"

import * as React from "react"
import { Shield, Terminal, Activity, ArrowRight } from "lucide-react"
import { Sidebar } from "@/components/sidebar"
import { CommandBar } from "@/components/command-bar"
import { Button } from "@/components/ui/button"

export default function Home() {
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar — hidden on mobile, visible on md+ */}
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
        <main className="flex flex-1 items-center justify-center overflow-auto p-6">
          <div className="flex max-w-lg flex-col items-center text-center">
            {/* Shield icon with glow */}
            <div className="relative mb-8">
              <div className="absolute inset-0 rounded-full bg-primary/20 blur-2xl" />
              <div className="relative flex size-20 items-center justify-center rounded-2xl border border-primary/20 bg-primary/5 glow-matrix">
                <Shield className="size-10 text-primary" />
              </div>
            </div>

            {/* Title */}
            <h1 className="font-heading text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Welcome to{" "}
              <span className="text-primary text-glow">Aegis</span>
            </h1>

            {/* Tagline */}
            <p className="mt-3 max-w-md text-base text-muted-foreground">
              AI-Native DevSecOps Command Center. Unified observability,
              security, and operations — from a single pane of glass.
            </p>

            {/* Status indicators */}
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <StatusPill icon={Terminal} label="CLI Ready" />
              <StatusPill icon={Activity} label="Systems Nominal" />
              <StatusPill icon={Shield} label="Security Active" />
            </div>

            {/* CTA */}
            <div className="mt-8 flex gap-3">
              <Button variant="default" className="gap-1.5 font-mono text-xs">
                Get Started
                <ArrowRight className="size-3.5" />
              </Button>
              <Button variant="outline" className="font-mono text-xs">
                View Docs
              </Button>
            </div>

            {/* Version */}
            <p className="mt-12 font-mono text-[11px] text-muted-foreground/40">
              aegis v0.1.0 &middot; build 2026.04.10
            </p>
          </div>
        </main>
      </div>
    </div>
  )
}

function StatusPill({
  icon: Icon,
  label,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
}) {
  return (
    <div className="flex items-center gap-1.5 rounded-full border border-border bg-muted/50 px-3 py-1">
      <span className="relative flex size-1.5">
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-75" />
        <span className="relative inline-flex size-1.5 rounded-full bg-primary" />
      </span>
      <Icon className="size-3 text-muted-foreground" />
      <span className="font-mono text-[11px] text-muted-foreground">
        {label}
      </span>
    </div>
  )
}
