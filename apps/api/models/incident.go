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
	IncidentStatusResolved      IncidentStatus = "resolved"
)

// Incident represents a production incident tracked by Aegis.
type Incident struct {
	ID                   string         `json:"id"`
	Title                string         `json:"title"`
	Severity             Severity       `json:"severity"`
	Status               IncidentStatus `json:"status"`
	Service              string         `json:"service"`
	Assignee             string         `json:"assignee"`
	Description          string         `json:"description"`
	RootCause            string         `json:"root_cause,omitempty"`
	CreatedAt            time.Time      `json:"created_at"`
	UpdatedAt            time.Time      `json:"updated_at"`
}

// CreateIncidentRequest represents the payload for creating a new incident.
type CreateIncidentRequest struct {
	Title       string   `json:"title"`
	Severity    Severity `json:"severity"`
	Service     string   `json:"service"`
	Assignee    string   `json:"assignee,omitempty"`
	Description string   `json:"description"`
}

// UpdateIncidentRequest represents the payload for updating an existing incident.
type UpdateIncidentRequest struct {
	Title       *string         `json:"title,omitempty"`
	Severity    *Severity       `json:"severity,omitempty"`
	Status      *IncidentStatus `json:"status,omitempty"`
	Assignee    *string         `json:"assignee,omitempty"`
	Description *string         `json:"description,omitempty"`
	RootCause   *string         `json:"root_cause,omitempty"`
}
