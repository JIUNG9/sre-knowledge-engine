package models

import "time"

// SLIType represents the type of Service Level Indicator.
type SLIType string

const (
	SLITypeAvailability SLIType = "availability"
	SLITypeLatency      SLIType = "latency"
	SLITypeErrorRate    SLIType = "error_rate"
	SLITypeThroughput   SLIType = "throughput"
)

// SLOStatus represents whether an SLO is being met.
type SLOStatus string

const (
	SLOStatusMeeting   SLOStatus = "meeting"
	SLOStatusAtRisk    SLOStatus = "at_risk"
	SLOStatusBreaching SLOStatus = "breaching"
)

// SLO represents a Service Level Objective tracked by Aegis.
type SLO struct {
	ID                       string    `json:"id"`
	ServiceID                string    `json:"service_id"`
	Name                     string    `json:"name"`
	Description              string    `json:"description"`
	Target                   float64   `json:"target"`
	Current                  float64   `json:"current"`
	Window                   string    `json:"window"`
	SLIType                  SLIType   `json:"sli_type"`
	ErrorBudgetTotal         float64   `json:"error_budget_total"`
	ErrorBudgetRemaining     float64   `json:"error_budget_remaining"`
	ErrorBudgetConsumedPct   float64   `json:"error_budget_consumed_percent"`
	BurnRate                 float64   `json:"burn_rate"`
	Status                   SLOStatus `json:"status"`
	CreatedAt                time.Time `json:"created_at"`
	UpdatedAt                time.Time `json:"updated_at"`
}

// SLOCreateRequest represents the payload for creating a new SLO.
type SLOCreateRequest struct {
	ServiceID   string  `json:"service_id"`
	Name        string  `json:"name"`
	Description string  `json:"description"`
	Target      float64 `json:"target"`
	Window      string  `json:"window"`
	SLIType     SLIType `json:"sli_type"`
}

// SLOUpdateRequest represents the payload for updating an existing SLO.
// Pointer fields allow partial updates.
type SLOUpdateRequest struct {
	Name        *string  `json:"name,omitempty"`
	Description *string  `json:"description,omitempty"`
	Target      *float64 `json:"target,omitempty"`
	Window      *string  `json:"window,omitempty"`
	SLIType     *SLIType `json:"sli_type,omitempty"`
}

// ErrorBudgetDataPoint represents a single data point in an error budget time series.
type ErrorBudgetDataPoint struct {
	Timestamp time.Time `json:"timestamp"`
	Remaining float64   `json:"remaining"`
	BurnRate  float64   `json:"burn_rate"`
}

// SLOTimeSeries represents the error budget time series for a specific SLO.
type SLOTimeSeries struct {
	SLOID      string                 `json:"slo_id"`
	DataPoints []ErrorBudgetDataPoint `json:"data_points"`
}

// SLOSummary provides an aggregate overview of all SLOs.
type SLOSummary struct {
	TotalSLOs          int     `json:"total_slos"`
	Meeting            int     `json:"meeting"`
	AtRisk             int     `json:"at_risk"`
	Breaching          int     `json:"breaching"`
	AverageErrorBudget float64 `json:"average_error_budget"`
}
