export interface SavedQuery {
  id: string
  name: string
  description: string
  filters: {
    levels?: string[]
    services?: string[]
    search?: string
    timeRange?: string
    security?: boolean
  }
  icon: "clock" | "shield" | "search" | "zap" | "server"
}

export const SAVED_QUERIES: SavedQuery[] = [
  {
    id: "sq-001",
    name: "Production Errors (last 1h)",
    description: "All ERROR and FATAL level logs from the past hour",
    filters: {
      levels: ["ERROR", "FATAL"],
      timeRange: "1h",
    },
    icon: "clock",
  },
  {
    id: "sq-002",
    name: "Auth Failures",
    description: "Login failures, locked accounts, and authentication errors",
    filters: {
      search: "failed login|auth|login failed|account locked|brute force",
      security: true,
    },
    icon: "shield",
  },
  {
    id: "sq-003",
    name: "Slow Queries (>1s)",
    description: "Database queries exceeding 1 second threshold",
    filters: {
      search: "slow query|Slow query",
    },
    icon: "zap",
  },
  {
    id: "sq-004",
    name: "Deployment Events",
    description: "All events from the deployment controller service",
    filters: {
      services: ["deployment-controller"],
    },
    icon: "server",
  },
  {
    id: "sq-005",
    name: "Security Alerts",
    description: "All security-tagged events: auth failures, privilege escalation, CVEs",
    filters: {
      security: true,
    },
    icon: "shield",
  },
]
