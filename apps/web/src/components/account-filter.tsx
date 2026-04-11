"use client"

import { Cloud } from "lucide-react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useAccountStore } from "@/lib/stores/account-store"

interface AccountFilterProps {
  value: string | null
  onChange: (value: string | null) => void
}

export function AccountFilter({ value, onChange }: AccountFilterProps) {
  const { accounts } = useAccountStore()

  return (
    <div className="flex items-center gap-3 rounded-xl border border-primary/20 bg-primary/5 px-4 py-2.5">
      <div className="flex items-center gap-2">
        <Cloud className="size-5 text-primary" />
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Service Account
        </span>
      </div>
      <Select
        value={value || "all"}
        onValueChange={(v) => onChange(v === "all" ? null : v)}
      >
        <SelectTrigger className="h-9 w-44 border-border/60 bg-background text-sm font-semibold">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Accounts</SelectItem>
          {accounts.map((acc) => (
            <SelectItem key={acc.id} value={acc.id}>
              <div className="flex items-center gap-2">
                <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-bold uppercase">
                  {acc.provider}
                </span>
                {acc.name}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
