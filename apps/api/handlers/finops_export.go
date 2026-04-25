package handlers

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"

	"github.com/junegu/aegis/api/internal/excel"
	"github.com/junegu/aegis/api/models"
)

// Export-format constants. Anything else returns 400.
const (
	formatCSV  = "csv"
	formatXLSX = "xlsx"
)

// writeExport sets the right content headers and pipes either CSV bytes or
// an XLSX binary onto the Fiber response. Filename pattern:
//
//	aegis-finops-<view>-<YYYY-MM-DD>.{csv,xlsx}
//
// We never embed account IDs or other identifiers in the filename.
func writeExport(c *fiber.Ctx, format, view, sheet string, header []string, rows []excel.Row) error {
	date := time.Now().UTC().Format("2006-01-02")
	switch format {
	case formatCSV:
		filename := fmt.Sprintf("aegis-finops-%s-%s.csv", view, date)
		c.Set(fiber.HeaderContentType, excel.MimeCSV)
		c.Set(fiber.HeaderContentDisposition, fmt.Sprintf("attachment; filename=%q", filename))
		// Write header + rows directly to the Fiber response body writer.
		// Fiber's BodyWriter flushes onto the underlying fasthttp response,
		// so we don't buffer the whole payload in a separate []byte.
		return excel.WriteCSV(c.Response().BodyWriter(), header, rows)
	case formatXLSX:
		filename := fmt.Sprintf("aegis-finops-%s-%s.xlsx", view, date)
		data, err := excel.WriteXLSX(sheet, header, rows)
		if err != nil {
			return fiber.NewError(fiber.StatusInternalServerError, fmt.Sprintf("xlsx build failed: %v", err))
		}
		c.Set(fiber.HeaderContentType, excel.MimeXLSX)
		c.Set(fiber.HeaderContentDisposition, fmt.Sprintf("attachment; filename=%q", filename))
		return c.Send(data)
	default:
		return fiber.NewError(fiber.StatusBadRequest, fmt.Sprintf("unsupported format %q (use csv or xlsx)", format))
	}
}

// parseExportFormat returns the requested format, defaulting to csv.
func parseExportFormat(c *fiber.Ctx) string {
	f := strings.ToLower(strings.TrimSpace(c.Query("format", formatCSV)))
	return f
}

// -----------------------------------------------------------------------------
// Cost export
// -----------------------------------------------------------------------------

// ExportFinOpsCosts streams daily cost entries.
//
//	GET /api/v1/finops/export/costs?format=csv|xlsx
//	   &start=YYYY-MM-DD&end=YYYY-MM-DD
//	   &account=...&group_by=service|account|region
//
// When group_by is supplied the rows are aggregated by that dimension. Missing
// start/end default to the last 30 days of available data.
func ExportFinOpsCosts(c *fiber.Ctx) error {
	format := parseExportFormat(c)
	start := c.Query("start")
	end := c.Query("end")
	account := c.Query("account")
	groupBy := strings.ToLower(c.Query("group_by"))

	// Default to the full 30-day window when caller omits bounds.
	if start == "" || end == "" {
		start, end = defaultCostWindow(finopsCostEntries)
	}

	filtered := make([]models.CostEntry, 0, len(finopsCostEntries))
	for _, e := range finopsCostEntries {
		if e.Date < start || e.Date > end {
			continue
		}
		if account != "" && !strings.EqualFold(e.Account, account) {
			continue
		}
		filtered = append(filtered, e)
	}

	switch groupBy {
	case "service", "account", "region":
		return writeExport(c, format, "costs-by-"+groupBy, "Costs",
			[]string{titleCase(groupBy), "Total (USD)", "Currency", "Entries"},
			aggregateCostEntries(filtered, groupBy),
		)
	case "", "date", "day":
		// Ungrouped: one row per (date, service) entry.
		header := []string{"Date", "Service", "Account", "Provider", "Amount", "Currency", "Env", "Team", "Region"}
		rows := make([]excel.Row, 0, len(filtered))
		// Deterministic order: by date, then service.
		sort.Slice(filtered, func(i, j int) bool {
			if filtered[i].Date == filtered[j].Date {
				return filtered[i].Service < filtered[j].Service
			}
			return filtered[i].Date < filtered[j].Date
		})
		for _, e := range filtered {
			rows = append(rows, excel.Row{
				e.Date, e.Service, e.Account, e.Provider,
				e.Amount, e.Currency,
				e.Tags["env"], e.Tags["team"], e.Tags["region"],
			})
		}
		return writeExport(c, format, "costs", "Costs", header, rows)
	default:
		return fiber.NewError(fiber.StatusBadRequest,
			fmt.Sprintf("unsupported group_by %q (use service, account, or region)", groupBy))
	}
}

