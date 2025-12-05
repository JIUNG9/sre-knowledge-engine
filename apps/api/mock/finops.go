package mock

import (
	"fmt"
	"math"
	"math/rand"
	"time"

	"github.com/junegu/aegis/api/models"
)

// awsServices maps AWS services to their approximate monthly cost targets.
var awsServices = map[string]float64{
	"Amazon EC2":     3500.0,
	"Amazon RDS":     2800.0,
	"Amazon S3":      1200.0,
	"Amazon EKS":     3500.0,
	"AWS Lambda":     450.0,
	"Other Services": 1000.0,
}

// teamBudgets maps teams to their monthly spending limits.
var teamBudgets = map[string]float64{
	"platform":  6000.0,
	"identity":  2500.0,
	"payments":  2800.0,
	"messaging": 1500.0,
}

// GenerateMockCostEntries generates 30 days of realistic AWS cost data.
func GenerateMockCostEntries() []models.CostEntry {
	now := time.Now().UTC()
	entries := make([]models.CostEntry, 0, 30*len(awsServices))

	for day := 0; day < 30; day++ {
		date := now.AddDate(0, 0, -(29 - day))
		dateStr := date.Format("2006-01-02")

		for service, monthlyTarget := range awsServices {
			// Daily cost = monthly / 30 with some variance (+/- 15%).
			dailyBase := monthlyTarget / 30.0
			variance := dailyBase * 0.15
			amount := dailyBase + (rand.Float64()*2-1)*variance
			amount = math.Round(amount*100) / 100

			entry := models.CostEntry{
				Date:     dateStr,
				Service:  service,
				Account:  pickAccount(service),
				Provider: "AWS",
				Amount:   amount,
				Currency: "USD",
				Tags: map[string]string{
					"env":    "production",
					"team":   pickTeamForService(service),
					"region": randomRegion(),
				},
			}
			entries = append(entries, entry)
		}
	}

	return entries
}

// GenerateMockCostSummary returns a cost summary with month-over-month comparison.
func GenerateMockCostSummary() models.CostSummary {
	now := time.Now().UTC()
	period := now.Format("2006-01")

	totalCost := 0.0
	costByService := make(map[string]float64)
	for svc, monthlyTarget := range awsServices {
		// Slight variance from target.
		actual := monthlyTarget * (0.95 + rand.Float64()*0.10)
		actual = math.Round(actual*100) / 100
		costByService[svc] = actual
		totalCost += actual
	}
	totalCost = math.Round(totalCost*100) / 100

	// Previous period was ~5% lower.
	previousPeriod := totalCost * 0.95
	previousPeriod = math.Round(previousPeriod*100) / 100
	changePercent := math.Round(((totalCost-previousPeriod)/previousPeriod)*10000) / 100

	costByTeam := map[string]float64{
		"platform":  math.Round((costByService["Amazon EC2"]*0.4+costByService["Amazon EKS"]+costByService["Other Services"]*0.5)*100) / 100,
		"identity":  math.Round((costByService["Amazon EC2"]*0.2+costByService["Amazon RDS"]*0.3)*100) / 100,
		"payments":  math.Round((costByService["Amazon EC2"]*0.25+costByService["Amazon RDS"]*0.5+costByService["AWS Lambda"]*0.6)*100) / 100,
		"messaging": math.Round((costByService["Amazon EC2"]*0.15+costByService["Amazon RDS"]*0.2+costByService["Amazon S3"]*0.3+costByService["AWS Lambda"]*0.4)*100) / 100,
	}

	return models.CostSummary{
		Period:         period,
		TotalCost:      totalCost,
		PreviousPeriod: previousPeriod,
		ChangePercent:  changePercent,
		CostByProvider: map[string]float64{"AWS": totalCost},
		CostByService:  costByService,
		CostByTeam:     costByTeam,
	}
}

// GenerateMockCostTrends generates daily cost trend data for charting over the past 30 days.
func GenerateMockCostTrends() []models.CostTrend {
	now := time.Now().UTC()
	trends := make([]models.CostTrend, 0, 30)

	for day := 0; day < 30; day++ {
		date := now.AddDate(0, 0, -(29 - day))
		dateStr := date.Format("2006-01-02")

		// Total daily cost across all services.
		dailyTotal := 0.0
		for _, monthlyTarget := range awsServices {
			dailyBase := monthlyTarget / 30.0
			variance := dailyBase * 0.15
			dailyTotal += dailyBase + (rand.Float64()*2-1)*variance
		}
		dailyTotal = math.Round(dailyTotal*100) / 100

		trends = append(trends, models.CostTrend{
			Date:     dateStr,
			Amount:   dailyTotal,
			Provider: "AWS",
		})
	}

	return trends
}

