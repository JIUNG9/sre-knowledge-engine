export type SliType = "availability" | "latency" | "error_rate" | "throughput"
export type SloWindow = "7d" | "30d" | "90d" | "365d"
export type SloStatus = "meeting" | "at_risk" | "breaching"
export type BurnRate = "normal" | "fast_burn" | "exhausted"

export interface ErrorBudgetPoint {
  date: string
  remaining: number // percentage 0-100
  burnRate: number
}

export interface SliMeasurement {
  date: string
  value: number
}

export interface EventAnnotation {
  date: string
  type: "deployment" | "incident"
  label: string
}

export interface SloDefinition {
  id: string
  name: string
  service: string
  target: number // e.g. 99.9
  current: number // e.g. 99.92
  sliType: SliType
  window: SloWindow
  status: SloStatus
  burnRate: BurnRate
  errorBudgetRemaining: number // percentage 0-100
  description: string
  errorBudgetData: ErrorBudgetPoint[]
  sliHistory: SliMeasurement[]
  events: EventAnnotation[]
}

// Helper to generate daily date strings for the last N days
function generateDates(days: number): string[] {
  const dates: string[] = []
  const now = new Date()
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    dates.push(d.toISOString().split("T")[0])
  }
  return dates
}

// Generate error budget data with a specific trajectory
function generateErrorBudget(
  days: number,
  startRemaining: number,
  endRemaining: number,
  volatility: number = 2
): ErrorBudgetPoint[] {
  const dates = generateDates(days)
  const step = (endRemaining - startRemaining) / (days - 1)
  return dates.map((date, i) => {
    const base = startRemaining + step * i
    const jitter = (Math.sin(i * 0.7) + Math.cos(i * 1.3)) * volatility
    const remaining = Math.max(0, Math.min(100, base + jitter))
    const burnRate = remaining < 25 ? 3.2 : remaining < 50 ? 1.8 : 0.6
    return { date, remaining: Math.round(remaining * 100) / 100, burnRate }
  })
}

// Generate SLI measurement history
function generateSliHistory(
  days: number,
  baseline: number,
  variance: number
): SliMeasurement[] {
  const dates = generateDates(days)
  return dates.map((date, i) => {
    const jitter = (Math.sin(i * 1.1) + Math.cos(i * 0.9)) * variance
    return {
      date,
      value: Math.round((baseline + jitter) * 1000) / 1000,
    }
  })
}

