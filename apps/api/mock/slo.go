package mock

import (
	"math"
	"math/rand"
	"time"

	"github.com/junegu/aegis/api/models"
)

// GenerateMockSLOs returns 10 realistic SLOs across 6 services with varied statuses.
func GenerateMockSLOs() []models.SLO {
	now := time.Now().UTC()

	slos := []models.SLO{
		// --- api-gateway (2 SLOs) ---
		{
			ID:          "slo-001",
			ServiceID:   "api-gateway",
			Name:        "Gateway Availability",
			Description: "Percentage of successful (non-5xx) responses across all gateway endpoints",
			Target:      99.99,
			Current:     99.97,
			Window:      "30d",
			SLIType:     models.SLITypeAvailability,
			Status:      models.SLOStatusAtRisk,
			CreatedAt:   now.AddDate(0, -6, 0),
			UpdatedAt:   now.Add(-15 * time.Minute),
		},
		{
			ID:          "slo-002",
			ServiceID:   "api-gateway",
			Name:        "Gateway P99 Latency",
			Description: "99th percentile response time must remain below 200ms",
			Target:      99.5,
			Current:     99.72,
			Window:      "30d",
			SLIType:     models.SLITypeLatency,
			Status:      models.SLOStatusMeeting,
			CreatedAt:   now.AddDate(0, -6, 0),
			UpdatedAt:   now.Add(-10 * time.Minute),
		},
		// --- auth-service (1 SLO) ---
		{
			ID:          "slo-003",
			ServiceID:   "auth-service",
			Name:        "Auth Service Availability",
			Description: "Authentication and authorization endpoints must remain available",
			Target:      99.95,
			Current:     99.98,
			Window:      "30d",
			SLIType:     models.SLITypeAvailability,
			Status:      models.SLOStatusMeeting,
			CreatedAt:   now.AddDate(0, -5, 0),
			UpdatedAt:   now.Add(-5 * time.Minute),
		},
		// --- user-service (2 SLOs) ---
		{
			ID:          "slo-004",
			ServiceID:   "user-service",
			Name:        "User Service Availability",
			Description: "Core user CRUD and profile endpoints must remain available",
			Target:      99.9,
			Current:     99.95,
			Window:      "30d",
			SLIType:     models.SLITypeAvailability,
			Status:      models.SLOStatusMeeting,
			CreatedAt:   now.AddDate(0, -4, 0),
			UpdatedAt:   now.Add(-20 * time.Minute),
		},
		{
			ID:          "slo-005",
			ServiceID:   "user-service",
			Name:        "User Service Error Rate",
			Description: "Server-side error rate for user service must remain below threshold",
			Target:      99.5,
			Current:     98.8,
			Window:      "7d",
			SLIType:     models.SLITypeErrorRate,
			Status:      models.SLOStatusAtRisk,
			CreatedAt:   now.AddDate(0, -4, 0),
			UpdatedAt:   now.Add(-8 * time.Minute),
		},
		// --- payment-service (2 SLOs) ---
		{
			ID:          "slo-006",
			ServiceID:   "payment-service",
			Name:        "Payment API Availability",
			Description: "Payment processing endpoints must maintain high availability",
			Target:      99.95,
			Current:     99.62,
			Window:      "30d",
			SLIType:     models.SLITypeAvailability,
			Status:      models.SLOStatusBreaching,
			CreatedAt:   now.AddDate(0, -6, 0),
			UpdatedAt:   now.Add(-2 * time.Minute),
		},
		{
			ID:          "slo-007",
			ServiceID:   "payment-service",
			Name:        "Payment Latency P99",
			Description: "99th percentile latency for payment processing under 500ms",
			Target:      99.0,
			Current:     98.1,
			Window:      "30d",
			SLIType:     models.SLITypeLatency,
			Status:      models.SLOStatusBreaching,
			CreatedAt:   now.AddDate(0, -6, 0),
			UpdatedAt:   now.Add(-3 * time.Minute),
		},
		// --- notification-service (2 SLOs) ---
		{
			ID:          "slo-008",
			ServiceID:   "notification-service",
			Name:        "Notification Delivery Rate",
			Description: "Notifications must be delivered successfully within SLA window",
			Target:      99.5,
			Current:     99.68,
			Window:      "7d",
			SLIType:     models.SLITypeThroughput,
			Status:      models.SLOStatusMeeting,
			CreatedAt:   now.AddDate(0, -3, 0),
			UpdatedAt:   now.Add(-12 * time.Minute),
		},
		{
			ID:          "slo-009",
			ServiceID:   "notification-service",
			Name:        "Notification Error Rate",
			Description: "Error rate for notification dispatch must remain below threshold",
			Target:      99.0,
			Current:     99.34,
			Window:      "30d",
			SLIType:     models.SLITypeErrorRate,
			Status:      models.SLOStatusMeeting,
			CreatedAt:   now.AddDate(0, -3, 0),
			UpdatedAt:   now.Add(-18 * time.Minute),
		},
		// --- deployment-controller (1 SLO) ---
		{
			ID:          "slo-010",
			ServiceID:   "deployment-controller",
			Name:        "Deploy Success Rate",
			Description: "Deployments initiated through the controller must succeed",
			Target:      99.0,
			Current:     97.5,
			Window:      "90d",
			SLIType:     models.SLITypeAvailability,
			Status:      models.SLOStatusAtRisk,
			CreatedAt:   now.AddDate(0, -8, 0),
			UpdatedAt:   now.Add(-30 * time.Minute),
		},
	}

	// Compute error budget fields for each SLO.
	for i := range slos {
		computeErrorBudget(&slos[i])
	}

	return slos
}

