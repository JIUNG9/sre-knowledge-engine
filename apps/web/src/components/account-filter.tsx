"use client";

import { Filter, Check } from "lucide-react";
import { useAccountStore } from "@/lib/stores/account-store";
import { cn } from "@/lib/utils";

interface AccountFilterProps {
  value: string | null;
  onChange: (value: string | null) => void;
}

export function AccountFilter({ value, onChange }: AccountFilterProps) {
  const { accounts } = useAccountStore();

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <Filter className="size-4 text-muted-foreground" />
      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Account:
      </span>

      {/* All chip */}
      <button
        onClick={() => onChange(null)}
        className={cn(
          "flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold transition-all border",
          !value
            ? "bg-primary text-primary-foreground border-primary"
            : "bg-muted/50 text-foreground border-border hover:bg-muted"
        )}
      >
        {!value && <Check className="size-3.5" />}
        All
      </button>

      {/* Per-account chips */}
      {accounts.map((acc) => (
        <button
          key={acc.id}
          onClick={() => onChange(acc.id === value ? null : acc.id)}
          className={cn(
            "flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-all border",
            value === acc.id
              ? "bg-primary text-primary-foreground border-primary"
              : "bg-muted/50 text-foreground border-border hover:bg-muted"
          )}
        >
          {value === acc.id && <Check className="size-3.5" />}
          <span className={cn(
            "rounded px-1.5 py-0.5 text-[10px] font-bold uppercase",
            value === acc.id ? "bg-black/20" : "bg-primary/15 text-primary"
          )}>
            {acc.provider}
          </span>
          {acc.name}
          <span className={cn(
            "text-xs",
            value === acc.id ? "text-primary-foreground/70" : "text-muted-foreground"
          )}>
            ({acc.role})
          </span>
        </button>
      ))}
    </div>
  );
}
