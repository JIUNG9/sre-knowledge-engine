// FinOps Mock Data
// ============================================================================

export type Provider = "AWS" | "GCP" | "Azure"
export type AnomalySeverity = "high" | "medium" | "low"
export type Granularity = "daily" | "weekly" | "monthly"

// --- Daily cost data ---

export interface DailyCostPoint {
  date: string
  ec2: number
  rds: number
  s3: number
  eks: number
  lambda: number
  total: number
}

export interface ProviderCost {
  provider: Provider
  cost: number
  color: string
}

export interface ServiceCostRow {
  id: string
  service: string
  team: string
  account: string
  provider: Provider
  currentMonth: number
  previousMonth: number
  changePercent: number
  trend: number[] // 7-day sparkline values
}

export interface CostAnomaly {
  id: string
  service: string
  expected: number
  actual: number
  deviation: number // percentage
  severity: AnomalySeverity
  detectedAt: string
  description: string
}

export interface TeamBudget {
  id: string
  team: string
  budget: number
  currentSpend: number
  projected: number
  usagePercent: number
  projectedPercent: number
}

export interface K8sNamespaceCost {
  namespace: string
  cost: number
  cpuRequested: number
  cpuUsed: number
  memRequested: number
  memUsed: number
  color: string
}

export interface K8sPodCost {
  id: string
  pod: string
  namespace: string
  deployment: string
  costPerDay: number
  cpuWaste: number // percentage of CPU requested but not used
  memWaste: number
}

export interface K8sRecommendation {
  id: string
  type: "downsize" | "terminate" | "right-size" | "schedule"
  resource: string
  namespace: string
  estimatedSavings: number
  description: string
}

export interface MonthlyTotalCost {
  month: string
  total: number
}

// --- Helpers ---

function generateDates(days: number): string[] {
  const dates: string[] = []
  const now = new Date(2026, 3, 10) // April 10, 2026
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    dates.push(d.toISOString().split("T")[0])
  }
  return dates
}

function jitter(base: number, range: number): number {
  return Math.round((base + (Math.random() - 0.5) * 2 * range) * 100) / 100
}

// --- 30 days of daily cost data for 5 AWS services ---

const dates30 = generateDates(30)

export const DAILY_COSTS: DailyCostPoint[] = dates30.map((date, i) => {
  // EC2: base ~$180/day, spike on day 22
  const ec2 = i === 22 ? 412.5 : jitter(180, 20)
  // RDS: base ~$95/day, steady
  const rds = jitter(95, 8)
  // S3: base ~$45/day, spike on day 25-27
  const s3 = i >= 25 && i <= 27 ? jitter(98, 10) : jitter(45, 6)
  // EKS: base ~$65/day
  const eks = jitter(65, 10)
  // Lambda: base ~$28/day
  const lambda = jitter(28, 5)
  const total = Math.round((ec2 + rds + s3 + eks + lambda) * 100) / 100

  return { date, ec2, rds, s3, eks, lambda, total }
})

// --- Previous month data (for comparison) ---

const prevDates = (() => {
  const dates: string[] = []
  const start = new Date(2026, 2, 11) // March 11
  for (let i = 0; i < 30; i++) {
    const d = new Date(start)
    d.setDate(d.getDate() + i)
    dates.push(d.toISOString().split("T")[0])
  }
  return dates
})()

export const PREV_MONTH_DAILY_COSTS: DailyCostPoint[] = prevDates.map(
  (date) => {
    const ec2 = jitter(170, 18)
    const rds = jitter(90, 7)
    const s3 = jitter(42, 5)
    const eks = jitter(60, 8)
    const lambda = jitter(26, 4)
    const total = Math.round((ec2 + rds + s3 + eks + lambda) * 100) / 100
    return { date, ec2, rds, s3, eks, lambda, total }
  }
)

// --- Cost summary ---

export const TOTAL_CURRENT_MONTH = 12450
export const TOTAL_PREVIOUS_MONTH = 11890
export const MOM_CHANGE_PERCENT = 4.7

// --- Cost by provider ---

export const PROVIDER_COSTS: ProviderCost[] = [
  { provider: "AWS", cost: 10280, color: "#FF9900" },
  { provider: "GCP", cost: 1450, color: "#4285F4" },
  { provider: "Azure", cost: 720, color: "#0078D4" },
]

// --- Top 5 most expensive services ---

export interface TopService {
  service: string
  cost: number
  color: string
}

export const TOP_SERVICES: TopService[] = [
  { service: "EC2", cost: 5400, color: "#00FF88" },
  { service: "RDS", cost: 2850, color: "#00BFFF" },
  { service: "EKS", cost: 1950, color: "#A855F7" },
  { service: "S3", cost: 1350, color: "#FFB020" },
  { service: "Lambda", cost: 900, color: "#FF6B6B" },
]