// computeErrorBudget fills in the derived error budget fields on an SLO.
func computeErrorBudget(slo *models.SLO) {
	// Error budget total is (100 - target).  E.g. 99.95 target => 0.05 budget.
	slo.ErrorBudgetTotal = 100.0 - slo.Target

	// How much of the budget has been consumed = (target - current) / budget_total.
	// If current >= target, consumed is based on how close we are.
	consumed := (slo.Target - slo.Current) / slo.ErrorBudgetTotal
	if consumed < 0 {
		// Current exceeds target: some budget was consumed but not all.
		// Map to a positive consumed percentage based on how far above target.
		// E.g. if target=99.9, current=99.95, budget_total=0.1, consumed = -0.5 => 50% used (generous headroom)
		// We flip the sign and ensure it stays in [0, 1].
		consumed = 1.0 - math.Abs(consumed)
		if consumed < 0 {
			consumed = 0
		}
	}
	if consumed > 1 {
		consumed = 1
	}

	slo.ErrorBudgetConsumedPct = math.Round(consumed*10000) / 100 // percentage with 2 decimals
	slo.ErrorBudgetRemaining = math.Round((1-consumed)*10000) / 100

	// Burn rate: how fast budget is being consumed relative to the window.
	// >1 means consuming faster than the window allows.
	switch slo.Status {
	case models.SLOStatusBreaching:
		slo.BurnRate = 2.0 + rand.Float64()*3.0 // 2x-5x
	case models.SLOStatusAtRisk:
		slo.BurnRate = 1.0 + rand.Float64()*1.0 // 1x-2x
	default:
		slo.BurnRate = 0.2 + rand.Float64()*0.6 // 0.2x-0.8x
	}
	slo.BurnRate = math.Round(slo.BurnRate*100) / 100
}

