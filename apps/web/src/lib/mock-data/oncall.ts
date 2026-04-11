// ---- Types ----

export type MemberRole = "SRE" | "Backend" | "Platform" | "DevOps" | "Security";

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: MemberRole;
  avatarInitials: string;
  expertise: string[];
  isOnCall?: boolean;
}

export type TaskPriority = "P0" | "P1" | "P2" | "P3";
export type TaskStatus = "open" | "in-progress" | "done";

export interface OnCallTask {
  id: string;
  title: string;
  assignee: string;
  priority: TaskPriority;
  status: TaskStatus;
  linkedIncident?: string;
  linkedRunbook?: string;
  createdAt: string;
}

export interface AIRecommendation {
  id: string;
  description: string;
  confidence: number; // 0-100
  type: "assignment" | "redistribution" | "handoff";
}

// ---- Schedule & Runbooks (extracted from page) ----

export const CURRENT_ON_CALL = {
  primary: {
    name: "June Gu",
    team: "Platform",
    since: "2026-03-08T09:00:00Z",
    until: "2026-03-15T09:00:00Z",
  },
  secondary: {
    name: "SRE Bot",
    team: "Platform",
    since: "2026-03-08T09:00:00Z",
    until: "2026-03-15T09:00:00Z",
  },
};

export const SCHEDULE = [
  { week: "Mar 1-7", primary: "Team Member A", secondary: "Team Member B" },
  { week: "Mar 8-14", primary: "June Gu", secondary: "SRE Bot" },
  { week: "Mar 15-21", primary: "Team Member C", secondary: "Team Member A" },
  { week: "Mar 22-28", primary: "Team Member B", secondary: "Team Member C" },
];

export const RUNBOOKS = [
  {
    id: "rb-001",
    title: "Database Connection Pool Exhaustion",
    service: "payment-service",
    lastUsed: "2026-03-02",
    steps: 5,
    severity: "critical" as const,
  },
  {
    id: "rb-002",
    title: "High Memory Usage Alert",
    service: "api-gateway",
    lastUsed: "2026-02-28",
    steps: 4,
    severity: "high" as const,
  },
  {
    id: "rb-003",
    title: "Certificate Renewal Procedure",
    service: "infrastructure",
    lastUsed: "2026-02-15",
    steps: 6,
    severity: "medium" as const,
  },
  {
    id: "rb-004",
    title: "Kafka Consumer Lag Remediation",
    service: "notification-service",
    lastUsed: "2026-02-20",
    steps: 7,
    severity: "high" as const,
  },
  {
    id: "rb-005",
    title: "Redis Cluster Failover",
    service: "infrastructure",
    lastUsed: "2026-01-30",
    steps: 8,
    severity: "critical" as const,
  },
  {
    id: "rb-006",
    title: "DNS Resolution Failure",
    service: "infrastructure",
    lastUsed: "2026-02-10",
    steps: 3,
    severity: "medium" as const,
  },
];

export const ESCALATION_POLICIES = [
  { level: 1, target: "Primary On-Call", delay: "0 min", method: "Slack + PagerDuty" },
  { level: 2, target: "Secondary On-Call", delay: "5 min", method: "Slack + PagerDuty + Phone" },
  { level: 3, target: "Team Lead", delay: "15 min", method: "Phone + SMS" },
  { level: 4, target: "Engineering Manager", delay: "30 min", method: "Phone + SMS + Email" },
];

// ---- Team members ----

export const TEAM_MEMBERS: TeamMember[] = [
  {
    id: "tm-001",
    name: "June Gu",
    email: "june.gu@aegis.dev",
    role: "SRE",
    avatarInitials: "JG",
    expertise: ["Kubernetes", "Terraform", "AWS", "PostgreSQL"],
    isOnCall: true,
  },
  {
    id: "tm-002",
    name: "Sarah Chen",
    email: "sarah.chen@aegis.dev",
    role: "Backend",
    avatarInitials: "SC",
    expertise: ["Go", "Kafka", "Payment Systems"],
  },
  {
    id: "tm-003",
    name: "Mike Rodriguez",
    email: "mike.rodriguez@aegis.dev",
    role: "Platform",
    avatarInitials: "MR",
    expertise: ["CI/CD", "Docker", "GitHub Actions"],
  },
  {
    id: "tm-004",
    name: "Lisa Wang",
    email: "lisa.wang@aegis.dev",
    role: "Backend",
    avatarInitials: "LW",
    expertise: ["Java", "Spring Boot", "PostgreSQL"],
  },
  {
    id: "tm-005",
    name: "David Kim",
    email: "david.kim@aegis.dev",
    role: "DevOps",
    avatarInitials: "DK",
    expertise: ["ArgoCD", "Helm", "Monitoring"],
  },
  {
    id: "tm-006",
    name: "Alex Turner",
    email: "alex.turner@aegis.dev",
    role: "Security",
    avatarInitials: "AT",
    expertise: ["RBAC", "Network Policies", "Compliance"],
  },
];