// --- Service cost breakdown table ---

export const SERVICE_COSTS: ServiceCostRow[] = [
  {
    id: "svc-1",
    service: "EC2 (Compute)",
    team: "Platform",
    account: "prod-main",
    provider: "AWS",
    currentMonth: 5400,
    previousMonth: 5100,
    changePercent: 5.88,
    trend: [170, 175, 180, 182, 185, 412, 178],
  },
  {
    id: "svc-2",
    service: "RDS (Database)",
    team: "Engineering",
    account: "prod-main",
    provider: "AWS",
    currentMonth: 2850,
    previousMonth: 2780,
    changePercent: 2.52,
    trend: [90, 92, 95, 93, 96, 94, 95],
  },
  {
    id: "svc-3",
    service: "EKS (Kubernetes)",
    team: "Platform",
    account: "prod-k8s",
    provider: "AWS",
    currentMonth: 1950,
    previousMonth: 1820,
    changePercent: 7.14,
    trend: [58, 60, 62, 64, 65, 67, 68],
  },
  {
    id: "svc-4",
    service: "S3 (Storage)",
    team: "Data",
    account: "prod-data",
    provider: "AWS",
    currentMonth: 1350,
    previousMonth: 1260,
    changePercent: 7.14,
    trend: [40, 42, 43, 44, 98, 96, 45],
  },
  {
    id: "svc-5",
    service: "Lambda (Compute)",
    team: "Engineering",
    account: "prod-main",
    provider: "AWS",
    currentMonth: 900,
    previousMonth: 930,
    changePercent: -3.23,
    trend: [30, 29, 28, 28, 27, 28, 27],
  },
  {
    id: "svc-6",
    service: "CloudFront (CDN)",
    team: "Engineering",
    account: "prod-main",
    provider: "AWS",
    currentMonth: 480,
    previousMonth: 520,
    changePercent: -7.69,
    trend: [18, 17, 16, 15, 16, 15, 15],
  },
  {
    id: "svc-7",
    service: "GKE (Kubernetes)",
    team: "Platform",
    account: "gcp-prod",
    provider: "GCP",
    currentMonth: 980,
    previousMonth: 890,
    changePercent: 10.11,
    trend: [28, 30, 31, 32, 33, 34, 35],
  },
  {
    id: "svc-8",
    service: "BigQuery",
    team: "Data",
    account: "gcp-analytics",
    provider: "GCP",
    currentMonth: 470,
    previousMonth: 510,
    changePercent: -7.84,
    trend: [18, 17, 16, 15, 15, 14, 15],
  },
  {
    id: "svc-9",
    service: "Azure AKS",
    team: "Security",
    account: "azure-sec",
    provider: "Azure",
    currentMonth: 420,
    previousMonth: 380,
    changePercent: 10.53,
    trend: [12, 13, 13, 14, 14, 15, 15],
  },
  {
    id: "svc-10",
    service: "Azure Blob Storage",
    team: "Security",
    account: "azure-sec",
    provider: "Azure",
    currentMonth: 300,
    previousMonth: 320,
    changePercent: -6.25,
    trend: [11, 11, 10, 10, 10, 9, 10],
  },
]

// --- Cost anomalies ---

export const COST_ANOMALIES: CostAnomaly[] = [
  {
    id: "anomaly-1",
    service: "EC2 (Compute)",
    expected: 180,
    actual: 412.5,
    deviation: 129.2,
    severity: "high",
    detectedAt: "2026-04-02T14:23:00Z",
    description:
      "Unexpected EC2 spike detected. Auto-scaling group launched 12 additional c5.2xlarge instances due to a misconfigured health check threshold.",
  },
  {
    id: "anomaly-2",
    service: "S3 (Storage)",
    expected: 45,
    actual: 98,
    deviation: 117.8,
    severity: "medium",
    detectedAt: "2026-04-05T09:15:00Z",
    description:
      "S3 cost increase correlated with a CI/CD pipeline storing build artifacts without lifecycle policies. Estimated 2.1TB of orphaned objects.",
  },
]

// --- Team budgets ---

export const TEAM_BUDGETS: TeamBudget[] = [
  {
    id: "budget-1",
    team: "Engineering",
    budget: 5000,
    currentSpend: 3900,
    projected: 5850,
    usagePercent: 78,
    projectedPercent: 117,
  },
  {
    id: "budget-2",
    team: "Platform",
    budget: 8000,
    currentSpend: 3600,
    projected: 5400,
    usagePercent: 45,
    projectedPercent: 67.5,
  },
  {
    id: "budget-3",
    team: "Data",
    budget: 2000,
    currentSpend: 1840,
    projected: 2760,
    usagePercent: 92,
    projectedPercent: 138,
  },
  {
    id: "budget-4",
    team: "Security",
    budget: 2500,
    currentSpend: 875,
    projected: 1312,
    usagePercent: 35,
    projectedPercent: 52.5,
  },
]

