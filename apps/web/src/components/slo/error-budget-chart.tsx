"use client"

import * as React from "react"
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts"
import type { ErrorBudgetPoint, EventAnnotation } from "@/lib/mock-data/slo"

interface ErrorBudgetChartProps {
  data: ErrorBudgetPoint[]
  events?: EventAnnotation[]
  height?: number
}

function getGradientColor(remaining: number): string {
  if (remaining > 50) return "#00FF88"
  if (remaining > 25) return "#FFB020"
  return "#FF4444"
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{
    value: number
    payload: ErrorBudgetPoint
  }>
  label?: string
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null

  const point = payload[0]
  const remaining = point.value
  const color = getGradientColor(remaining)

  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-mono text-muted-foreground">{label}</p>
      <p className="font-mono font-medium" style={{ color }}>
        {remaining.toFixed(2)}% remaining
      </p>
      <p className="font-mono text-muted-foreground">
        Burn rate: {point.payload.burnRate.toFixed(1)}x
      </p>
    </div>
  )
}

export function ErrorBudgetChart({
  data,
  events = [],
  height = 200,
}: ErrorBudgetChartProps) {
  // Determine final color state for gradient
  const lastPoint = data[data.length - 1]
  const endColor = lastPoint ? getGradientColor(lastPoint.remaining) : "#00FF88"

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 8, right: 8, left: -20, bottom: 0 }}
        >
          <defs>
            <linearGradient
              id="errorBudgetGradient"
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" stopColor={endColor} stopOpacity={0.3} />
              <stop offset="100%" stopColor={endColor} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.05)"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(val: string) => {
              const d = new Date(val)
              return `${d.getMonth() + 1}/${d.getDate()}`
            }}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(val: number) => `${val}%`}
          />
          <RechartsTooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={0}
            stroke="#FF4444"
            strokeDasharray="4 4"
            strokeOpacity={0.6}
            label={{
              value: "Budget Exhausted",
              position: "insideTopRight",
              fontSize: 9,
              fill: "#FF4444",
            }}
          />
          <ReferenceLine
            y={25}
            stroke="#FFB020"
            strokeDasharray="2 4"
            strokeOpacity={0.3}
          />
          <ReferenceLine
            y={50}
            stroke="#00FF88"
            strokeDasharray="2 4"
            strokeOpacity={0.2}
          />
          {events.map((event, i) => (
            <ReferenceLine
              key={`event-${i}`}
              x={event.date}
              stroke={
                event.type === "incident"
                  ? "rgba(255,68,68,0.5)"
                  : "rgba(0,255,136,0.3)"
              }
              strokeDasharray="2 2"
              label={{
                value: event.type === "incident" ? "!" : "D",
                position: "top",
                fontSize: 9,
                fill:
                  event.type === "incident"
                    ? "rgba(255,68,68,0.7)"
                    : "rgba(0,255,136,0.5)",
              }}
            />
          ))}
          <Area
            type="monotone"
            dataKey="remaining"
            stroke={endColor}
            strokeWidth={2}
            fill="url(#errorBudgetGradient)"
            dot={false}
            activeDot={{
              r: 4,
              fill: endColor,
              stroke: "rgba(10,10,15,0.8)",
              strokeWidth: 2,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// Smaller sparkline version for use in cards
interface ErrorBudgetSparklineProps {
  data: ErrorBudgetPoint[]
  height?: number
}

export function ErrorBudgetSparkline({
  data,
  height = 40,
}: ErrorBudgetSparklineProps) {
  const lastPoint = data[data.length - 1]
  const color = lastPoint ? getGradientColor(lastPoint.remaining) : "#00FF88"

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
          <defs>
            <linearGradient
              id={`sparkGrad-${color.replace("#", "")}`}
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="0%" stopColor={color} stopOpacity={0.2} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="remaining"
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
