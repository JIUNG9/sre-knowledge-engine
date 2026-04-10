"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { useLocale } from "next-intl"
import { Globe } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const locales = [
  { code: "en", label: "EN", name: "English" },
  { code: "ko", label: "KO", name: "한국어" },
] as const

interface LanguageSwitcherProps {
  collapsed?: boolean
}

export function LanguageSwitcher({ collapsed }: LanguageSwitcherProps) {
  const locale = useLocale()
  const router = useRouter()

  const currentLocale = locales.find((l) => l.code === locale) ?? locales[0]

  function switchLocale(newLocale: string) {
    document.cookie = `aegis-locale=${newLocale};path=/;max-age=${60 * 60 * 24 * 365};samesite=lax`
    router.refresh()
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            size={collapsed ? "icon-sm" : "sm"}
            className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
          >
            <Globe className="size-4 shrink-0" />
            {!collapsed && (
              <span className="text-xs font-medium">{currentLocale.label}</span>
            )}
          </Button>
        }
      />
      <DropdownMenuContent side="top" align="start">
        {locales.map((l) => (
          <DropdownMenuItem
            key={l.code}
            className={cn(locale === l.code && "bg-muted")}
            onSelect={() => switchLocale(l.code)}
          >
            <span className="font-mono text-xs font-medium">{l.label}</span>
            <span className="ml-2 text-xs text-muted-foreground">{l.name}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
