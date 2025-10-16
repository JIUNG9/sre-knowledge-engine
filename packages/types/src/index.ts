// ─── Core Types ──────────────────────────────────────────────

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type IncidentStatus =
  | "open"
  | "investigating"
  | "identified"
  | "monitoring"
  | "resolved";

export type ServiceStatus = "healthy" | "degraded" | "down" | "unknown";

// ─── Incident ────────────────────────────────────────────────

export interface Incident {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  status: IncidentStatus;
  service: string;
  assignee?: string;
  rootCause?: string;
  remediation?: string;
  aiInvestigation?: AIInvestigation;
  createdAt: string;
  updatedAt: string;
  resolvedAt?: string;
}

export interface AIInvestigation {
  summary: string;
  rootCause: string;
  affectedServices: string[];
  proposedRemediation: string;
  confidenceScore: number;
  toolsUsed: string[];
  tokenUsage: {
    input: number;
    output: number;
    cached: number;
  };
}

// ─── Service Catalog ─────────────────────────────────────────

export interface Service {
  id: string;
  name: string;
  team: string;
  repository: string;
  description: string;
  status: ServiceStatus;
  sloTarget: number;
  sloCurrent: number;
  dependencies: string[];
  tags: string[];
}

// ─── SLO / SLI ──────────────────────────────────────────────

export type SLIType = "availability" | "latency" | "error_rate" | "throughput";
export type SLOWindow = "7d" | "30d" | "90d" | "365d";

export interface SLO {
  id: string;
  serviceId: string;
  name: string;
  target: number;
  current: number;
  window: SLOWindow;
  sliType: SLIType;
  errorBudgetTotal: number;
  errorBudgetRemaining: number;
  errorBudgetConsumedPercent: number;
  burnRate: number;
  createdAt: string;
}

// ─── Log Explorer ────────────────────────────────────────────

export type LogLevel =
  | "trace"
  | "debug"
  | "info"
  | "warn"
  | "error"
  | "fatal";

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  service: string;
  traceId?: string;
  spanId?: string;
  attributes: Record<string, string>;
}

export interface LogQuery {
  query: string;
  startTime: string;
  endTime: string;
  levels?: LogLevel[];
  services?: string[];
  limit: number;
  offset: number;
}

// ─── FinOps ──────────────────────────────────────────────────

export interface CostEntry {
  date: string;
  service: string;
  account: string;
  provider: "aws" | "gcp" | "azure";
  amount: number;
  currency: string;
  tags: Record<string, string>;
}

export interface CostSummary {
  period: string;
  totalCost: number;
  costByService: Record<string, number>;
  costByTeam: Record<string, number>;
  monthOverMonthChange: number;
  anomalies: CostAnomaly[];
}

export interface CostAnomaly {
  service: string;
  expectedCost: number;
  actualCost: number;
  deviationPercent: number;
  detectedAt: string;
}

// ─── Alerts & Webhooks ───────────────────────────────────────

export type AlertSource =
  | "signoz"
  | "datadog"
  | "prometheus"
  | "cloudwatch"
  | "custom";

export interface Alert {
  id: string;
  source: AlertSource;
  title: string;
  description: string;
  severity: Severity;
  service: string;
  status: "firing" | "resolved";
  labels: Record<string, string>;
  annotations: Record<string, string>;
  startsAt: string;
  endsAt?: string;
}

// ─── DORA Metrics ────────────────────────────────────────────

export interface DORAMetrics {
  period: string;
  deploymentFrequency: number;
  leadTimeForChanges: number; // hours
  changeFailureRate: number; // percentage
  timeToRestore: number; // hours
}

// ─── Security ────────────────────────────────────────────────

export type VulnerabilitySeverity =
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "negligible";

export interface Vulnerability {
  id: string;
  cveId: string;
  title: string;
  severity: VulnerabilitySeverity;
  package: string;
  version: string;
  fixedVersion?: string;
  service: string;
  scanner: "trivy" | "snyk" | "grype";
  detectedAt: string;
}

// ─── API Response ────────────────────────────────────────────

export interface APIResponse<T> {
  data: T;
  meta?: {
    total: number;
    page: number;
    pageSize: number;
  };
}

export interface APIError {
  error: string;
  message: string;
  statusCode: number;
}