// GenerateMockErrorBudget generates a realistic error budget time series for charting.
// It produces `days` data points (one per day), with patterns that match the SLO status.
func GenerateMockErrorBudget(sloID string, days int) []models.ErrorBudgetDataPoint {
	// Determine the final remaining budget based on the SLO ID so that the
	// time series endpoint is consistent with the SLO data.
	finalRemaining := 60.0 // default: healthy
	pattern := "steady"

	switch sloID {
	case "slo-001": // gateway availability, at_risk
		finalRemaining = 38.0
		pattern = "gradual_decline"
	case "slo-002": // gateway latency, meeting
		finalRemaining = 72.0
		pattern = "steady"
	case "slo-003": // auth availability, meeting
		finalRemaining = 82.0
		pattern = "steady"
	case "slo-004": // user availability, meeting
		finalRemaining = 75.0
		pattern = "steady"
	case "slo-005": // user error rate, at_risk
		finalRemaining = 42.0
		pattern = "incident_spike"
	case "slo-006": // payment availability, breaching
		finalRemaining = 12.0
		pattern = "heavy_burn"
	case "slo-007": // payment latency, breaching
		finalRemaining = 18.0
		pattern = "heavy_burn"
	case "slo-008": // notification throughput, meeting
		finalRemaining = 68.0
		pattern = "steady"
	case "slo-009": // notification error rate, meeting
		finalRemaining = 65.0
		pattern = "steady"
	case "slo-010": // deploy success rate, at_risk
		finalRemaining = 35.0
		pattern = "incident_spike"
	}

	points := make([]models.ErrorBudgetDataPoint, days)
	now := time.Now().UTC().Truncate(24 * time.Hour)

	for i := 0; i < days; i++ {
		dayIndex := i
		t := now.AddDate(0, 0, -(days - 1 - i)) // oldest first

		var remaining float64
		var burnRate float64

		progress := float64(dayIndex) / float64(days-1)

		switch pattern {
		case "steady":
			// Budget stays relatively flat with minor noise.
			start := 95.0
			end := finalRemaining
			remaining = start - (start-end)*progress + (rand.Float64()-0.5)*2
			burnRate = 0.3 + rand.Float64()*0.4

		case "gradual_decline":
			// Slow steady decline.
			start := 85.0
			remaining = start - (start-finalRemaining)*progress + (rand.Float64()-0.5)*1.5
			burnRate = 0.8 + rand.Float64()*0.8

		case "incident_spike":
			// Mostly steady, then a sudden drop around day 20 (simulating an incident).
			start := 88.0
			if progress < 0.65 {
				remaining = start - (start-55)*progress + (rand.Float64()-0.5)*2
				burnRate = 0.5 + rand.Float64()*0.5
			} else if progress < 0.75 {
				// Incident: sharp drop.
				incidentProgress := (progress - 0.65) / 0.10
				remaining = 55 - (55-finalRemaining)*0.7*incidentProgress + (rand.Float64()-0.5)*1
				burnRate = 3.0 + rand.Float64()*2.0
			} else {
				// Post-incident: slow continued burn.
				postProgress := (progress - 0.75) / 0.25
				remaining = finalRemaining + 8*(1-postProgress) + (rand.Float64()-0.5)*1
				burnRate = 1.0 + rand.Float64()*0.5
			}

		case "heavy_burn":
			// Aggressive burn from the start, accelerating.
			start := 90.0
			// Use an exponential-like curve.
			remaining = start - (start-finalRemaining)*math.Pow(progress, 0.6) + (rand.Float64()-0.5)*2
			if progress < 0.3 {
				burnRate = 1.5 + rand.Float64()*1.0
			} else if progress < 0.7 {
				burnRate = 2.5 + rand.Float64()*1.5
			} else {
				burnRate = 3.5 + rand.Float64()*2.0
			}
		}

		// Clamp values.
		if remaining < 0 {
			remaining = 0
		}
		if remaining > 100 {
			remaining = 100
		}
		remaining = math.Round(remaining*100) / 100
		burnRate = math.Round(burnRate*100) / 100

		points[i] = models.ErrorBudgetDataPoint{
			Timestamp: t,
			Remaining: remaining,
			BurnRate:  burnRate,
		}
	}

	return points
}