// aggregateCostEntries sums amounts and counts rows for a given dimension.
func aggregateCostEntries(entries []models.CostEntry, dim string) []excel.Row {
	type bucket struct {
		total   float64
		count   int
		currency string
	}
	buckets := map[string]*bucket{}
	for _, e := range entries {
		var key string
		switch dim {
		case "service":
			key = e.Service
		case "account":
			key = e.Account
		case "region":
			key = e.Tags["region"]
			if key == "" {
				key = "unknown"
			}
		}
		b := buckets[key]
		if b == nil {
			b = &bucket{currency: e.Currency}
			buckets[key] = b
		}
		b.total += e.Amount
		b.count++
	}
	keys := make([]string, 0, len(buckets))
	for k := range buckets {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	rows := make([]excel.Row, 0, len(buckets))
	for _, k := range keys {
		b := buckets[k]
		rows = append(rows, excel.Row{
			k, roundCents(b.total), b.currency, b.count,
		})
	}
	return rows
}

// defaultCostWindow returns the min and max date found in entries, so the
// export matches the data the dashboard is actually showing.
func defaultCostWindow(entries []models.CostEntry) (string, string) {
	if len(entries) == 0 {
		now := time.Now().UTC().Format("2006-01-02")
		return now, now
	}
	min, max := entries[0].Date, entries[0].Date
	for _, e := range entries {
		if e.Date < min {
			min = e.Date
		}
		if e.Date > max {
			max = e.Date
		}
	}
	return min, max
}

// -----------------------------------------------------------------------------
// Budgets export
// -----------------------------------------------------------------------------

// ExportFinOpsBudgets returns one row per tracked budget.
//
//	GET /api/v1/finops/export/budgets?format=csv|xlsx
func ExportFinOpsBudgets(c *fiber.Ctx) error {
	format := parseExportFormat(c)

	header := []string{
		"Budget ID", "Name", "Team", "Period",
		"Limit (USD)", "Current Spend (USD)", "Projected (USD)",
		"Utilization %", "Status",
	}
	rows := make([]excel.Row, 0, len(finopsBudgets))
	for _, b := range finopsBudgets {
		util := 0.0
		if b.Limit > 0 {
			util = (b.CurrentSpend / b.Limit) * 100.0
		}
		rows = append(rows, excel.Row{
			b.ID, b.Name, b.Team, b.Period,
			roundCents(b.Limit), roundCents(b.CurrentSpend), roundCents(b.ProjectedSpend),
			roundCents(util), string(b.Status),
		})
	}
	return writeExport(c, format, "budgets", "Budgets", header, rows)
}

// -----------------------------------------------------------------------------
// Anomalies export
// -----------------------------------------------------------------------------

// ExportFinOpsAnomalies returns the anomalies detected within the lookback window.
//
//	GET /api/v1/finops/export/anomalies?format=csv|xlsx&lookback=30
func ExportFinOpsAnomalies(c *fiber.Ctx) error {
	format := parseExportFormat(c)
	lookbackDays := 30
	if raw := c.Query("lookback"); raw != "" {
		if n, err := strconv.Atoi(raw); err == nil && n > 0 {
			lookbackDays = n
		}
	}
	cutoff := time.Now().UTC().Add(-time.Duration(lookbackDays) * 24 * time.Hour)

	header := []string{
		"Anomaly ID", "Service", "Severity", "Detected At (UTC)",
		"Expected (USD)", "Actual (USD)", "Deviation %",
		"Description",
	}
	rows := make([]excel.Row, 0, len(finopsCostAnomalies))
	for _, a := range finopsCostAnomalies {
		if a.DetectedAt.Before(cutoff) {
			continue
		}
		rows = append(rows, excel.Row{
			a.ID, a.Service, string(a.Severity),
			a.DetectedAt.UTC().Format(time.RFC3339),
			roundCents(a.ExpectedCost), roundCents(a.ActualCost), roundCents(a.DeviationPercent),
			a.Description,
		})
	}
	return writeExport(c, format, "anomalies", "Anomalies", header, rows)
}

// -----------------------------------------------------------------------------
// Kubernetes allocation export
// -----------------------------------------------------------------------------

// ExportFinOpsKubernetes returns Kubernetes cost allocation rows. The
// window and aggregate params are accepted for forward-compatibility — the
// mock data only exposes a per-namespace slice today.
//
//	GET /api/v1/finops/export/k8s?format=csv|xlsx&window=7d&aggregate=namespace|controller|pod
func ExportFinOpsKubernetes(c *fiber.Ctx) error {
	format := parseExportFormat(c)
	aggregate := strings.ToLower(c.Query("aggregate", "namespace"))
	window := c.Query("window", "7d")

	switch aggregate {
	case "", "namespace", "controller", "pod":
		// fine — single shape today
	default:
		return fiber.NewError(fiber.StatusBadRequest,
			fmt.Sprintf("unsupported aggregate %q (use namespace, controller, or pod)", aggregate))
	}

	header := []string{
		"Namespace", "Window", "Pods",
		"CPU Cost (USD)", "Memory Cost (USD)", "Storage Cost (USD)",
		"Total Cost (USD)", "Idle %",
	}
	rows := make([]excel.Row, 0, len(finopsKubernetesCosts))
	for _, k := range finopsKubernetesCosts {
		rows = append(rows, excel.Row{
			k.Namespace, window, k.Pods,
			roundCents(k.CPUCost), roundCents(k.MemoryCost), roundCents(k.StorageCost),
			roundCents(k.TotalCost), roundCents(k.IdlePercent),
		})
	}
	return writeExport(c, format, "k8s-"+aggregate, "K8sAllocation", header, rows)
}

// -----------------------------------------------------------------------------
// small helpers
// -----------------------------------------------------------------------------

// roundCents rounds to 2dp so USD amounts don't bleed float noise into the
// spreadsheet (e.g. 180.00000001).
func roundCents(v float64) float64 {
	return float64(int64(v*100+0.5)) / 100
}

func titleCase(s string) string {
	if s == "" {
		return s
	}
	return strings.ToUpper(s[:1]) + s[1:]
}
