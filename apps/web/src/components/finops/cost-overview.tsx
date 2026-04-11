"use client"

import * as React from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowDown, ArrowUp, DollarSign, TrendingUp } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  TOTAL_CURRENT_MONTH,
  TOTAL_PREVIOUS_MONTH,
  MOM_CHANGE_PERCENT,
  PROVIDER_COSTS,
  TOP_SERVICES,
  DAILY_COSTS,
  type ProviderCost,
  type TopService,
  type DailyCostPoint,
} from "@/lib/mock-data/finops"

// --- Currency formatter ---

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

// --- Custom tooltips ---

interface AreaTooltipProps {
  active?: boolean
  payload?: Array<{ value: number; payload: DailyCostPoint }>
  label?: string
}

function DailySpendTooltip({ active, payload, label }: AreaTooltipProps) {
  if (!active || !payload || !payload.length) return null
  const point = payload[0].payload
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="mb-1.5 font-mono text-muted-foreground">{label}</p>
      <p className="font-mono font-medium text-foreground">
        Total: {formatCurrency(point.total)}
      </p>
      <div className="mt-1 space-y-0.5">
        <p className="font-mono text-xs text-muted-foreground">
          EC2: {formatCurrency(point.ec2)}
        </p>
        <p className="font-mono text-xs text-muted-foreground">
          RDS: {formatCurrency(point.rds)}
        </p>
        <p className="font-mono text-xs text-muted-foreground">
          EKS: {formatCurrency(point.eks)}
        </p>
        <p className="font-mono text-xs text-muted-foreground">
          S3: {formatCurrency(point.s3)}
        </p>
        <p className="font-mono text-xs text-muted-foreground">
          Lambda: {formatCurrency(point.lambda)}
        </p>
      </div>
    </div>
  )
}

interface BarTooltipProps {
  active?: boolean
  payload?: Array<{ value: number; payload: TopService }>
}

function TopServiceTooltip({ active, payload }: BarTooltipProps) {
  if (!active || !payload || !payload.length) return null
  const item = payload[0].payload
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="font-mono font-medium text-foreground">
        {item.service}: {formatCurrency(item.cost)}
      </p>
    </div>
  )
}

interface PieTooltipProps {
  active?: boolean
  payload?: Array<{ value: number; payload: ProviderCost }>
}

function ProviderTooltip({ active, payload }: PieTooltipProps) {
  if (!active || !payload || !payload.length) return null
  const item = payload[0].payload
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="font-mono font-medium text-foreground">
        {item.provider}: {formatCurrency(item.cost)}
      </p>
    </div>
  )
}

// --- Main component ---

export function CostOverview() {
  const isIncrease = MOM_CHANGE_PERCENT > 0

  return (
    <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
      {/* Total Monthly Spend */}
      <Card>
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-muted-foreground">
            <DollarSign className="size-5 text-primary" />
            Monthly Spend
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-5xl font-bold tracking-tight text-foreground">
              {formatCurrency(TOTAL_CURRENT_MONTH)}
            </span>
          </div>
          <div className="mt-3 flex items-center gap-2">
            {isIncrease ? (
              <ArrowUp className="size-4 text-[#FF4444]" />
            ) : (
              <ArrowDown className="size-4 text-[#00FF88]" />
            )}
            <span
              className={cn(
                "font-mono text-base font-medium",
                isIncrease ? "text-[#FF4444]" : "text-[#00FF88]"
              )}
            >
              {MOM_CHANGE_PERCENT}%
            </span>
            <span className="font-mono text-sm text-muted-foreground">
              vs {formatCurrency(TOTAL_PREVIOUS_MONTH)} prev
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Cost by Provider (donut) */}
      <Card>
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-muted-foreground">
            <TrendingUp className="size-5 text-primary" />
            By Provider
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="flex items-center gap-5">
            <div className="size-[140px] shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={PROVIDER_COSTS}
                    dataKey="cost"
                    nameKey="provider"
                    cx="50%"
                    cy="50%"
                    innerRadius={28}
                    outerRadius={45}
                    strokeWidth={0}
                  >
                    {PROVIDER_COSTS.map((entry) => (
                      <Cell key={entry.provider} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip content={<ProviderTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-col gap-2">
              {PROVIDER_COSTS.map((p) => (
                <div key={p.provider} className="flex items-center gap-2">
                  <div
                    className="size-3 rounded-full"
                    style={{ backgroundColor: p.color }}
                  />
                  <span className="font-mono text-sm text-muted-foreground">
                    {p.provider}
                  </span>
                  <span className="ml-auto font-mono text-sm font-medium text-foreground">
                    {formatCurrency(p.cost)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Daily Spend Trend (area chart, spans 2 cols on xl) */}
      <Card className="xl:col-span-2">
        <CardHeader className="border-b">
          <CardTitle className="text-muted-foreground">
            Daily Spend (30d)
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={DAILY_COSTS}
                margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
              >
                <defs>
                  <linearGradient
                    id="dailySpendGrad"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="0%"
                      stopColor="#00FF88"
                      stopOpacity={0.25}
                    />
                    <stop
                      offset="100%"
                      stopColor="#00FF88"
                      stopOpacity={0.02}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(255,255,255,0.05)"
                  vertical={false}
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val: string) => {
                    const d = new Date(val)
                    return `${d.getMonth() + 1}/${d.getDate()}`
                  }}
                  interval={6}
                />
                <YAxis
                  tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val: number) => `$${val}`}
                />
                <RechartsTooltip content={<DailySpendTooltip />} />
                <Area
                  type="monotone"
                  dataKey="total"
                  stroke="#00FF88"
                  strokeWidth={2}
                  fill="url(#dailySpendGrad)"
                  dot={false}
                  activeDot={{
                    r: 4,
                    fill: "#00FF88",
                    stroke: "rgba(10,10,15,0.8)",
                    strokeWidth: 2,
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Top 5 Most Expensive Services (horizontal bar chart, spans full width) */}
      <Card className="md:col-span-2 xl:col-span-4">
        <CardHeader className="border-b">
          <CardTitle className="text-muted-foreground">
            Top 5 Services by Cost
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={TOP_SERVICES}
                layout="vertical"
                margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(255,255,255,0.05)"
                  horizontal={false}
                />
                <XAxis
                  type="number"
                  tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val: number) => `$${val}`}
                />
                <YAxis
                  type="category"
                  dataKey="service"
                  tick={{ fontSize: 11, fill: "rgba(255,255,255,0.7)" }}
                  tickLine={false}
                  axisLine={false}
                  width={60}
                />
                <RechartsTooltip content={<TopServiceTooltip />} />
                <Bar dataKey="cost" radius={[0, 4, 4, 0]} barSize={20}>
                  {TOP_SERVICES.map((entry) => (
                    <Cell key={entry.service} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
