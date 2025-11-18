package models

import "time"

// ServiceStatus represents the health status of a service.
type ServiceStatus string

const (
	ServiceStatusHealthy  ServiceStatus = "healthy"
	ServiceStatusDegraded ServiceStatus = "degraded"
	ServiceStatusDown     ServiceStatus = "down"
)

// Service represents a service in the Aegis service catalog.
type Service struct {
	ID           string        `json:"id"`
	Name         string        `json:"name"`
	Description  string        `json:"description"`
	Team         string        `json:"team"`
	Repository   string        `json:"repository"`
	Language     string        `json:"language"`
	Framework    string        `json:"framework"`
	SLOTarget    float64       `json:"slo_target"`
	Status       ServiceStatus `json:"status"`
	Dependencies []string      `json:"dependencies"`
	Tier         string        `json:"tier"`
	OnCallTeam   string        `json:"oncall_team"`
	DeployFreq   string        `json:"deploy_frequency"`
	LastDeploy   time.Time     `json:"last_deploy"`
	CreatedAt    time.Time     `json:"created_at"`
	UpdatedAt    time.Time     `json:"updated_at"`
}
