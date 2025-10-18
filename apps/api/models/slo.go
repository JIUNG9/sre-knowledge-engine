package models

// SLIType represents the type of Service Level Indicator.
type SLIType string

const (
	SLITypeAvailability SLIType = "availability"
	SLITypeLatency      SLIType = "latency"
	SLITypeErrorRate    SLIType = "error_rate"
	SLITypeThroughput   SLIType = "throughput"
)

// SLO represents a Service Level Objective tracked by Aegis.
type SLO struct {
	ID                   string  `json:"id"`
	ServiceID            string  `json:"service_id"`
	Name                 string  `json:"name"`
	Target               float64 `json:"target"`
	Current              float64 `json:"current"`
	Window               string  `json:"window"`
	SLIType              SLIType `json:"sli_type"`
	ErrorBudgetRemaining float64 `json:"error_budget_remaining"`
}
