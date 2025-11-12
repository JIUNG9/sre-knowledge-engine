export type ServiceStatus = "healthy" | "degraded" | "down"

export interface Service {
  id: string
  name: string
  status: ServiceStatus
  team: string
  repository: string
  dependencies: string[]
  sloCount: number
  slosMeeting: number
  slosBreaching: number
  healthTrend: number[] // 7-day health score 0-100
}

export const SERVICES: Service[] = [
  {
    id: "svc-001",
    name: "api-gateway",
    status: "healthy",
    team: "Platform",
    repository: "github.com/aegis/api-gateway",
    dependencies: ["auth-service", "user-service", "payment-service"],
    sloCount: 2,
    slosMeeting: 2,
    slosBreaching: 0,
    healthTrend: [98, 99, 97, 99, 100, 99, 99],
  },
  {
    id: "svc-002",
    name: "auth-service",
    status: "degraded",
    team: "Security",
    repository: "github.com/aegis/auth-service",
    dependencies: ["user-service"],
    sloCount: 2,
    slosMeeting: 1,
    slosBreaching: 1,
    healthTrend: [99, 98, 95, 92, 88, 85, 82],
  },
  {
    id: "svc-003",
    name: "payment-service",
    status: "healthy",
    team: "Commerce",
    repository: "github.com/aegis/payment-service",
    dependencies: ["auth-service", "notification-service"],
    sloCount: 2,
    slosMeeting: 2,
    slosBreaching: 0,
    healthTrend: [100, 100, 99, 100, 100, 99, 100],
  },
  {
    id: "svc-004",
    name: "user-service",
    status: "healthy",
    team: "Platform",
    repository: "github.com/aegis/user-service",
    dependencies: [],
    sloCount: 1,
    slosMeeting: 1,
    slosBreaching: 0,
    healthTrend: [97, 98, 99, 98, 99, 99, 98],
  },
  {
    id: "svc-005",
    name: "notification-service",
    status: "down",
    team: "Messaging",
    repository: "github.com/aegis/notification-service",
    dependencies: [],
    sloCount: 2,
    slosMeeting: 0,
    slosBreaching: 2,
    healthTrend: [95, 90, 78, 65, 45, 30, 20],
  },
  {
    id: "svc-006",
    name: "deployment-controller",
    status: "healthy",
    team: "Platform",
    repository: "github.com/aegis/deployment-controller",
    dependencies: ["config-service"],
    sloCount: 1,
    slosMeeting: 1,
    slosBreaching: 0,
    healthTrend: [100, 100, 100, 99, 100, 100, 100],
  },
]

export function getServiceByName(name: string): Service | undefined {
  return SERVICES.find((s) => s.name === name)
}
