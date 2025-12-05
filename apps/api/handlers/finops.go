package handlers

import (
	"strings"

	"github.com/gofiber/fiber/v2"

	"github.com/junegu/aegis/api/mock"
	"github.com/junegu/aegis/api/models"
)

// finops data loaded once from mock generators.
var (
	finopsCostEntries    []models.CostEntry
	finopsCostSummary    models.CostSummary
	finopsCostTrends     []models.CostTrend
	finopsCostAnomalies  []models.CostAnomaly
	finopsBudgets        []models.Budget
	finopsKubernetesCosts []models.KubernetesCost
)

func init() {
	finopsCostEntries = mock.GenerateMockCostEntries()
	finopsCostSummary = mock.GenerateMockCostSummary()
	finopsCostTrends = mock.GenerateMockCostTrends()
	finopsCostAnomalies = mock.GenerateMockCostAnomalies()
	finopsBudgets = mock.GenerateMockBudgets()
	finopsKubernetesCosts = mock.GenerateMockKubernetesCosts()
}

// GetFinOpsSummary returns a monthly cost summary with month-over-month comparison.
//
//	GET /api/v1/finops/summary
func GetFinOpsSummary(c *fiber.Ctx) error {
	return c.JSON(finopsCostSummary)
}

// GetFinOpsCosts returns cost entries with optional filters.
//
//	GET /api/v1/finops/costs?provider=...&service=...&team=...&start=...&end=...
func GetFinOpsCosts(c *fiber.Ctx) error {
	provider := c.Query("provider")
	service := c.Query("service")
	team := c.Query("team")
	start := c.Query("start") // YYYY-MM-DD
	end := c.Query("end")     // YYYY-MM-DD

	filtered := make([]models.CostEntry, 0, len(finopsCostEntries))
	for _, entry := range finopsCostEntries {
		if provider != "" && !strings.EqualFold(entry.Provider, provider) {
			continue
		}
		if service != "" && !strings.EqualFold(entry.Service, service) {
			continue
		}
		if team != "" && entry.Tags["team"] != team {
			continue
		}
		if start != "" && entry.Date < start {
			continue
		}
		if end != "" && entry.Date > end {
			continue
		}
		filtered = append(filtered, entry)
	}

	return c.JSON(fiber.Map{
		"data":  filtered,
		"total": len(filtered),
	})
}

// GetFinOpsTrends returns cost trend data for charting.
//
//	GET /api/v1/finops/trends?granularity=daily|weekly|monthly
func GetFinOpsTrends(c *fiber.Ctx) error {
	// granularity is accepted but mock always returns daily data.
	return c.JSON(fiber.Map{
		"data":        finopsCostTrends,
		"granularity": c.Query("granularity", "daily"),
		"total":       len(finopsCostTrends),
	})
}

// GetFinOpsAnomalies returns detected cost anomalies.
//
//	GET /api/v1/finops/anomalies
func GetFinOpsAnomalies(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"data":  finopsCostAnomalies,
		"total": len(finopsCostAnomalies),
	})
}

// GetFinOpsBudgets returns budget tracking status for all teams.
//
//	GET /api/v1/finops/budgets
func GetFinOpsBudgets(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"data":  finopsBudgets,
		"total": len(finopsBudgets),
	})
}

// GetFinOpsKubernetes returns Kubernetes namespace cost allocation.
//
//	GET /api/v1/finops/kubernetes
func GetFinOpsKubernetes(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"data":  finopsKubernetesCosts,
		"total": len(finopsKubernetesCosts),
	})
}
