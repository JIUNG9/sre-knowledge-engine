package models

import "time"

// AlertSource represents the origin system of an alert.
type AlertSource string

const (
	AlertSourceSigNoz      AlertSource = "signoz"
	AlertSourceDatadog     AlertSource = "datadog"
	AlertSourcePrometheus  AlertSource = "prometheus"
	AlertSourceCloudWatch  AlertSource = "cloudwatch"
)

// AlertStatus represents whether an alert is currently firing or resolved.
type AlertStatus string

const (
	AlertStatusFiring   AlertStatus = "firing"
	AlertStatusResolved AlertStatus = "resolved"
)

// Alert represents an individual alert received from a monitoring source.
type Alert struct {
	ID          string            `json:"id"`
	Source      AlertSource       `json:"source"`
	Title       string            `json:"title"`
	Description string            `json:"description"`
	Severity    Severity          `json:"severity"`
	Service     string            `json:"service"`
	Status      AlertStatus       `json:"status"`
	Labels      map[string]string `json:"labels,omitempty"`
	Annotations map[string]string `json:"annotations,omitempty"`
	StartsAt    time.Time         `json:"starts_at"`
	EndsAt      *time.Time        `json:"ends_at,omitempty"`
	Fingerprint string            `json:"fingerprint"`
}

// AlertGroup groups alerts by their fingerprint for deduplication.
type AlertGroup struct {
	Fingerprint string    `json:"fingerprint"`
	Count       int       `json:"count"`
	Alerts      []Alert   `json:"alerts"`
	FirstSeen   time.Time `json:"first_seen"`
	LastSeen    time.Time `json:"last_seen"`
}

// AlertmanagerPayload represents the webhook payload from Prometheus Alertmanager.
type AlertmanagerPayload struct {
	Version           string              `json:"version"`
	GroupKey          string              `json:"groupKey"`
	TruncatedAlerts   int                 `json:"truncatedAlerts"`
	Status            string              `json:"status"`
	Receiver          string              `json:"receiver"`
	GroupLabels       map[string]string   `json:"groupLabels"`
	CommonLabels      map[string]string   `json:"commonLabels"`
	CommonAnnotations map[string]string   `json:"commonAnnotations"`
	ExternalURL       string              `json:"externalURL"`
	Alerts            []AlertmanagerAlert `json:"alerts"`
}

// AlertmanagerAlert represents a single alert in an Alertmanager webhook payload.
type AlertmanagerAlert struct {
	Status       string            `json:"status"`
	Labels       map[string]string `json:"labels"`
	Annotations  map[string]string `json:"annotations"`
	StartsAt     time.Time         `json:"startsAt"`
	EndsAt       time.Time         `json:"endsAt"`
	GeneratorURL string            `json:"generatorURL"`
	Fingerprint  string            `json:"fingerprint"`
}
