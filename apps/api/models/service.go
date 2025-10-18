package models

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
	Team         string        `json:"team"`
	Repository   string        `json:"repository"`
	SLOTarget    float64       `json:"slo_target"`
	Status       ServiceStatus `json:"status"`
	Dependencies []string      `json:"dependencies"`
}
