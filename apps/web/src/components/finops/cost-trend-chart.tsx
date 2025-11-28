"use client"

import * as React from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { TrendingUp } from "lucide-react"
import {
  DAILY_COSTS,
  PREV_MONTH_DAILY_COSTS,
  MONTHLY_TOTALS,
  type DailyCostPoint,
  type MonthlyTotalCost,
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

// Build comparison data (current vs previous day-by-day)
interface ComparisonPoint {
  day: number
  current: number
  previous: number
}

const comparisonData: ComparisonPoint[] = DAILY_COSTS.map((point, i) => ({
  day: i + 1,
  current: point.total,
  previous: PREV_MONTH_DAILY_COSTS[i]?.total ?? 0,
}))

// Build weekly aggregation from daily data
interface WeeklyPoint {
  week: string
  total: number
}

function aggregateWeekly(data: DailyCostPoint[]): WeeklyPoint[] {
  const weeks: WeeklyPoint[] = []
  for (let i = 0; i < data.length; i += 7) {
    const slice = data.slice(i, i + 7)
    const total = slice.reduce((sum, d) => sum + d.total, 0)
    weeks.push({
      week: `W${Math.floor(i / 7) + 1}`,
      total: Math.round(total),
    })
  }
  return weeks
}

const weeklyData = aggregateWeekly(DAILY_COSTS)

// --- Custom tooltips ---

interface ComparisonTooltipProps {
  active?: boolean
  payload?: Array<{ value: number; dataKey: string; color: string }>
  label?: string
}

function ComparisonTooltip({ active, payload, label }: ComparisonTooltipProps) {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-mono text-muted-foreground">Day {label}</p>
      {payload.map((entry) => (
        <p
          key={entry.dataKey}
          className="font-mono text-[11px] font-medium"
          style={{ color: entry.color }}
        >
          {entry.dataKey === "current" ? "Current" : "Previous"}:{" "}
          {formatCurrency(entry.value)}
        </p>
      ))}
    </div>
  )
}

interface GenericTooltipProps {
  active?: boolean
  payload?: Array<{ value: number }>
  label?: string
  labelPrefix?: string
}

function GenericTooltip({
  active,
  payload,
  label,
  labelPrefix = "",
}: GenericTooltipProps) {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-mono text-muted-foreground">
        {labelPrefix}
        {label}
      </p>
      <p className="font-mono font-medium text-foreground">
        {formatCurrency(payload[0].value)}
      </p>
    </div>
  )
}

// --- Main component ---

export function CostTrendChart() {
  const [granularity, setGranularity] = React.useState<"daily" | "weekly" | "monthly">(
    "daily"
  )

  return (
    <Card size="sm">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-muted-foreground">
          <TrendingUp className="size-4 text-primary" />
          Cost Trends
        </CardTitle>
        <CardAction>
          <Select
            value={granularity}
            onValueChange={(v) => {
              if (v) setGranularity(v as "daily" | "weekly" | "monthly")
            }}
          >
            <SelectTrigger size="sm" className="font-mono text-[11px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="daily">Daily</SelectItem>
              <SelectItem value="weekly">Weekly</SelectItem>
              <SelectItem value="monthly">Monthly</SelectItem>
            </SelectContent>
          </Select>
        </CardAction>
      </CardHeader>
      <CardContent className="pt-3">
        <Tabs defaultValue="comparison">
          <TabsList variant="line" className="mb-3">
            <TabsTrigger value="comparison" className="font-mono text-[11px]">
              Month vs Month
            </TabsTrigger>
            <TabsTrigger value="trend" className="font-mono text-[11px]">
              Trend
            </TabsTrigger>
          </TabsList>

          {/* Comparison: current vs previous month overlay */}
          <TabsContent value="comparison">
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={comparisonData}
                  margin={{ top: 8, right: 8, left: -10, bottom: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(255,255,255,0.05)"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="day"
                    tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }}
                    tickLine={false}
                    axisLine={false}
                    label={{
                      value: "Day of Month",
                      position: "insideBottom",
                      offset: -2,
                      fontSize: 9,
                      fill: "rgba(255,255,255,0.3)",
                    }}
                  />
                  <YAxis
                    tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val: number) => `$${val}`}
                  />
                  <RechartsTooltip content={<ComparisonTooltip />} />
                  <Legend
                    wrapperStyle={{ fontSize: 10, fontFamily: "monospace" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="current"
                    name="Current Month"
                    stroke="#00FF88"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{
                      r: 4,
                      fill: "#00FF88",
                      stroke: "rgba(10,10,15,0.8)",
                      strokeWidth: 2,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="previous"
                    name="Previous Month"
                    stroke="#00BFFF"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={false}
                    activeDot={{
                      r: 4,
                      fill: "#00BFFF",
                      stroke: "rgba(10,10,15,0.8)",
                      strokeWidth: 2,
                    }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </TabsContent>

          {/* Trend view with granularity toggle */}
          <TabsContent value="trend">
            <div className="h-[260px]">
              {granularity === "daily" && (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={DAILY_COSTS}
                    margin={{ top: 8, right: 8, left: -10, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient
                        id="trendDailyGrad"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="0%"
                          stopColor="#A855F7"
                          stopOpacity={0.25}
                        />
                        <stop
                          offset="100%"
                          stopColor="#A855F7"
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
                    <RechartsTooltip
                      content={<GenericTooltip />}
                    />
                    <Area
                      type="monotone"
                      dataKey="total"
                      stroke="#A855F7"
                      strokeWidth={2}
                      fill="url(#trendDailyGrad)"
                      dot={false}
                      activeDot={{
                        r: 4,
                        fill: "#A855F7",
                        stroke: "rgba(10,10,15,0.8)",
                        strokeWidth: 2,
                      }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}

              {granularity === "weekly" && (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={weeklyData}
                    margin={{ top: 8, right: 8, left: -10, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(255,255,255,0.05)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="week"
                      tick={{ fontSize: 10, fill: "rgba(255,255,255,0.6)" }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val: number) => `$${val}`}
                    />
                    <RechartsTooltip
                      content={<GenericTooltip labelPrefix="Week: " />}
                    />
                    <Bar
                      dataKey="total"
                      fill="#00BFFF"
                      radius={[4, 4, 0, 0]}
                      barSize={36}
                    />
                  </BarChart>
                </ResponsiveContainer>
              )}

              {granularity === "monthly" && (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={MONTHLY_TOTALS}
                    margin={{ top: 8, right: 8, left: -10, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(255,255,255,0.05)"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="month"
                      tick={{ fontSize: 10, fill: "rgba(255,255,255,0.6)" }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val: number) =>
                        `$${(val / 1000).toFixed(0)}k`
                      }
                    />
                    <RechartsTooltip content={<GenericTooltip />} />
                    <Bar
                      dataKey="total"
                      fill="#FFB020"
                      radius={[4, 4, 0, 0]}
                      barSize={36}
                    />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
