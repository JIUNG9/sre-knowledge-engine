package models

import "time"

// BudgetStatus represents the status of a team budget.
type BudgetStatus string

const (
	BudgetStatusUnder    BudgetStatus = "under"
	BudgetStatusAtRisk   BudgetStatus = "at_risk"
	BudgetStatusExceeded BudgetStatus = "exceeded"
)

// AnomalySeverity represents the severity of a cost anomaly.
type AnomalySeverity string

const (
	AnomalySeverityCritical AnomalySeverity = "critical"
	AnomalySeverityWarning  AnomalySeverity = "warning"
	AnomalySeverityInfo     AnomalySeverity = "info"
)

// CostEntry represents a single cost line item for a given day and service.
type CostEntry struct {
	Date     string            `json:"date"`
	Service  string            `json:"service"`
	Account  string            `json:"account"`
	Provider string            `json:"provider"`
	Amount   float64           `json:"amount"`
	Currency string            `json:"currency"`
	Tags     map[string]string `json:"tags"`
}

// CostSummary provides a high-level overview of cloud spend for a period.
type CostSummary struct {
	Period         string             `json:"period"`
	TotalCost      float64            `json:"total_cost"`
	PreviousPeriod float64            `json:"previous_period"`
	ChangePercent  float64            `json:"change_percent"`
	CostByProvider map[string]float64 `json:"cost_by_provider"`
	CostByService  map[string]float64 `json:"cost_by_service"`
	CostByTeam     map[string]float64 `json:"cost_by_team"`
}

// CostAnomaly represents a detected deviation from expected cloud spending.
type CostAnomaly struct {
	ID               string          `json:"id"`
	Service          string          `json:"service"`
	ExpectedCost     float64         `json:"expected_cost"`
	ActualCost       float64         `json:"actual_cost"`
	DeviationPercent float64         `json:"deviation_percent"`
	Severity         AnomalySeverity `json:"severity"`
	DetectedAt       time.Time       `json:"detected_at"`
	Description      string          `json:"description"`
}

// Budget represents a team or project cost budget with tracking.
type Budget struct {
	ID             string       `json:"id"`
	Name           string       `json:"name"`
	Team           string       `json:"team"`
	Limit          float64      `json:"limit"`
	CurrentSpend   float64      `json:"current_spend"`
	ProjectedSpend float64      `json:"projected_spend"`
	Period         string       `json:"period"`
	Status         BudgetStatus `json:"status"`
}

// KubernetesCost represents cost allocation for a single Kubernetes namespace.
type KubernetesCost struct {
	Namespace   string  `json:"namespace"`
	Pods        int     `json:"pods"`
	CPUCost     float64 `json:"cpu_cost"`
	MemoryCost  float64 `json:"memory_cost"`
	StorageCost float64 `json:"storage_cost"`
	TotalCost   float64 `json:"total_cost"`
	IdlePercent float64 `json:"idle_percent"`
}

// CostTrend represents a single data point for cost trend charting.
type CostTrend struct {
	Date     string  `json:"date"`
	Amount   float64 `json:"amount"`
	Provider string  `json:"provider"`
}
