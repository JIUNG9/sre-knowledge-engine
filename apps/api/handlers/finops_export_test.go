package handlers

import (
	"bytes"
	"encoding/csv"
	"io"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gofiber/fiber/v2"
	"github.com/xuri/excelize/v2"
)

// newTestApp builds a minimal Fiber app with the FinOps export routes
// wired. We don't depend on the real routes.Setup because it pulls in
// auth middleware and other global state we don't need here.
func newTestApp(t *testing.T) *fiber.App {
	t.Helper()
	app := fiber.New(fiber.Config{DisableStartupMessage: true})
	g := app.Group("/api/v1/finops/export")
	g.Get("/costs", ExportFinOpsCosts)
	g.Get("/budgets", ExportFinOpsBudgets)
	g.Get("/anomalies", ExportFinOpsAnomalies)
	g.Get("/k8s", ExportFinOpsKubernetes)
	return app
}

func doGET(t *testing.T, app *fiber.App, url string) (status int, headers map[string]string, body []byte) {
	t.Helper()
	req := httptest.NewRequest(fiber.MethodGet, url, nil)
	resp, err := app.Test(req, -1)
	if err != nil {
		t.Fatalf("app.Test(%s) error: %v", url, err)
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	h := map[string]string{}
	for k, v := range resp.Header {
		if len(v) > 0 {
			h[k] = v[0]
		}
	}
	return resp.StatusCode, h, b
}

// Case 1: CSV happy-path. Costs export must return 200, a CSV content-type,
// a correctly-formed attachment filename, a header row, and at least one
// data row given the mock generator produces 30 days of data.
func TestExportFinOpsCosts_CSV(t *testing.T) {
	app := newTestApp(t)

	status, h, body := doGET(t, app, "/api/v1/finops/export/costs?format=csv")
	if status != fiber.StatusOK {
		t.Fatalf("status = %d, want 200 (body: %s)", status, string(body))
	}
	ct := h["Content-Type"]
	if !strings.HasPrefix(ct, "text/csv") {
		t.Errorf("Content-Type = %q, want text/csv*", ct)
	}
	cd := h["Content-Disposition"]
	if !strings.Contains(cd, "attachment;") || !strings.Contains(cd, "aegis-finops-costs-") || !strings.HasSuffix(cd, `.csv"`) {
		t.Errorf("Content-Disposition = %q, want attachment w/ aegis-finops-costs-<date>.csv", cd)
	}

	// Parse as CSV and check the header + that we got data rows.
	r := csv.NewReader(bytes.NewReader(body))
	records, err := r.ReadAll()
	if err != nil {
		t.Fatalf("csv parse: %v", err)
	}
	if len(records) < 2 {
		t.Fatalf("expected header + at least 1 row, got %d records", len(records))
	}
	wantHeader := []string{"Date", "Service", "Account", "Provider", "Amount", "Currency", "Env", "Team", "Region"}
	for i, col := range wantHeader {
		if records[0][i] != col {
			t.Errorf("header[%d] = %q, want %q", i, records[0][i], col)
		}
	}
}

// Case 2: XLSX happy-path. Budgets export must be a valid .xlsx file that
// excelize can re-open, with the header row present.
func TestExportFinOpsBudgets_XLSX(t *testing.T) {
	app := newTestApp(t)

	status, h, body := doGET(t, app, "/api/v1/finops/export/budgets?format=xlsx")
	if status != fiber.StatusOK {
		t.Fatalf("status = %d, want 200 (body len %d)", status, len(body))
	}
	ct := h["Content-Type"]
	if ct != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" {
		t.Errorf("Content-Type = %q, want xlsx mime", ct)
	}
	cd := h["Content-Disposition"]
	if !strings.Contains(cd, "aegis-finops-budgets-") || !strings.HasSuffix(cd, `.xlsx"`) {
		t.Errorf("Content-Disposition = %q, want aegis-finops-budgets-<date>.xlsx", cd)
	}

	f, err := excelize.OpenReader(bytes.NewReader(body))
	if err != nil {
		t.Fatalf("open xlsx: %v", err)
	}
	defer func() { _ = f.Close() }()

	sheet := f.GetSheetName(0)
	rows, err := f.GetRows(sheet)
	if err != nil {
		t.Fatalf("read rows: %v", err)
	}
	if len(rows) < 2 {
		t.Fatalf("expected header + at least 1 data row, got %d", len(rows))
	}
	if rows[0][0] != "Budget ID" {
		t.Errorf("header[0] = %q, want Budget ID", rows[0][0])
	}
}

// Case 3: invalid format must return 400.
func TestExportFinOpsCosts_InvalidFormat(t *testing.T) {
	app := newTestApp(t)
	status, _, body := doGET(t, app, "/api/v1/finops/export/costs?format=pdf")
	if status != fiber.StatusBadRequest {
		t.Fatalf("status = %d, want 400 (body: %s)", status, string(body))
	}
	if !strings.Contains(string(body), "unsupported format") {
		t.Errorf("body = %q, want to mention 'unsupported format'", string(body))
	}
}

// Case 4: missing start/end must not error — the handler should fall back
// to the min/max dates in the data set and still return data.
func TestExportFinOpsCosts_DefaultDateWindow(t *testing.T) {
	app := newTestApp(t)
	status, _, body := doGET(t, app, "/api/v1/finops/export/costs")
	if status != fiber.StatusOK {
		t.Fatalf("status = %d, want 200", status)
	}
	// Header + 1+ rows, same sanity check as case 1.
	r := csv.NewReader(bytes.NewReader(body))
	records, err := r.ReadAll()
	if err != nil {
		t.Fatalf("csv parse: %v", err)
	}
	if len(records) < 2 {
		t.Fatalf("default window returned no data rows (%d records)", len(records))
	}
}

// Bonus case: k8s aggregate and anomalies endpoints should also 200 on the
// happy path — cheap coverage on the remaining handlers.
func TestExportFinOpsK8sAndAnomalies(t *testing.T) {
	app := newTestApp(t)

	// k8s xlsx
	status, h, body := doGET(t, app, "/api/v1/finops/export/k8s?format=xlsx&aggregate=namespace&window=7d")
	if status != fiber.StatusOK {
		t.Fatalf("k8s status = %d (body len %d)", status, len(body))
	}
	if !strings.Contains(h["Content-Disposition"], "aegis-finops-k8s-namespace-") {
		t.Errorf("k8s Content-Disposition = %q", h["Content-Disposition"])
	}

	// anomalies csv, wide lookback so any generated anomaly matches.
	status, h, body = doGET(t, app, "/api/v1/finops/export/anomalies?format=csv&lookback=3650")
	if status != fiber.StatusOK {
		t.Fatalf("anomalies status = %d", status)
	}
	if !strings.Contains(h["Content-Disposition"], "aegis-finops-anomalies-") {
		t.Errorf("anomalies Content-Disposition = %q", h["Content-Disposition"])
	}
	// At least one header line should be there.
	if !strings.HasPrefix(string(body), "Anomaly ID,") {
		t.Errorf("anomalies body should start with header, got: %q", firstLine(string(body)))
	}
}

func firstLine(s string) string {
	if i := strings.IndexByte(s, '\n'); i >= 0 {
		return s[:i]
	}
	return s
}