// ---- Tasks ----

export const TASKS: OnCallTask[] = [
  {
    id: "task-001",
    title: "Investigate payment-service connection pool saturation",
    assignee: "tm-002",
    priority: "P0",
    status: "in-progress",
    linkedIncident: "INC-1301",
    createdAt: "2026-04-10T08:00:00Z",
  },
  {
    id: "task-002",
    title: "Deploy PgBouncer for auth-service",
    assignee: "tm-004",
    priority: "P0",
    status: "in-progress",
    linkedIncident: "INC-1299",
    createdAt: "2026-04-10T07:30:00Z",
  },
  {
    id: "task-003",
    title: "Fix cert-manager DNS01 challenge IAM permissions",
    assignee: "tm-001",
    priority: "P1",
    status: "open",
    linkedIncident: "INC-1300",
    linkedRunbook: "rb-003",
    createdAt: "2026-04-10T06:00:00Z",
  },
  {
    id: "task-004",
    title: "Review and merge auth-service memory fix PR #482",
    assignee: "tm-003",
    priority: "P1",
    status: "done",
    linkedIncident: "INC-1295",
    createdAt: "2026-04-09T14:00:00Z",
  },
  {
    id: "task-005",
    title: "Run Kafka consumer lag remediation runbook",
    assignee: "tm-005",
    priority: "P1",
    status: "open",
    linkedRunbook: "rb-004",
    createdAt: "2026-04-10T05:00:00Z",
  },
  {
    id: "task-006",
    title: "Update SigNoz alert thresholds for notification-service",
    assignee: "tm-005",
    priority: "P2",
    status: "open",
    linkedIncident: "INC-1292",
    createdAt: "2026-04-09T10:00:00Z",
  },
  {
    id: "task-007",
    title: "Audit RBAC policies for new endpoints",
    assignee: "tm-006",
    priority: "P2",
    status: "in-progress",
    createdAt: "2026-04-08T09:00:00Z",
  },
  {
    id: "task-008",
    title: "Write postmortem for rate limiter misconfiguration",
    assignee: "tm-002",
    priority: "P2",
    status: "done",
    linkedIncident: "INC-1288",
    createdAt: "2026-04-05T11:00:00Z",
  },
  {
    id: "task-009",
    title: "Set up Redis Cluster failover monitoring",
    assignee: "tm-001",
    priority: "P3",
    status: "open",
    linkedRunbook: "rb-005",
    createdAt: "2026-04-07T08:00:00Z",
  },
  {
    id: "task-010",
    title: "Document DNS resolution failure runbook improvements",
    assignee: "tm-006",
    priority: "P3",
    status: "open",
    linkedRunbook: "rb-006",
    createdAt: "2026-04-06T16:00:00Z",
  },
];

// ---- AI Recommendations ----

export const AI_RECOMMENDATIONS: AIRecommendation[] = [
  {
    id: "ai-001",
    description:
      "Assign junegu to payment-service incidents (handled 5 similar incidents in the past 30 days, 92% resolution rate)",
    confidence: 87,
    type: "assignment",
  },
  {
    id: "ai-002",
    description:
      "Consider redistributing: Sarah Chen has 4 active tasks, David Kim has 1. Moving task-006 to David Kim would balance the load",
    confidence: 74,
    type: "redistribution",
  },
  {
    id: "ai-003",
    description:
      "Handoff summary: 2 active incidents (INC-1301 P0, INC-1299 P0), 1 monitoring (INC-1292), RB-003 cert renewal in progress. Next on-call should prioritize PgBouncer deployment",
    confidence: 95,
    type: "handoff",
  },
];

// ---- Lookup helpers ----

export function getMemberById(id: string): TeamMember | undefined {
  return TEAM_MEMBERS.find((m) => m.id === id);
}

export function getMemberName(id: string): string {
  return getMemberById(id)?.name ?? "Unassigned";
}
