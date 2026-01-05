package models

import "time"

// Severity represents the severity level of an incident.
type Severity string

const (
	SeverityCritical Severity = "critical"
	SeverityHigh     Severity = "high"
	SeverityMedium   Severity = "medium"
	SeverityLow      Severity = "low"
)

// IncidentStatus represents the current status of an incident.
type IncidentStatus string

const (
	IncidentStatusOpen          IncidentStatus = "open"
	IncidentStatusInvestigating IncidentStatus = "investigating"
	IncidentStatusIdentified    IncidentStatus = "identified"
	IncidentStatusMonitoring    IncidentStatus = "monitoring"
	IncidentStatusResolved      IncidentStatus = "resolved"
)

// TimelineEventType represents what kind of event occurred.
type TimelineEventType string

const (
	TimelineEventAlertFired    TimelineEventType = "alert_fired"
	TimelineEventAcknowledged  TimelineEventType = "acknowledged"
	TimelineEventStatusChange  TimelineEventType = "status_change"
	TimelineEventNoteAdded     TimelineEventType = "note_added"
	TimelineEventEscalated     TimelineEventType = "escalated"
	TimelineEventResolved      TimelineEventType = "resolved"
)

// TimelineEvent represents a single event in an incident's timeline.
type TimelineEvent struct {
	ID         string            `json:"id"`
	IncidentID string            `json:"incident_id"`
	Type       TimelineEventType `json:"type"`
	Actor      string            `json:"actor"`
	Message    string            `json:"message"`
	Metadata   map[string]string `json:"metadata,omitempty"`
	Timestamp  time.Time         `json:"timestamp"`
}

// Incident represents a production incident tracked by Aegis.
type Incident struct {
	ID            string          `json:"id"`
	Title         string          `json:"title"`
	Description   string          `json:"description"`
	Severity      Severity        `json:"severity"`
	Status        IncidentStatus  `json:"status"`
	Service       string          `json:"service"`
	Assignee      string          `json:"assignee"`
	Timeline      []TimelineEvent `json:"timeline"`
	RelatedAlerts []string        `json:"related_alerts"`
	RootCause     string          `json:"root_cause,omitempty"`
	Remediation   string          `json:"remediation,omitempty"`
	CreatedAt     time.Time       `json:"created_at"`
	UpdatedAt     time.Time       `json:"updated_at"`
	ResolvedAt    *time.Time      `json:"resolved_at,omitempty"`
	Duration      float64         `json:"duration"` // seconds
}

// CreateIncidentRequest represents the payload for creating a new incident.
type CreateIncidentRequest struct {
	Title       string   `json:"title"`
	Description string   `json:"description"`
	Severity    Severity `json:"severity"`
	Service     string   `json:"service"`
	Assignee    string   `json:"assignee,omitempty"`
}

// UpdateIncidentRequest represents the payload for updating an existing incident.
type UpdateIncidentRequest struct {
	Title       *string         `json:"title,omitempty"`
	Description *string         `json:"description,omitempty"`
	Severity    *Severity       `json:"severity,omitempty"`
	Status      *IncidentStatus `json:"status,omitempty"`
	Service     *string         `json:"service,omitempty"`
	Assignee    *string         `json:"assignee,omitempty"`
	RootCause   *string         `json:"root_cause,omitempty"`
	Remediation *string         `json:"remediation,omitempty"`
}

// TimelineAddRequest represents the payload for adding a timeline event.
type TimelineAddRequest struct {
	Type     TimelineEventType `json:"type"`
	Actor    string            `json:"actor"`
	Message  string            `json:"message"`
	Metadata map[string]string `json:"metadata,omitempty"`
}

// IncidentStats holds aggregated incident statistics.
type IncidentStats struct {
	TotalActive    int     `json:"total_active"`
	Critical       int     `json:"critical"`
	High           int     `json:"high"`
	Medium         int     `json:"medium"`
	Low            int     `json:"low"`
	MTTR           float64 `json:"mttr"`            // mean time to resolve in seconds
	OpenedToday    int     `json:"opened_today"`
	ResolvedToday  int     `json:"resolved_today"`
	ResolutionRate float64 `json:"resolution_rate"`  // 0.0 to 1.0
}