// --- Kubernetes cost allocation ---

export const K8S_NAMESPACE_COSTS: K8sNamespaceCost[] = [
  {
    namespace: "production",
    cost: 1250,
    cpuRequested: 48,
    cpuUsed: 31,
    memRequested: 128,
    memUsed: 89,
    color: "#00FF88",
  },
  {
    namespace: "staging",
    cost: 420,
    cpuRequested: 24,
    cpuUsed: 8,
    memRequested: 64,
    memUsed: 18,
    color: "#00BFFF",
  },
  {
    namespace: "monitoring",
    cost: 310,
    cpuRequested: 16,
    cpuUsed: 12,
    memRequested: 48,
    memUsed: 38,
    color: "#A855F7",
  },
  {
    namespace: "ci-cd",
    cost: 180,
    cpuRequested: 12,
    cpuUsed: 4,
    memRequested: 32,
    memUsed: 10,
    color: "#FFB020",
  },
]

export const K8S_POD_COSTS: K8sPodCost[] = [
  {
    id: "pod-1",
    pod: "api-gateway-7d8f9",
    namespace: "production",
    deployment: "api-gateway",
    costPerDay: 18.5,
    cpuWaste: 22,
    memWaste: 15,
  },
  {
    id: "pod-2",
    pod: "auth-service-4c2a1",
    namespace: "production",
    deployment: "auth-service",
    costPerDay: 12.3,
    cpuWaste: 35,
    memWaste: 28,
  },
  {
    id: "pod-3",
    pod: "user-service-9b7e3",
    namespace: "production",
    deployment: "user-service",
    costPerDay: 14.8,
    cpuWaste: 18,
    memWaste: 12,
  },
  {
    id: "pod-4",
    pod: "sse-broker-2f5d8",
    namespace: "production",
    deployment: "sse-broker",
    costPerDay: 22.1,
    cpuWaste: 42,
    memWaste: 55,
  },
  {
    id: "pod-5",
    pod: "prometheus-0",
    namespace: "monitoring",
    deployment: "prometheus",
    costPerDay: 8.9,
    cpuWaste: 15,
    memWaste: 8,
  },
  {
    id: "pod-6",
    pod: "grafana-6a3b2",
    namespace: "monitoring",
    deployment: "grafana",
    costPerDay: 4.2,
    cpuWaste: 60,
    memWaste: 45,
  },
  {
    id: "pod-7",
    pod: "staging-api-1d9f4",
    namespace: "staging",
    deployment: "staging-api",
    costPerDay: 9.5,
    cpuWaste: 68,
    memWaste: 72,
  },
  {
    id: "pod-8",
    pod: "runner-arc-5e8c1",
    namespace: "ci-cd",
    deployment: "arc-runner",
    costPerDay: 6.0,
    cpuWaste: 75,
    memWaste: 80,
  },
]

export const K8S_RECOMMENDATIONS: K8sRecommendation[] = [
  {
    id: "rec-1",
    type: "right-size",
    resource: "sse-broker",
    namespace: "production",
    estimatedSavings: 280,
    description:
      "sse-broker pods request 4 CPU cores but average usage is 2.3 cores. Reduce requests to 2.5 cores.",
  },
  {
    id: "rec-2",
    type: "schedule",
    resource: "staging-api",
    namespace: "staging",
    estimatedSavings: 195,
    description:
      "Staging environment runs 24/7 but is only used during business hours (09:00-18:00 KST). Schedule scale-down.",
  },
  {
    id: "rec-3",
    type: "terminate",
    resource: "grafana (idle replica)",
    namespace: "monitoring",
    estimatedSavings: 85,
    description:
      "Second Grafana replica has zero requests in the last 14 days. Remove idle replica.",
  },
  {
    id: "rec-4",
    type: "downsize",
    resource: "arc-runner",
    namespace: "ci-cd",
    estimatedSavings: 120,
    description:
      "CI/CD runners request 4GB memory but peak usage is 1.2GB. Reduce memory request to 2GB.",
  },
]

// --- Monthly totals (for quarter-over-quarter) ---

export const MONTHLY_TOTALS: MonthlyTotalCost[] = [
  { month: "2025-11", total: 10200 },
  { month: "2025-12", total: 10850 },
  { month: "2026-01", total: 11200 },
  { month: "2026-02", total: 11450 },
  { month: "2026-03", total: 11890 },
  { month: "2026-04", total: 12450 },
]
