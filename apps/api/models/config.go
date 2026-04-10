package models

import "time"

// AegisConfig represents a configuration entry for the Aegis platform.
type AegisConfig struct {
	ID        string    `json:"id"`
	Section   string    `json:"section"` // "ai", "cloud", "integrations", "team", "general"
	Key       string    `json:"key"`
	Value     string    `json:"value"` // encrypted for secrets
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// SetupStatus represents the current state of the initial setup wizard.
type SetupStatus struct {
	Completed   bool        `json:"completed"`
	CurrentStep int         `json:"current_step"`
	Steps       []SetupStep `json:"steps"`
}

// SetupStep represents an individual step in the setup wizard.
type SetupStep struct {
	Number int    `json:"number"`
	Name   string `json:"name"`
	Status string `json:"status"` // "complete", "current", "pending"
}

// CloudAccount represents a connected cloud provider account.
type CloudAccount struct {
	ID             string    `json:"id"`
	Name           string    `json:"name"`
	Alias          string    `json:"alias"`
	Provider       string    `json:"provider"` // aws, gcp, azure, ncloud, custom
	AccountID      string    `json:"account_id"`
	Region         string    `json:"region"`
	Role           string    `json:"role"` // hub, spoke, standalone
	Status         string    `json:"status"` // connected, disconnected, error
	ConnectionType string    `json:"connection_type"` // access_key, assume_role
	CreatedAt      time.Time `json:"created_at"`
}

// Integration represents an external tool integration.
type Integration struct {
	ID        string            `json:"id"`
	Name      string            `json:"name"`
	Category  string            `json:"category"` // monitoring, deployment, notification, ticketing, security
	Status    string            `json:"status"`   // connected, disconnected, error, not_configured
	Config    map[string]string `json:"config,omitempty"` // API keys etc (masked in response)
	LastSync  *time.Time        `json:"last_sync,omitempty"`
	LastError string            `json:"last_error,omitempty"`
}

// TeamMember represents a member of the Aegis team.
type TeamMember struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	Email string `json:"email"`
	Role  string `json:"role"` // admin, member, viewer
}

// ConnectionTestResult represents the result of testing a connection.
type ConnectionTestResult struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
	Latency int    `json:"latency_ms"`
}

// SaveConfigRequest represents the payload for saving a config entry.
type SaveConfigRequest struct {
	Section string `json:"section"`
	Key     string `json:"key"`
	Value   string `json:"value"`
}

// TestConnectionRequest represents the payload for testing a connection.
type TestConnectionRequest struct {
	Type   string            `json:"type"`
	Config map[string]string `json:"config"`
}

// CreateAccountRequest represents the payload for adding a cloud account.
type CreateAccountRequest struct {
	Name           string `json:"name"`
	Alias          string `json:"alias"`
	Provider       string `json:"provider"`
	AccountID      string `json:"account_id"`
	Region         string `json:"region"`
	Role           string `json:"role"`
	ConnectionType string `json:"connection_type"`
}

// UpdateAccountRequest represents the payload for updating a cloud account.
type UpdateAccountRequest struct {
	Name           *string `json:"name,omitempty"`
	Alias          *string `json:"alias,omitempty"`
	Provider       *string `json:"provider,omitempty"`
	AccountID      *string `json:"account_id,omitempty"`
	Region         *string `json:"region,omitempty"`
	Role           *string `json:"role,omitempty"`
	ConnectionType *string `json:"connection_type,omitempty"`
}

// UpdateIntegrationRequest represents the payload for updating an integration.
type UpdateIntegrationRequest struct {
	Config map[string]string `json:"config"`
}