export const MOCK_SLOS: SloDefinition[] = [
  // api-gateway: availability 99.9% (30d) - meeting
  {
    id: "slo-001",
    name: "API Gateway Availability",
    service: "api-gateway",
    target: 99.9,
    current: 99.95,
    sliType: "availability",
    window: "30d",
    status: "meeting",
    burnRate: "normal",
    errorBudgetRemaining: 72,
    description:
      "Percentage of successful HTTP responses (non-5xx) across all API gateway endpoints.",
    errorBudgetData: generateErrorBudget(30, 100, 72, 1.5),
    sliHistory: generateSliHistory(30, 99.95, 0.03),
    events: [
      { date: generateDates(30)[5], type: "deployment", label: "v2.14.0" },
      { date: generateDates(30)[18], type: "deployment", label: "v2.14.1" },
    ],
  },

  // api-gateway: latency p99 < 200ms (30d) - meeting
  {
    id: "slo-002",
    name: "API Gateway Latency P99",
    service: "api-gateway",
    target: 200,
    current: 145,
    sliType: "latency",
    window: "30d",
    status: "meeting",
    burnRate: "normal",
    errorBudgetRemaining: 85,
    description:
      "99th percentile response latency for API gateway requests must be under 200ms.",
    errorBudgetData: generateErrorBudget(30, 100, 85, 2),
    sliHistory: generateSliHistory(30, 145, 15),
    events: [
      { date: generateDates(30)[10], type: "deployment", label: "v2.14.0" },
    ],
  },

  // auth-service: availability 99.95% (30d) - at_risk
  {
    id: "slo-003",
    name: "Auth Service Availability",
    service: "auth-service",
    target: 99.95,
    current: 99.91,
    sliType: "availability",
    window: "30d",
    status: "at_risk",
    burnRate: "fast_burn",
    errorBudgetRemaining: 32,
    description:
      "Percentage of successful authentication and token refresh requests.",
    errorBudgetData: generateErrorBudget(30, 100, 32, 3),
    sliHistory: generateSliHistory(30, 99.91, 0.04),
    events: [
      { date: generateDates(30)[8], type: "deployment", label: "v1.8.3" },
      {
        date: generateDates(30)[15],
        type: "incident",
        label: "INC-1234: Token refresh failures",
      },
      { date: generateDates(30)[22], type: "deployment", label: "v1.8.4 hotfix" },
    ],
  },

  // auth-service: error rate < 0.1% (7d) - breaching
  {
    id: "slo-004",
    name: "Auth Service Error Rate",
    service: "auth-service",
    target: 0.1,
    current: 0.18,
    sliType: "error_rate",
    window: "7d",
    status: "breaching",
    burnRate: "exhausted",
    errorBudgetRemaining: 0,
    description:
      "Percentage of 5xx errors on authentication endpoints must stay below 0.1%.",
    errorBudgetData: generateErrorBudget(7, 45, 0, 4),
    sliHistory: generateSliHistory(7, 0.18, 0.05),
    events: [
      {
        date: generateDates(7)[2],
        type: "incident",
        label: "INC-1234: Token refresh failures",
      },
      { date: generateDates(7)[5], type: "deployment", label: "v1.8.4 hotfix" },
    ],
  },

  // payment-service: availability 99.99% (30d) - meeting
  {
    id: "slo-005",
    name: "Payment Service Availability",
    service: "payment-service",
    target: 99.99,
    current: 99.995,
    sliType: "availability",
    window: "30d",
    status: "meeting",
    burnRate: "normal",
    errorBudgetRemaining: 91,
    description:
      "Percentage of successful payment processing transactions. Critical SLO for revenue.",
    errorBudgetData: generateErrorBudget(30, 100, 91, 0.5),
    sliHistory: generateSliHistory(30, 99.995, 0.002),
    events: [
      { date: generateDates(30)[12], type: "deployment", label: "v3.2.0" },
      { date: generateDates(30)[25], type: "deployment", label: "v3.2.1" },
    ],
  },

  // payment-service: latency p99 < 500ms (30d) - meeting
  {
    id: "slo-006",
    name: "Payment Service Latency P99",
    service: "payment-service",
    target: 500,
    current: 320,
    sliType: "latency",
    window: "30d",
    status: "meeting",
    burnRate: "normal",
    errorBudgetRemaining: 68,
    description:
      "99th percentile response latency for payment processing must be under 500ms.",
    errorBudgetData: generateErrorBudget(30, 100, 68, 3),
    sliHistory: generateSliHistory(30, 320, 40),
    events: [
      { date: generateDates(30)[12], type: "deployment", label: "v3.2.0" },
    ],
  },

  // user-service: availability 99.9% (30d) - meeting
  {
    id: "slo-007",
    name: "User Service Availability",
    service: "user-service",
    target: 99.9,
    current: 99.93,
    sliType: "availability",
    window: "30d",
    status: "meeting",
    burnRate: "normal",
    errorBudgetRemaining: 58,
    description:
      "Percentage of successful user CRUD and profile lookup requests.",
    errorBudgetData: generateErrorBudget(30, 100, 58, 2),
    sliHistory: generateSliHistory(30, 99.93, 0.04),
    events: [
      { date: generateDates(30)[7], type: "deployment", label: "v1.12.0" },
      { date: generateDates(30)[20], type: "deployment", label: "v1.12.1" },
    ],
  },

  // notification-service: availability 99.5% (30d) - breaching
  {
    id: "slo-008",
    name: "Notification Service Availability",
    service: "notification-service",
    target: 99.5,
    current: 98.2,
    sliType: "availability",
    window: "30d",
    status: "breaching",
    burnRate: "exhausted",
    errorBudgetRemaining: 0,
    description:
      "Percentage of successfully delivered notifications (push, email, SMS).",
    errorBudgetData: generateErrorBudget(30, 80, 0, 5),
    sliHistory: generateSliHistory(30, 98.2, 0.8),
    events: [
      { date: generateDates(30)[4], type: "deployment", label: "v0.9.5" },
      {
        date: generateDates(30)[10],
        type: "incident",
        label: "INC-1198: Queue backpressure",
      },
      {
        date: generateDates(30)[18],
        type: "incident",
        label: "INC-1210: Provider outage",
      },
      { date: generateDates(30)[24], type: "deployment", label: "v0.9.6" },
    ],
  },

  // notification-service: throughput > 1000 msg/s (7d) - at_risk
  {
    id: "slo-009",
    name: "Notification Throughput",
    service: "notification-service",
    target: 1000,
    current: 870,
    sliType: "throughput",
    window: "7d",
    status: "at_risk",
    burnRate: "fast_burn",
    errorBudgetRemaining: 18,
    description:
      "Sustained message throughput must exceed 1000 messages per second.",
    errorBudgetData: generateErrorBudget(7, 60, 18, 4),
    sliHistory: generateSliHistory(7, 870, 80),
    events: [
      {
        date: generateDates(7)[1],
        type: "incident",
        label: "INC-1210: Provider outage",
      },
      { date: generateDates(7)[5], type: "deployment", label: "v0.9.6" },
    ],
  },

  // deployment-controller: availability 99.9% (30d) - meeting
  {
    id: "slo-010",
    name: "Deployment Controller Availability",
    service: "deployment-controller",
    target: 99.9,
    current: 99.98,
    sliType: "availability",
    window: "30d",
    status: "meeting",
    burnRate: "normal",
    errorBudgetRemaining: 95,
    description:
      "Percentage of successful deployment pipeline executions and rollout operations.",
    errorBudgetData: generateErrorBudget(30, 100, 95, 0.8),
    sliHistory: generateSliHistory(30, 99.98, 0.01),
    events: [
      { date: generateDates(30)[15], type: "deployment", label: "v2.0.0" },
    ],
  },
]

export function getSloById(id: string): SloDefinition | undefined {
  return MOCK_SLOS.find((slo) => slo.id === id)
}

export function getSlosByService(service: string): SloDefinition[] {
  return MOCK_SLOS.filter((slo) => slo.service === service)
}

export function getSlosByStatus(status: SloStatus): SloDefinition[] {
  return MOCK_SLOS.filter((slo) => slo.status === status)
}

export function getSlosByWindow(window: SloWindow): SloDefinition[] {
  return MOCK_SLOS.filter((slo) => slo.window === window)
}

export function getSlosBySliType(type: SliType): SloDefinition[] {
  return MOCK_SLOS.filter((slo) => slo.sliType === type)
}