// GenerateMockCostAnomalies returns 2 realistic cost anomalies.
func GenerateMockCostAnomalies() []models.CostAnomaly {
	now := time.Now().UTC()

	return []models.CostAnomaly{
		{
			ID:               "anomaly-001",
			Service:          "Amazon EC2",
			ExpectedCost:     116.67,
			ActualCost:       198.42,
			DeviationPercent: 70.1,
			Severity:         models.AnomalySeverityCritical,
			DetectedAt:       now.Add(-6 * time.Hour),
			Description:      "EC2 spend surged 70% above the 7-day rolling average. Root cause: auto-scaling group in us-east-1 launched 12 additional c5.2xlarge instances during a traffic spike that did not scale down due to a misconfigured cooldown period.",
		},
		{
			ID:               "anomaly-002",
			Service:          "Amazon S3",
			ExpectedCost:     40.00,
			ActualCost:       58.73,
			DeviationPercent: 46.8,
			Severity:         models.AnomalySeverityWarning,
			DetectedAt:       now.Add(-18 * time.Hour),
			Description:      "S3 request costs increased 47% over baseline. A batch ETL job in the data-pipeline account is issuing excessive LIST and GET operations against the analytics bucket, likely due to a missing pagination cursor in the export script.",
		},
	}
}

// GenerateMockBudgets returns 4 team budgets with realistic spend tracking.
func GenerateMockBudgets() []models.Budget {
	now := time.Now().UTC()
	dayOfMonth := float64(now.Day())
	daysInMonth := float64(daysInCurrentMonth(now))
	monthProgress := dayOfMonth / daysInMonth

	budgets := make([]models.Budget, 0, len(teamBudgets))

	budgetData := []struct {
		id       string
		name     string
		team     string
		limit    float64
		spendPct float64 // percentage of limit spent so far
		status   models.BudgetStatus
	}{
		{
			id:       "budget-001",
			name:     "Platform Infrastructure",
			team:     "platform",
			limit:    teamBudgets["platform"],
			spendPct: monthProgress * 0.92, // slightly under pace
			status:   models.BudgetStatusUnder,
		},
		{
			id:       "budget-002",
			name:     "Identity Services",
			team:     "identity",
			limit:    teamBudgets["identity"],
			spendPct: monthProgress * 1.08, // slightly over pace
			status:   models.BudgetStatusAtRisk,
		},
		{
			id:       "budget-003",
			name:     "Payment Processing",
			team:     "payments",
			limit:    teamBudgets["payments"],
			spendPct: monthProgress * 1.25, // significantly over pace
			status:   models.BudgetStatusExceeded,
		},
		{
			id:       "budget-004",
			name:     "Messaging Platform",
			team:     "messaging",
			limit:    teamBudgets["messaging"],
			spendPct: monthProgress * 0.85, // well under pace
			status:   models.BudgetStatusUnder,
		},
	}

	for _, bd := range budgetData {
		currentSpend := math.Round(bd.limit*bd.spendPct*100) / 100
		projectedSpend := math.Round((currentSpend/monthProgress)*100) / 100

		budgets = append(budgets, models.Budget{
			ID:             bd.id,
			Name:           bd.name,
			Team:           bd.team,
			Limit:          bd.limit,
			CurrentSpend:   currentSpend,
			ProjectedSpend: projectedSpend,
			Period:         fmt.Sprintf("%s (monthly)", time.Now().Format("2006-01")),
			Status:         bd.status,
		})
	}

	return budgets
}

// GenerateMockKubernetesCosts returns cost allocation data for 5 K8s namespaces.
func GenerateMockKubernetesCosts() []models.KubernetesCost {
	return []models.KubernetesCost{
		{
			Namespace:   "production",
			Pods:        42,
			CPUCost:     890.50,
			MemoryCost:  645.30,
			StorageCost: 210.00,
			TotalCost:   1745.80,
			IdlePercent: 12.5,
		},
		{
			Namespace:   "staging",
			Pods:        18,
			CPUCost:     312.40,
			MemoryCost:  198.60,
			StorageCost: 85.00,
			TotalCost:   596.00,
			IdlePercent: 35.2,
		},
		{
			Namespace:   "monitoring",
			Pods:        8,
			CPUCost:     245.00,
			MemoryCost:  380.20,
			StorageCost: 150.00,
			TotalCost:   775.20,
			IdlePercent: 18.0,
		},
		{
			Namespace:   "data-pipeline",
			Pods:        12,
			CPUCost:     178.30,
			MemoryCost:  112.50,
			StorageCost: 95.00,
			TotalCost:   385.80,
			IdlePercent: 28.4,
		},
		{
			Namespace:   "ci-runners",
			Pods:        6,
			CPUCost:     98.20,
			MemoryCost:  65.40,
			StorageCost: 30.00,
			TotalCost:   193.60,
			IdlePercent: 52.0,
		},
	}
}

// pickAccount returns a realistic AWS account ID for a given service.
func pickAccount(service string) string {
	switch service {
	case "Amazon EKS", "Amazon EC2":
		return "111122223333"
	case "Amazon RDS":
		return "444455556666"
	case "Amazon S3":
		return "777788889999"
	default:
		return "111122223333"
	}
}

// pickTeamForService maps AWS services to the primary owning team.
func pickTeamForService(service string) string {
	switch service {
	case "Amazon EKS":
		return "platform"
	case "Amazon EC2":
		// EC2 is shared across teams.
		teams := []string{"platform", "identity", "payments", "messaging"}
		return teams[rand.Intn(len(teams))]
	case "Amazon RDS":
		return "payments"
	case "Amazon S3":
		return "messaging"
	case "AWS Lambda":
		return "payments"
	default:
		return "platform"
	}
}

// daysInCurrentMonth returns the number of days in the given time's month.
func daysInCurrentMonth(t time.Time) int {
	year, month, _ := t.Date()
	return time.Date(year, month+1, 0, 0, 0, 0, 0, t.Location()).Day()
}
