"use client"

import * as React from "react"
import { Shield, User, Sparkles } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useAIStore } from "@/lib/stores/ai-store"
import { AccountSwitcher } from "@/components/account-switcher"

export function CommandBar() {
  const openPanel = useAIStore((s) => s.openPanel)

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-sm">
      {/* Left: Logo + branding (visible on mobile where sidebar is hidden) */}
      <div className="flex items-center gap-2 md:hidden">
        <div className="flex size-7 items-center justify-center rounded-md bg-primary/10">
          <Shield className="size-4 text-primary" />
        </div>
        <span className="font-heading text-sm font-semibold tracking-wider text-foreground">
          AEGIS
        </span>
      </div>

      {/* Center: Search / Command palette trigger */}
      <div className="mx-auto flex w-full max-w-md items-center md:mx-0 md:ml-0">
        <div className="relative w-full">
          <Input
            type="search"
            placeholder="Search or run command..."
            className="h-10 bg-muted/50 pl-3 pr-16 font-mono text-sm placeholder:text-muted-foreground/60 focus-visible:border-primary/40 focus-visible:ring-primary/20"
            readOnly
          />
          <kbd className="pointer-events-none absolute top-1/2 right-2 flex h-5 -translate-y-1/2 items-center gap-0.5 rounded border border-border bg-muted px-1.5 font-mono text-xs text-muted-foreground">
            <span className="text-xs">&#8984;</span>K
          </kbd>
        </div>
      </div>

      <Separator orientation="vertical" className="mx-3 hidden h-6 md:block" />

      {/* Account Switcher */}
      <div className="hidden md:flex">
        <AccountSwitcher />
      </div>

      <Separator orientation="vertical" className="mx-3 hidden h-6 md:block" />

      {/* Right: AI Assistant + User */}
      <div className="flex items-center gap-1.5">
        <Tooltip>
          <TooltipTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={openPanel}
                className="relative text-muted-foreground hover:text-foreground"
              />
            }
          >
            <Sparkles className="size-4" />
            {/* Green availability dot */}
            <span className="absolute top-1 right-1 size-1.5 rounded-full bg-emerald-500" />
            <span className="sr-only">AI Assistant</span>
          </TooltipTrigger>
          <TooltipContent>
            AI Assistant
            <kbd className="ml-1.5 rounded border border-border bg-muted px-1 font-mono text-[10px]">
              &#8984;J
            </kbd>
          </TooltipContent>
        </Tooltip>

        <Button
          variant="ghost"
          size="icon-sm"
          className="text-muted-foreground hover:text-foreground"
        >
          <User className="size-4" />
          <span className="sr-only">User menu</span>
        </Button>
      </div>
    </header>
  )
}
