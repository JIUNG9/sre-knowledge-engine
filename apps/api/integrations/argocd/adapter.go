// Package argocd implements the integration adapter for ArgoCD GitOps platform.
package argocd

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/junegu/aegis/api/integrations"
)

// Adapter implements integrations.Adapter for ArgoCD.
type Adapter struct {
	serverURL string
	authToken string
	httpClient *http.Client
	connected  bool
}

// New creates a new ArgoCD adapter.
func New() *Adapter {
	return &Adapter{
		httpClient: &http.Client{Timeout: 15 * time.Second},
	}
}

// ID returns the unique identifier for the ArgoCD adapter.
func (a *Adapter) ID() string { return "argocd" }

// Name returns the human-readable name.
func (a *Adapter) Name() string { return "ArgoCD" }

// Category returns the adapter category.
func (a *Adapter) Category() string { return "deployment" }

// Connect validates and stores the ArgoCD connection configuration.
func (a *Adapter) Connect(config map[string]string) error {
	serverURL, ok := config["server_url"]
	if !ok || serverURL == "" {
		return fmt.Errorf("ArgoCD server URL is required")
	}

	authToken, ok := config["auth_token"]
	if !ok || authToken == "" {
		return fmt.Errorf("ArgoCD auth token is required")
	}

	a.serverURL = serverURL
	a.authToken = authToken
	a.connected = true
	return nil
}

// Test verifies the ArgoCD connection by listing applications.
func (a *Adapter) Test() (*integrations.HealthResult, error) {
	if !a.connected {
		return &integrations.HealthResult{
			Healthy: false,
			Message: "Not connected. Call Connect() first.",
		}, nil
	}

	start := time.Now()

	req, err := http.NewRequest("GET", a.serverURL+"/api/v1/applications", nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+a.authToken)

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

	if resp.StatusCode == http.StatusUnauthorized || resp.StatusCode == http.StatusForbidden {
		return &integrations.HealthResult{
			Healthy: false,
			Message: "Authentication failed. Check your auth token.",
			Latency: latency,
		}, nil
	}

	if resp.StatusCode != http.StatusOK {
		return &integrations.HealthResult{
			Healthy: false,
			Message: fmt.Sprintf("ArgoCD returned HTTP %d", resp.StatusCode),
			Latency: latency,
		}, nil
	}

	return &integrations.HealthResult{
		Healthy: true,
		Message: "ArgoCD is healthy and accessible",
		Latency: latency,
	}, nil
}

// Sync lists all ArgoCD applications and their sync status.
func (a *Adapter) Sync() (*integrations.SyncResult, error) {
	if !a.connected {
		return nil, fmt.Errorf("not connected")
	}

	start := time.Now()

	req, err := http.NewRequest("GET", a.serverURL+"/api/v1/applications", nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+a.authToken)

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
			Message:  fmt.Sprintf("ArgoCD returned HTTP %d", resp.StatusCode),
		}, nil
	}

	// Parse the applications response.
	var appsResp struct {
		Items []json.RawMessage `json:"items"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&appsResp); err != nil {
		return &integrations.SyncResult{
			Success:  true,
			Items:    0,
			Duration: duration,
			Message:  "Sync completed but failed to parse response",
		}, nil
	}

	return &integrations.SyncResult{
		Success:  true,
		Items:    len(appsResp.Items),
		Duration: duration,
		Message:  fmt.Sprintf("Synced %d applications from ArgoCD", len(appsResp.Items)),
	}, nil
}

// Disconnect clears the ArgoCD connection configuration.
func (a *Adapter) Disconnect() error {
	a.serverURL = ""
	a.authToken = ""
	a.connected = false
	return nil
}

// ConfigSchema returns the configuration fields required by ArgoCD.
func (a *Adapter) ConfigSchema() []integrations.ConfigField {
	return []integrations.ConfigField{
		{
			Key:         "server_url",
			Label:       "Server URL",
			Type:        "url",
			Required:    true,
			Placeholder: "https://argocd.example.com",
			HelpText:    "The base URL of your ArgoCD server",
		},
		{
			Key:         "auth_token",
			Label:       "Auth Token",
			Type:        "password",
			Required:    true,
			Placeholder: "Enter your ArgoCD auth token",
			HelpText:    "ArgoCD API token. Generate one via Settings > Accounts in the ArgoCD UI.",
		},
	}
}

// Compile-time interface check.
var _ integrations.Adapter = (*Adapter)(nil)
