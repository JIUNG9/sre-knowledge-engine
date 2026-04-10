"use client"

import * as React from "react"
import {
  Area,
  AreaChart,
  ResponsiveContainer,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { ArrowDown, ArrowUp, ArrowUpDown, Minus } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  SERVICE_COSTS,
  type ServiceCostRow,
} from "@/lib/mock-data/finops"

// --- Helpers ---

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

type SortField =
  | "service"
  | "team"
  | "account"
  | "provider"
  | "currentMonth"
  | "previousMonth"
  | "changePercent"

type SortDirection = "asc" | "desc"

// --- Sparkline ---

function TrendSparkline({ data, change }: { data: number[]; change: number }) {
  const chartData = data.map((v, i) => ({ idx: i, value: v }))
  const color = change < 0 ? "#00FF88" : change > 0 ? "#FF4444" : "#666"

  return (
    <div className="h-[24px] w-[80px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 2, right: 0, left: 0, bottom: 2 }}
        >
          <defs>
            <linearGradient
              id={`sparkGrad-${color.replace("#", "")}`}
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" stopColor={color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#sparkGrad-${color.replace("#", "")})`}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// --- Change indicator ---

function ChangeIndicator({ change }: { change: number }) {
  if (change === 0) {
    return (
      <span className="flex items-center gap-1 font-mono text-xs text-muted-foreground">
        <Minus className="size-3" />
        0%
      </span>
    )
  }

  const isIncrease = change > 0
  return (
    <span
      className={cn(
        "flex items-center gap-1 font-mono text-xs font-medium",
        isIncrease ? "text-[#FF4444]" : "text-[#00FF88]"
      )}
    >
      {isIncrease ? (
        <ArrowUp className="size-3" />
      ) : (
        <ArrowDown className="size-3" />
      )}
      {Math.abs(change).toFixed(1)}%
    </span>
  )
}

// --- Provider badge ---

function ProviderBadge({ provider }: { provider: string }) {
  const colorMap: Record<string, string> = {
    AWS: "#FF9900",
    GCP: "#4285F4",
    Azure: "#0078D4",
  }
  const color = colorMap[provider] ?? "#888"

  return (
    <Badge
      variant="outline"
      className="font-mono text-xs"
      style={{ borderColor: `${color}40`, color }}
    >
      {provider}
    </Badge>
  )
}

// --- Main component ---

export function CostByService() {
  const [sortField, setSortField] = React.useState<SortField>("currentMonth")
  const [sortDir, setSortDir] = React.useState<SortDirection>("desc")
  const [selectedRow, setSelectedRow] = React.useState<string | null>(null)

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === "asc" ? "desc" : "asc")
    } else {
      setSortField(field)
      setSortDir("desc")
    }
  }

  const sorted = React.useMemo(() => {
    return [...SERVICE_COSTS].sort((a, b) => {
      const aVal = a[sortField]
      const bVal = b[sortField]
      const cmp =
        typeof aVal === "string" && typeof bVal === "string"
          ? aVal.localeCompare(bVal)
          : (aVal as number) - (bVal as number)
      return sortDir === "asc" ? cmp : -cmp
    })
  }, [sortField, sortDir])

  const SortableHead = ({
    field,
    children,
    className,
  }: {
    field: SortField
    children: React.ReactNode
    className?: string
  }) => (
    <TableHead
      className={cn("cursor-pointer select-none hover:text-foreground", className)}
      onClick={() => handleSort(field)}
    >
      <span className="flex items-center gap-1 font-mono text-xs">
        {children}
        <ArrowUpDown
          className={cn(
            "size-3 transition-colors",
            sortField === field
              ? "text-primary"
              : "text-muted-foreground/40"
          )}
        />
      </span>
    </TableHead>
  )

  return (
    <Card size="sm">
      <CardHeader className="border-b">
        <CardTitle className="text-muted-foreground">
          Cost by Service
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <SortableHead field="service">Service</SortableHead>
              <SortableHead field="team">Team</SortableHead>
              <SortableHead field="account">Account</SortableHead>
              <SortableHead field="provider">Provider</SortableHead>
              <SortableHead field="currentMonth" className="text-right">
                Current
              </SortableHead>
              <SortableHead field="previousMonth" className="text-right">
                Previous
              </SortableHead>
              <SortableHead field="changePercent" className="text-right">
                Change
              </SortableHead>
              <TableHead className="font-mono text-xs">Trend</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sorted.map((row) => (
              <TableRow
                key={row.id}
                className={cn(
                  "cursor-pointer transition-colors",
                  selectedRow === row.id && "bg-primary/5"
                )}
                onClick={() =>
                  setSelectedRow(selectedRow === row.id ? null : row.id)
                }
              >
                <TableCell className="font-mono text-xs font-medium text-foreground">
                  {row.service}
                </TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {row.team}
                </TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {row.account}
                </TableCell>
                <TableCell>
                  <ProviderBadge provider={row.provider} />
                </TableCell>
                <TableCell className="text-right font-mono text-xs font-medium text-foreground">
                  {formatCurrency(row.currentMonth)}
                </TableCell>
                <TableCell className="text-right font-mono text-xs text-muted-foreground">
                  {formatCurrency(row.previousMonth)}
                </TableCell>
                <TableCell className="text-right">
                  <ChangeIndicator change={row.changePercent} />
                </TableCell>
                <TableCell>
                  <TrendSparkline
                    data={row.trend}
                    change={row.changePercent}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