// GenerateMockServices returns 6 services with realistic metadata.
func GenerateMockServices() []models.Service {
	now := time.Now().UTC()

	return []models.Service{
		{
			ID:           "api-gateway",
			Name:         "API Gateway",
			Description:  "Edge proxy handling routing, rate limiting, and TLS termination for all inbound traffic",
			Team:         "platform",
			Repository:   "github.com/aegis/api-gateway",
			Language:     "Go",
			Framework:    "Fiber v2",
			SLOTarget:    99.99,
			Status:       models.ServiceStatusHealthy,
			Dependencies: []string{"auth-service", "user-service", "payment-service", "notification-service"},
			Tier:         "tier-0",
			OnCallTeam:   "platform-sre",
			DeployFreq:   "2x/week",
			LastDeploy:   now.Add(-18 * time.Hour),
			CreatedAt:    now.AddDate(-1, 0, 0),
			UpdatedAt:    now.Add(-18 * time.Hour),
		},
		{
			ID:           "auth-service",
			Name:         "Auth Service",
			Description:  "Handles authentication, authorization, OAuth2/OIDC, and session management",
			Team:         "identity",
			Repository:   "github.com/aegis/auth-service",
			Language:     "Java",
			Framework:    "Spring Boot 3",
			SLOTarget:    99.95,
			Status:       models.ServiceStatusHealthy,
			Dependencies: []string{"user-service"},
			Tier:         "tier-0",
			OnCallTeam:   "identity-sre",
			DeployFreq:   "1x/week",
			LastDeploy:   now.Add(-72 * time.Hour),
			CreatedAt:    now.AddDate(-1, -2, 0),
			UpdatedAt:    now.Add(-72 * time.Hour),
		},
		{
			ID:           "user-service",
			Name:         "User Service",
			Description:  "User profiles, preferences, and account management with PostgreSQL backend",
			Team:         "identity",
			Repository:   "github.com/aegis/user-service",
			Language:     "Java",
			Framework:    "Spring Boot 3",
			SLOTarget:    99.9,
			Status:       models.ServiceStatusDegraded,
			Dependencies: []string{},
			Tier:         "tier-1",
			OnCallTeam:   "identity-sre",
			DeployFreq:   "3x/week",
			LastDeploy:   now.Add(-6 * time.Hour),
			CreatedAt:    now.AddDate(-1, -2, 0),
			UpdatedAt:    now.Add(-6 * time.Hour),
		},
		{
			ID:           "payment-service",
			Name:         "Payment Service",
			Description:  "Payment processing, billing, subscriptions, and Stripe integration",
			Team:         "payments",
			Repository:   "github.com/aegis/payment-service",
			Language:     "Java",
			Framework:    "Spring Boot 3",
			SLOTarget:    99.95,
			Status:       models.ServiceStatusDegraded,
			Dependencies: []string{"auth-service", "notification-service"},
			Tier:         "tier-0",
			OnCallTeam:   "payments-sre",
			DeployFreq:   "1x/week",
			LastDeploy:   now.Add(-48 * time.Hour),
			CreatedAt:    now.AddDate(0, -10, 0),
			UpdatedAt:    now.Add(-2 * time.Hour),
		},
		{
			ID:           "notification-service",
			Name:         "Notification Service",
			Description:  "Multi-channel notification dispatch: email, SMS, push, and in-app",
			Team:         "messaging",
			Repository:   "github.com/aegis/notification-service",
			Language:     "Go",
			Framework:    "Fiber v2",
			SLOTarget:    99.5,
			Status:       models.ServiceStatusHealthy,
			Dependencies: []string{},
			Tier:         "tier-1",
			OnCallTeam:   "messaging-sre",
			DeployFreq:   "2x/week",
			LastDeploy:   now.Add(-24 * time.Hour),
			CreatedAt:    now.AddDate(0, -8, 0),
			UpdatedAt:    now.Add(-24 * time.Hour),
		},
		{
			ID:           "deployment-controller",
			Name:         "Deployment Controller",
			Description:  "Kubernetes deployment orchestration, rollouts, rollbacks, and scaling",
			Team:         "platform",
			Repository:   "github.com/aegis/deployment-controller",
			Language:     "Go",
			Framework:    "client-go",
			SLOTarget:    99.0,
			Status:       models.ServiceStatusHealthy,
			Dependencies: []string{},
			Tier:         "tier-1",
			OnCallTeam:   "platform-sre",
			DeployFreq:   "1x/2weeks",
			LastDeploy:   now.Add(-168 * time.Hour),
			CreatedAt:    now.AddDate(-1, -6, 0),
			UpdatedAt:    now.Add(-168 * time.Hour),
		},
	}
}
