// Package signoz implements the integration adapter for SigNoz observability platform.
package signoz

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/junegu/aegis/api/integrations"
)

// Adapter implements integrations.Adapter for SigNoz.
type Adapter struct {
	url        string
	apiKey     string
	httpClient *http.Client
	connected  bool
}

// New creates a new SigNoz adapter.
func New() *Adapter {
	return &Adapter{
		httpClient: &http.Client{Timeout: 15 * time.Second},
	}
}

// ID returns the unique identifier for the SigNoz adapter.
func (a *Adapter) ID() string { return "signoz" }

// Name returns the human-readable name.
func (a *Adapter) Name() string { return "SigNoz" }

// Category returns the adapter category.
func (a *Adapter) Category() string { return "monitoring" }

// Connect validates and stores the SigNoz connection configuration.
func (a *Adapter) Connect(config map[string]string) error {
	url, ok := config["url"]
	if !ok || url == "" {
		return fmt.Errorf("SigNoz URL is required")
	}

	apiKey, ok := config["api_key"]
	if !ok || apiKey == "" {
		return fmt.Errorf("SigNoz API key is required")
	}

	a.url = url
	a.apiKey = apiKey
	a.connected = true
	return nil
}

// Test verifies the SigNoz connection by hitting the health endpoint.
func (a *Adapter) Test() (*integrations.HealthResult, error) {
	if !a.connected {
		return &integrations.HealthResult{
			Healthy: false,
			Message: "Not connected. Call Connect() first.",
		}, nil
	}

	start := time.Now()

	req, err := http.NewRequest("GET", a.url+"/api/v1/health", nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+a.apiKey)

	resp, err := a.httpClient.Do(req)
	latency := int(time.Since(start).Milliseconds())

	if err != nil {
		return &integrations.HealthResult{
			Healthy: false,
			Message: fmt.Sprintf("Connection failed: %v", err),
			Latency: latency,
		}, nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return &integrations.HealthResult{
			Healthy: false,
			Message: fmt.Sprintf("SigNoz returned HTTP %d", resp.StatusCode),
			Latency: latency,
		}, nil
	}

	return &integrations.HealthResult{
		Healthy: true,
		Message: "SigNoz is healthy",
		Latency: latency,
	}, nil
}

// Sync queries recent alerts from SigNoz.
func (a *Adapter) Sync() (*integrations.SyncResult, error) {
	if !a.connected {
		return nil, fmt.Errorf("not connected")
	}

	start := time.Now()

	req, err := http.NewRequest("GET", a.url+"/api/v1/alerts", nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+a.apiKey)

	resp, err := a.httpClient.Do(req)
	duration := int(time.Since(start).Milliseconds())

	if err != nil {
		return &integrations.SyncResult{
			Success:  false,
			Duration: duration,
			Message:  fmt.Sprintf("Sync failed: %v", err),
		}, nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return &integrations.SyncResult{
			Success:  false,
			Duration: duration,
			Message:  fmt.Sprintf("SigNoz returned HTTP %d", resp.StatusCode),
		}, nil
	}

	// Parse the alerts response to count items.
	var alertsResp struct {
		Data []json.RawMessage `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&alertsResp); err != nil {
		return &integrations.SyncResult{
			Success:  true,
			Items:    0,
			Duration: duration,
			Message:  "Sync completed but failed to parse response",
		}, nil
	}

	return &integrations.SyncResult{
		Success:  true,
		Items:    len(alertsResp.Data),
		Duration: duration,
		Message:  fmt.Sprintf("Synced %d alerts from SigNoz", len(alertsResp.Data)),
	}, nil
}

// Disconnect clears the SigNoz connection configuration.
func (a *Adapter) Disconnect() error {
	a.url = ""
	a.apiKey = ""
	a.connected = false
	return nil
}

// ConfigSchema returns the configuration fields required by SigNoz.
func (a *Adapter) ConfigSchema() []integrations.ConfigField {
	return []integrations.ConfigField{
		{
			Key:         "url",
			Label:       "SigNoz URL",
			Type:        "url",
			Required:    true,
			Placeholder: "https://signoz.example.com",
			HelpText:    "The base URL of your SigNoz instance",
		},
		{
			Key:         "api_key",
			Label:       "API Key",
			Type:        "password",
			Required:    true,
			Placeholder: "Enter your SigNoz API key",
			HelpText:    "API key for authenticating with SigNoz. Found in Settings > API Keys.",
		},
	}
}

// Compile-time interface check.
var _ integrations.Adapter = (*Adapter)(nil)
