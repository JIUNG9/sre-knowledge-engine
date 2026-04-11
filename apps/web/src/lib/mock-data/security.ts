// ---- Types ----

export type VulnerabilitySeverity = "critical" | "high" | "medium" | "low";

export interface Vulnerability {
  id: string;
  title: string;
  severity: VulnerabilitySeverity;
  package: string;
  version: string;
  fixedVersion: string;
  service: string;
  scanner: string;
  detectedAt: string;
}

export interface ComplianceCheck {
  id: string;
  name: string;
  status: "pass" | "fail" | "warn";
  category: string;
  notes: string;
}

export interface SeverityOverride {
  id: string;
  cveId: string;
  originalSeverity: VulnerabilitySeverity;
  newSeverity: VulnerabilitySeverity;
  justification: string;
  expiryDate?: string;
  createdAt: string;
}

export type LogSourceType =
  | "SigNoz"
  | "Datadog"
  | "Splunk"
  | "CloudWatch"
  | "Custom";

export type LogSourceStatus = "connected" | "disconnected" | "error";

export interface LogSource {
  id: string;
  name: string;
  type: LogSourceType;
  endpoint: string;
  status: LogSourceStatus;
  lastSeen?: string;
}

// ---- Severity colors ----

export const SEVERITY_COLORS: Record<string, string> = {
  critical: "text-red-400 bg-red-400/10 border-red-400/30",
  high: "text-orange-400 bg-orange-400/10 border-orange-400/30",
  medium: "text-amber-400 bg-amber-400/10 border-amber-400/30",
  low: "text-blue-400 bg-blue-400/10 border-blue-400/30",
};

// ---- Vulnerabilities ----

export const VULNERABILITIES: Vulnerability[] = [
  {
    id: "CVE-2025-1234",
    title: "OpenSSL buffer overflow in libcrypto",
    severity: "critical",
    package: "openssl",
    version: "3.0.12",
    fixedVersion: "3.0.13",
    service: "api-gateway",
    scanner: "trivy",
    detectedAt: "2026-02-28T10:00:00Z",
  },
  {
    id: "CVE-2025-5678",
    title: "Go net/http request smuggling",
    severity: "high",
    package: "golang.org/x/net",
    version: "0.19.0",
    fixedVersion: "0.20.0",
    service: "api-gateway",
    scanner: "trivy",
    detectedAt: "2026-03-01T08:00:00Z",
  },
  {
    id: "CVE-2025-9012",
    title: "Python Pillow heap overflow",
    severity: "high",
    package: "Pillow",
    version: "10.1.0",
    fixedVersion: "10.2.0",
    service: "ai-engine",
    scanner: "snyk",
    detectedAt: "2026-03-02T14:00:00Z",
  },
  {
    id: "CVE-2025-3456",
    title: "Node.js path traversal in undici",
    severity: "medium",
    package: "undici",
    version: "5.26.0",
    fixedVersion: "5.27.0",
    service: "web",
    scanner: "trivy",
    detectedAt: "2026-03-03T09:00:00Z",
  },
  {
    id: "CVE-2025-7890",
    title: "Redis Lua sandbox escape",
    severity: "medium",
    package: "redis",
    version: "7.2.3",
    fixedVersion: "7.2.4",
    service: "infrastructure",
    scanner: "grype",
    detectedAt: "2026-03-04T11:00:00Z",
  },
  {
    id: "CVE-2025-2345",
    title: "PostgreSQL privilege escalation",
    severity: "low",
    package: "postgresql",
    version: "16.1",
    fixedVersion: "16.2",
    service: "infrastructure",
    scanner: "trivy",
    detectedAt: "2026-03-05T16:00:00Z",
  },
];

// ---- Compliance checks ----

export const COMPLIANCE_CHECKS: ComplianceCheck[] = [
  { id: "cc-001", name: "Container images scanned", status: "pass", category: "CIS", notes: "" },
  { id: "cc-002", name: "No root containers running", status: "pass", category: "CIS", notes: "" },
  { id: "cc-003", name: "Secrets not in environment vars", status: "fail", category: "SOC2", notes: "3 services still using env-based secrets" },
  { id: "cc-004", name: "TLS 1.2+ enforced", status: "pass", category: "SOC2", notes: "" },
  { id: "cc-005", name: "RBAC enforced on all endpoints", status: "pass", category: "ISO27001", notes: "" },
  { id: "cc-006", name: "Audit logging enabled", status: "pass", category: "ISO27001", notes: "" },
  { id: "cc-007", name: "Dependency audit < 30 days", status: "warn", category: "CIS", notes: "Last audit 28 days ago" },
  { id: "cc-008", name: "Network policies defined", status: "pass", category: "CIS", notes: "" },
];

// ---- Severity overrides (initially empty) ----

export const SEVERITY_OVERRIDES: SeverityOverride[] = [];

// ---- Log sources ----

export const LOG_SOURCES: LogSource[] = [
  {
    id: "ls-001",
    name: "SigNoz Production",
    type: "SigNoz",
    endpoint: "https://signoz.aegis.internal:4317",
    status: "connected",
    lastSeen: "2026-04-10T08:30:00Z",
  },
  {
    id: "ls-002",
    name: "Datadog US-East",
    type: "Datadog",
    endpoint: "https://api.datadoghq.com/api/v2/logs",
    status: "disconnected",
  },
];

// ---- CIS / SOC2 templates ----

export const CIS_TEMPLATE: Omit<ComplianceCheck, "id">[] = [
  { name: "Container images scanned", status: "pass", category: "CIS", notes: "" },
  { name: "No root containers running", status: "pass", category: "CIS", notes: "" },
  { name: "Dependency audit < 30 days", status: "warn", category: "CIS", notes: "" },
  { name: "Network policies defined", status: "pass", category: "CIS", notes: "" },
  { name: "Pod security standards enforced", status: "pass", category: "CIS", notes: "" },
  { name: "Ingress TLS termination configured", status: "pass", category: "CIS", notes: "" },
];

export const SOC2_TEMPLATE: Omit<ComplianceCheck, "id">[] = [
  { name: "Secrets not in environment vars", status: "fail", category: "SOC2", notes: "" },
  { name: "TLS 1.2+ enforced", status: "pass", category: "SOC2", notes: "" },
  { name: "Access logs retained 90 days", status: "pass", category: "SOC2", notes: "" },
  { name: "MFA enforced for all users", status: "pass", category: "SOC2", notes: "" },
  { name: "Data encryption at rest", status: "pass", category: "SOC2", notes: "" },
  { name: "Incident response plan documented", status: "pass", category: "SOC2", notes: "" },
];
