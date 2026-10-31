package handlers

import (
	"encoding/json"
	"io"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"

	"github.com/JIUNG9/sre-knowledge-engine/apps/api/models"
)

// resetAlertStore swaps the package-level alert store for an empty one so a
// test sees only what it posted, and restores the original afterwards.
func resetAlertStore(t *testing.T) {
	t.Helper()
	alertStore.Lock()
	saved := alertStore.data
	alertStore.data = nil
	alertStore.Unlock()
	t.Cleanup(func() {
		alertStore.Lock()
		alertStore.data = saved
		alertStore.Unlock()
	})
}

func newWebhookApp() *fiber.App {
	h := NewWebhookHandlers(zap.NewNop())
	app := fiber.New(fiber.Config{DisableStartupMessage: true})
	app.Post("/webhooks/signoz", h.HandleSigNoz)
	app.Post("/webhooks/prometheus", h.HandlePrometheus)
	app.Post("/webhooks/datadog", h.HandleDatadog)
	return app
}

func postJSON(t *testing.T, app *fiber.App, path, body string) (int, []byte) {
	t.Helper()
	req := httptest.NewRequest(fiber.MethodPost, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	resp, err := app.Test(req, -1)
	if err != nil {
		t.Fatalf("app.Test(%s) error: %v", path, err)
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	return resp.StatusCode, b
}

func storedAlerts() []models.Alert {
	alertStore.RLock()
	defer alertStore.RUnlock()
	out := make([]models.Alert, len(alertStore.data))
	copy(out, alertStore.data)
	return out
}

func TestHandlePrometheus_StoresAlertWithMappedFields(t *testing.T) {
	resetAlertStore(t)
	app := newWebhookApp()

	status, body := postJSON(t, app, "/webhooks/prometheus", `{
		"status": "firing",
		"alerts": [{
			"status": "firing",
			"labels": {"alertname": "HighErrorRate", "severity": "warning", "service": "checkout"},
			"annotations": {"summary": "5xx above 5%"},
			"startsAt": "2026-10-01T10:00:00Z",
			"fingerprint": "abc123"
		}]
	}`)
	if status != fiber.StatusOK {
		t.Fatalf("status = %d, want 200 (body: %s)", status, body)
	}
	var resp map[string]any
	if err := json.Unmarshal(body, &resp); err != nil {
		t.Fatalf("response is not JSON: %v", err)
	}
	if resp["processed"] != float64(1) || resp["source"] != "prometheus" {
		t.Errorf("response = %v, want processed=1 source=prometheus", resp)
	}

	alerts := storedAlerts()
	if len(alerts) != 1 {
		t.Fatalf("stored %d alerts, want 1", len(alerts))
	}
	a := alerts[0]
	if a.Title != "HighErrorRate" || a.Description != "5xx above 5%" {
		t.Errorf("title/description = %q/%q", a.Title, a.Description)
	}
	if a.Source != models.AlertSourcePrometheus || a.Service != "checkout" {
		t.Errorf("source/service = %q/%q", a.Source, a.Service)
	}
	if a.Severity != models.SeverityHigh {
		t.Errorf("severity = %q, want %q (warning maps to high)", a.Severity, models.SeverityHigh)
	}
	if a.Status != models.AlertStatusFiring || a.EndsAt != nil {
		t.Errorf("status/EndsAt = %q/%v, want firing/nil", a.Status, a.EndsAt)
	}
	if a.Fingerprint != "abc123" {
		t.Errorf("fingerprint = %q, want the one Alertmanager sent", a.Fingerprint)
	}
}

func TestHandlePrometheus_SameFingerprintIsDeduplicatedAndResolves(t *testing.T) {
	resetAlertStore(t)
	app := newWebhookApp()

	firing := `{"alerts": [{"status": "firing", "labels": {"alertname": "DiskFull"},
		"startsAt": "2026-10-01T10:00:00Z", "fingerprint": "fp-1"}]}`
	resolved := `{"alerts": [{"status": "resolved", "labels": {"alertname": "DiskFull"},
		"startsAt": "2026-10-01T10:00:00Z", "endsAt": "2026-10-01T10:30:00Z", "fingerprint": "fp-1"}]}`

	postJSON(t, app, "/webhooks/prometheus", firing)
	postJSON(t, app, "/webhooks/prometheus", firing)
	if n := len(storedAlerts()); n != 1 {
		t.Fatalf("after two identical posts stored %d alerts, want 1", n)
	}

	postJSON(t, app, "/webhooks/prometheus", resolved)
	alerts := storedAlerts()
	if len(alerts) != 1 {
		t.Fatalf("after resolve stored %d alerts, want 1", len(alerts))
	}
	if alerts[0].Status != models.AlertStatusResolved {
		t.Errorf("status = %q, want resolved", alerts[0].Status)
	}
	wantEnd := time.Date(2026, 10, 1, 10, 30, 0, 0, time.UTC)
	if alerts[0].EndsAt == nil || !alerts[0].EndsAt.Equal(wantEnd) {
		t.Errorf("EndsAt = %v, want %v", alerts[0].EndsAt, wantEnd)
	}

	// The same alert firing again reopens it and clears the end time.
	postJSON(t, app, "/webhooks/prometheus", firing)
	alerts = storedAlerts()
	if len(alerts) != 1 || alerts[0].Status != models.AlertStatusFiring || alerts[0].EndsAt != nil {
		t.Errorf("after re-fire got %+v, want one firing alert with no EndsAt", alerts)
	}
}

func TestHandlePrometheus_MissingFingerprintIsDerivedFromLabels(t *testing.T) {
	resetAlertStore(t)
	app := newWebhookApp()

	// Same labels, different JSON key order: must dedupe to one alert.
	postJSON(t, app, "/webhooks/prometheus",
		`{"alerts": [{"status": "firing", "labels": {"alertname": "A", "service": "api"}}]}`)
	postJSON(t, app, "/webhooks/prometheus",
		`{"alerts": [{"status": "firing", "labels": {"service": "api", "alertname": "A"}}]}`)
	// Different labels: a separate alert.
	postJSON(t, app, "/webhooks/prometheus",
		`{"alerts": [{"status": "firing", "labels": {"alertname": "A", "service": "web"}}]}`)

	alerts := storedAlerts()
	if len(alerts) != 2 {
		t.Fatalf("stored %d alerts, want 2", len(alerts))
	}
	if alerts[0].Fingerprint == "" || alerts[0].Fingerprint == alerts[1].Fingerprint {
		t.Errorf("fingerprints %q and %q should be set and distinct", alerts[0].Fingerprint, alerts[1].Fingerprint)
	}
}

func TestHandlePrometheus_BatchCountsEveryAlert(t *testing.T) {
	resetAlertStore(t)
	app := newWebhookApp()

	status, body := postJSON(t, app, "/webhooks/prometheus", `{"alerts": [
		{"status": "firing", "labels": {"alertname": "A"}, "fingerprint": "f1"},
		{"status": "firing", "labels": {"alertname": "B"}, "fingerprint": "f2"},
		{"status": "firing", "labels": {"alertname": "A"}, "fingerprint": "f1"}
	]}`)
	if status != fiber.StatusOK {
		t.Fatalf("status = %d, want 200", status)
	}
	var resp map[string]any
	_ = json.Unmarshal(body, &resp)
	if resp["processed"] != float64(3) {
		t.Errorf("processed = %v, want 3 (received, not unique)", resp["processed"])
	}
	if n := len(storedAlerts()); n != 2 {
		t.Errorf("stored %d alerts, want 2 unique", n)
	}
}

func TestHandleWebhook_InvalidJSONIs400(t *testing.T) {
	resetAlertStore(t)
	app := newWebhookApp()

	for _, path := range []string{"/webhooks/prometheus", "/webhooks/signoz"} {
		status, body := postJSON(t, app, path, `{not json`)
		if status != fiber.StatusBadRequest {
			t.Errorf("%s: status = %d, want 400", path, status)
		}
		if !strings.Contains(string(body), "invalid_payload") {
			t.Errorf("%s: body = %s, want invalid_payload error", path, body)
		}
	}
	if n := len(storedAlerts()); n != 0 {
		t.Errorf("stored %d alerts after bad payloads, want 0", n)
	}
}

func TestHandleSigNoz_UsesSigNozSourceAndFallbackTitle(t *testing.T) {
	resetAlertStore(t)
	app := newWebhookApp()

	postJSON(t, app, "/webhooks/signoz",
		`{"alerts": [{"status": "firing", "labels": {"job": "ingest"}, "fingerprint": "s1"}]}`)

	alerts := storedAlerts()
	if len(alerts) != 1 {
		t.Fatalf("stored %d alerts, want 1", len(alerts))
	}
	if alerts[0].Source != models.AlertSourceSigNoz || alerts[0].Title != "SigNoz Alert" {
		t.Errorf("source/title = %q/%q", alerts[0].Source, alerts[0].Title)
	}
	if alerts[0].Service != "ingest" {
		t.Errorf("service = %q, want ingest (from the job label)", alerts[0].Service)
	}
}

func TestSeverityFromLabels(t *testing.T) {
	cases := map[string]models.Severity{
		"critical": models.SeverityCritical,
		"high":     models.SeverityHigh,
		"warning":  models.SeverityHigh,
		"medium":   models.SeverityMedium,
		"info":     models.SeverityMedium,
		"low":      models.SeverityLow,
		"page":     models.SeverityMedium, // unknown values default to medium
	}
	for in, want := range cases {
		if got := severityFromLabels(map[string]string{"severity": in}); got != want {
			t.Errorf("severity %q = %q, want %q", in, got, want)
		}
	}
	if got := severityFromLabels(nil); got != models.SeverityMedium {
		t.Errorf("no severity label = %q, want medium", got)
	}
}

func TestServiceFromLabels_PrefersServiceThenJobThenNamespaceThenApp(t *testing.T) {
	all := map[string]string{"service": "s", "job": "j", "namespace": "n", "app": "a"}
	if got := serviceFromLabels(all); got != "s" {
		t.Errorf("got %q, want s", got)
	}
	delete(all, "service")
	if got := serviceFromLabels(all); got != "j" {
		t.Errorf("got %q, want j", got)
	}
	delete(all, "job")
	if got := serviceFromLabels(all); got != "n" {
		t.Errorf("got %q, want n", got)
	}
	delete(all, "namespace")
	if got := serviceFromLabels(all); got != "a" {
		t.Errorf("got %q, want a", got)
	}
	if got := serviceFromLabels(map[string]string{}); got != "unknown" {
		t.Errorf("got %q, want unknown", got)
	}
}

func TestGenerateFingerprint_IsStableAndLabelSensitive(t *testing.T) {
	a := map[string]string{"alertname": "X", "service": "api"}
	b := map[string]string{"service": "api", "alertname": "X"}
	if generateFingerprint(a) != generateFingerprint(b) {
		t.Error("same labels must give the same fingerprint")
	}
	if generateFingerprint(a) == generateFingerprint(map[string]string{"alertname": "X", "service": "web"}) {
		t.Error("different label values must give different fingerprints")
	}
	// Plain concatenation would make these collide: {"a":"b=c"} vs {"a=b":"c"}.
	if generateFingerprint(map[string]string{"a": "b=c"}) == generateFingerprint(map[string]string{"a=b": "c"}) {
		t.Error("fingerprint collides when a label value contains '='")
	}
}

func TestHandleDatadog_MapsPriorityAndTags(t *testing.T) {
	resetAlertStore(t)
	app := newWebhookApp()

	status, _ := postJSON(t, app, "/webhooks/datadog", `{
		"id": "9001", "title": "High p99 latency", "body": "p99 above 2s",
		"priority": "P1", "alert_type": "warning",
		"tags": "service:checkout, env:prod,url:http://x/y,oncall"
	}`)
	if status != 200 {
		t.Fatalf("status = %d, want 200", status)
	}

	alerts := storedAlerts()
	if len(alerts) != 1 {
		t.Fatalf("stored %d alerts, want 1", len(alerts))
	}
	a := alerts[0]
	if a.Severity != models.SeverityCritical {
		t.Errorf("severity = %q, want critical (P1 beats alert_type warning)", a.Severity)
	}
	if a.Service != "checkout" {
		t.Errorf("service = %q, want checkout", a.Service)
	}
	want := map[string]string{"service": "checkout", "env": "prod", "url": "http://x/y", "oncall": "true"}
	if len(a.Labels) != len(want) {
		t.Errorf("labels = %v, want %v", a.Labels, want)
	}
	for k, v := range want {
		if a.Labels[k] != v {
			t.Errorf("label %q = %q, want %q", k, a.Labels[k], v)
		}
	}
	if _, ok := a.Labels["raw_tags"]; ok {
		t.Error("raw_tags label should no longer be set")
	}
}

func TestHandleDatadog_NumericPriorityAndTagArray(t *testing.T) {
	resetAlertStore(t)
	app := newWebhookApp()

	postJSON(t, app, "/webhooks/datadog",
		`{"id": "9002", "priority": 4, "tags": ["service:search", "env:prod"]}`)

	alerts := storedAlerts()
	if len(alerts) != 1 {
		t.Fatalf("stored %d alerts, want 1", len(alerts))
	}
	if alerts[0].Severity != models.SeverityLow {
		t.Errorf("severity = %q, want low (priority 4)", alerts[0].Severity)
	}
	if alerts[0].Service != "search" || alerts[0].Labels["env"] != "prod" {
		t.Errorf("service/labels = %q/%v", alerts[0].Service, alerts[0].Labels)
	}
}

func TestHandleDatadog_NoPriorityOrTagsDefaultsToMedium(t *testing.T) {
	resetAlertStore(t)
	app := newWebhookApp()

	postJSON(t, app, "/webhooks/datadog", `{"id": "9003"}`)

	alerts := storedAlerts()
	if len(alerts) != 1 {
		t.Fatalf("stored %d alerts, want 1", len(alerts))
	}
	if alerts[0].Severity != models.SeverityMedium {
		t.Errorf("severity = %q, want medium", alerts[0].Severity)
	}
	if len(alerts[0].Labels) != 0 {
		t.Errorf("labels = %v, want none", alerts[0].Labels)
	}
}

func TestDatadogSeverity(t *testing.T) {
	cases := []struct {
		priority, alertType string
		want                models.Severity
	}{
		{"P1", "", models.SeverityCritical},
		{" p2 ", "info", models.SeverityHigh},
		{"P3", "error", models.SeverityMedium},
		{"normal", "", models.SeverityMedium},
		{"P4", "error", models.SeverityLow},
		{"P5", "", models.SeverityLow},
		{"low", "", models.SeverityLow},
		{"", "error", models.SeverityHigh},
		{"", "WARNING", models.SeverityMedium},
		{"", "success", models.SeverityLow},
		{"P9", "snapshot", models.SeverityMedium},
		{"", "", models.SeverityMedium},
	}
	for _, c := range cases {
		if got := datadogSeverity(c.priority, c.alertType); got != c.want {
			t.Errorf("datadogSeverity(%q, %q) = %q, want %q", c.priority, c.alertType, got, c.want)
		}
	}
}

func TestDatadogTags_FirstValueWinsAndSkipsEmpty(t *testing.T) {
	got := datadogTags("env:a,, env:b ,:novalue,team: core")
	want := map[string]string{"env": "a", "team": "core"}
	if len(got) != len(want) {
		t.Fatalf("labels = %v, want %v", got, want)
	}
	for k, v := range want {
		if got[k] != v {
			t.Errorf("label %q = %q, want %q", k, got[k], v)
		}
	}
	if n := len(datadogTags(nil)); n != 0 {
		t.Errorf("nil tags gave %d labels, want 0", n)
	}
}

func TestHandleDatadog_RecoveryResolvesTheSameAlert(t *testing.T) {
	resetAlertStore(t)
	app := newWebhookApp()

	postJSON(t, app, "/webhooks/datadog", `{"id": "m-77", "title": "[Triggered] High error rate",
		"alert_type": "error", "alert_transition": "Triggered", "tags": "service:checkout"}`)
	if got := storedAlerts(); len(got) != 1 || got[0].Status != models.AlertStatusFiring {
		t.Fatalf("after trigger got %+v, want one firing alert", got)
	}

	postJSON(t, app, "/webhooks/datadog", `{"id": "m-77", "title": "[Recovered] High error rate",
		"alert_type": "success", "alert_transition": "Recovered", "tags": "service:checkout"}`)
	alerts := storedAlerts()
	if len(alerts) != 1 {
		t.Fatalf("after recovery stored %d alerts, want 1", len(alerts))
	}
	if alerts[0].Status != models.AlertStatusResolved {
		t.Errorf("status = %q, want resolved", alerts[0].Status)
	}
	if alerts[0].EndsAt == nil {
		t.Error("EndsAt is nil, want the recovery time")
	}

	// The monitor triggering again reopens it and clears the end time.
	postJSON(t, app, "/webhooks/datadog", `{"id": "m-77", "title": "[Triggered] High error rate",
		"alert_transition": "Triggered"}`)
	alerts = storedAlerts()
	if len(alerts) != 1 || alerts[0].Status != models.AlertStatusFiring || alerts[0].EndsAt != nil {
		t.Errorf("after re-trigger got %+v, want one firing alert with no EndsAt", alerts)
	}
}

func TestHandleDatadog_RecoveryFromTitleAloneWithoutTransition(t *testing.T) {
	resetAlertStore(t)
	app := newWebhookApp()

	postJSON(t, app, "/webhooks/datadog", `{"id": "m-8", "title": "Disk full"}`)
	postJSON(t, app, "/webhooks/datadog", `{"id": "m-8", "title": "[Recovered] Disk full"}`)
	alerts := storedAlerts()
	if len(alerts) != 1 || alerts[0].Status != models.AlertStatusResolved {
		t.Errorf("got %+v, want one resolved alert", alerts)
	}
}

func TestDatadogRecovered(t *testing.T) {
	cases := []struct {
		transition, title string
		want              bool
	}{
		{"Recovered", "x", true},
		{" recovered ", "x", true},
		{"", "[Recovered] disk", true},
		{"", " [recovered] disk", true},
		{"Triggered", "[Triggered] disk", false},
		{"Warn", "[Warn] disk", false},
		{"", "disk recovered later", false},
		{"", "", false},
	}
	for _, c := range cases {
		if got := datadogRecovered(c.transition, c.title); got != c.want {
			t.Errorf("datadogRecovered(%q, %q) = %v, want %v", c.transition, c.title, got, c.want)
		}
	}
}
