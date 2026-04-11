"use client"

import * as React from "react"
import {
  Area,
  AreaChart,
  ResponsiveContainer,
} from "recharts"
import { cn } from "@/lib/utils"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { SERVICES, type Service, type ServiceStatus } from "@/lib/mock-data/services"
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Server,
} from "lucide-react"

function getStatusConfig(status: ServiceStatus) {
  switch (status) {
    case "healthy":
      return {
        label: "Healthy",
        color: "#00FF88",
        icon: CheckCircle2,
        borderClass: "border-l-[#00FF88]/40",
      }
    case "degraded":
      return {
        label: "Degraded",
        color: "#FFB020",
        icon: AlertTriangle,
        borderClass: "border-l-[#FFB020]/40",
      }
    case "down":
      return {
        label: "Down",
        color: "#FF4444",
        icon: XCircle,
        borderClass: "border-l-[#FF4444]/40",
      }
  }
}

interface HealthSparklineProps {
  data: number[]
  color: string
}

function HealthSparkline({ data, color }: HealthSparklineProps) {
  const chartData = data.map((value, index) => ({ index, value }))

  return (
    <div className="h-8 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={chartData}
          margin={{ top: 1, right: 0, left: 0, bottom: 1 }}
        >
          <defs>
            <linearGradient
              id={`healthGrad-${color.replace("#", "")}`}
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
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#healthGrad-${color.replace("#", "")})`}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

interface ServiceHealthCardProps {
  service: Service
  isSelected: boolean
  onClick: () => void
}

function ServiceHealthCard({
  service,
  isSelected,
  onClick,
}: ServiceHealthCardProps) {
  const config = getStatusConfig(service.status)
  const StatusIcon = config.icon

  return (
    <Card
      className={cn(
        "cursor-pointer border-l-2 transition-all hover:bg-surface-hover",
        config.borderClass,
        isSelected && "ring-1 ring-primary/40 glow-matrix"
      )}
      onClick={onClick}
    >
      <CardContent className="grid gap-3 p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="size-4 text-muted-foreground" />
            <span className="font-mono text-sm font-medium text-foreground">
              {service.name}
            </span>
          </div>
          <StatusIcon className="size-4" style={{ color: config.color }} />
        </div>

        <HealthSparkline data={service.healthTrend} color={config.color} />

        <div className="flex items-center justify-between">
          <Badge
            variant="outline"
            className="px-2 py-0.5 font-mono text-xs"
            style={{
              borderColor: `${config.color}30`,
              color: config.color,
            }}
          >
            {config.label}
          </Badge>
          <div className="flex items-center gap-1 font-mono text-sm text-muted-foreground">
            <span className="text-[#00FF88]">{service.slosMeeting}</span>
            <span>/</span>
            <span>{service.sloCount}</span>
            <span>SLOs</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

interface ServiceHealthGridProps {
  selectedService: string | null
  onServiceSelect: (service: string | null) => void
}

export function ServiceHealthGrid({
  selectedService,
  onServiceSelect,
}: ServiceHealthGridProps) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      {SERVICES.map((service) => (
        <ServiceHealthCard
          key={service.id}
          service={service}
          isSelected={selectedService === service.name}
          onClick={() =>
            onServiceSelect(
              selectedService === service.name ? null : service.name
            )
          }
        />
      ))}
    </div>
  )
}
