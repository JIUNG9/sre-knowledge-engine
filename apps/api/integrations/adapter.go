// Package integrations defines the common interface for external service adapters.
// Each integration (SigNoz, Slack, ArgoCD, etc.) implements this interface to
// provide a consistent connect/test/sync/disconnect lifecycle.
package integrations

// Adapter is the interface that all integration adapters must implement.
// It provides a unified lifecycle for connecting, testing, syncing data,
// and disconnecting from external services.
type Adapter interface {
	// ID returns the unique identifier for this adapter (e.g., "signoz", "slack").
	ID() string

	// Name returns the human-readable name (e.g., "SigNoz", "Slack").
	Name() string

	// Category returns the adapter category (e.g., "monitoring", "notification", "deployment").
	Category() string

	// Connect establishes a connection using the provided configuration.
	// The config map contains key-value pairs matching the ConfigSchema fields.
	Connect(config map[string]string) error

	// Test verifies the connection is healthy and the credentials are valid.
	Test() (*HealthResult, error)

	// Sync pulls the latest data from the external service.
	Sync() (*SyncResult, error)

	// Disconnect cleanly tears down the connection and clears credentials.
	Disconnect() error

	// ConfigSchema returns the schema describing what configuration fields
	// this adapter requires from the user.
	ConfigSchema() []ConfigField
}

// ConfigField describes a single configuration field required by an adapter.
type ConfigField struct {
	Key         string `json:"key"`
	Label       string `json:"label"`
	Type        string `json:"type"` // text, password, url, select
	Required    bool   `json:"required"`
	Placeholder string `json:"placeholder,omitempty"`
	HelpText    string `json:"help_text,omitempty"`
}

// HealthResult represents the outcome of a connection health check.
type HealthResult struct {
	Healthy bool   `json:"healthy"`
	Message string `json:"message"`
	Latency int    `json:"latency_ms"`
}

// SyncResult represents the outcome of a data synchronization operation.
type SyncResult struct {
	Success  bool   `json:"success"`
	Items    int    `json:"items_synced"`
	Duration int    `json:"duration_ms"`
	Message  string `json:"message,omitempty"`
}
