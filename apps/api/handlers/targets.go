package handlers

import (
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"

	"github.com/junegu/aegis/api/middleware"
)

// TeamTargets represents SLO, MTTR, SLA, Error Budget, and Cost Budget targets
// for a specific cloud account or team.
type TeamTargets struct {
	AccountID   string  `json:"account_id"`
	SLOTarget   float64 `json:"slo_target"`    // percentage, e.g. 99.9
	MTTRTarget  float64 `json:"mttr_target"`   // minutes
	SLATarget   float64 `json:"sla_target"`    // percentage, e.g. 99.95
	ErrorBudget float64 `json:"error_budget"`  // minutes per month
	CostBudget  float64 `json:"cost_budget"`   // dollars per month
	UpdatedAt   string  `json:"updated_at"`
	UpdatedBy   string  `json:"updated_by"`
}

// UpdateTargetsRequest represents the payload for setting/updating targets.
type UpdateTargetsRequest struct {
	SLOTarget   *float64 `json:"slo_target,omitempty"`
	MTTRTarget  *float64 `json:"mttr_target,omitempty"`
	SLATarget   *float64 `json:"sla_target,omitempty"`
	ErrorBudget *float64 `json:"error_budget,omitempty"`
	CostBudget  *float64 `json:"cost_budget,omitempty"`
}

// targetStore provides thread-safe in-memory storage for team targets.
var targetStore = struct {
	sync.RWMutex
	data map[string]*TeamTargets
}{
	data: map[string]*TeamTargets{
		"all": {
			AccountID:   "all",
			SLOTarget:   99.9,
			MTTRTarget:  60,
			SLATarget:   99.95,
			ErrorBudget: 43.2,
			CostBudget:  50000,
			UpdatedAt:   "2026-04-01T00:00:00Z",
			UpdatedBy:   "system",
		},
		"acc-hub-001": {
			AccountID:   "acc-hub-001",
			SLOTarget:   99.95,
			MTTRTarget:  30,
			SLATarget:   99.99,
			ErrorBudget: 21.6,
			CostBudget:  25000,
			UpdatedAt:   "2026-04-05T10:30:00Z",
			UpdatedBy:   "june.gu@aegis.dev",
		},
		"acc-spoke-prod": {
			AccountID:   "acc-spoke-prod",
			SLOTarget:   99.9,
			MTTRTarget:  45,
			SLATarget:   99.95,
			ErrorBudget: 43.2,
			CostBudget:  15000,
			UpdatedAt:   "2026-04-05T10:30:00Z",
			UpdatedBy:   "june.gu@aegis.dev",
		},
		"acc-spoke-staging": {
			AccountID:   "acc-spoke-staging",
			SLOTarget:   99.5,
			MTTRTarget:  120,
			SLATarget:   99.0,
			ErrorBudget: 216.0,
			CostBudget:  5000,
			UpdatedAt:   "2026-04-03T14:00:00Z",
			UpdatedBy:   "system",
		},
	},
}

// ListTargets returns all team targets, optionally filtered by account_id.
//
//	GET /api/v1/targets?account_id=...
func ListTargets(c *fiber.Ctx) error {
	accountFilter := c.Query("account_id")

	targetStore.RLock()
	defer targetStore.RUnlock()

	var result []*TeamTargets
	for _, t := range targetStore.data {
		if accountFilter != "" && t.AccountID != accountFilter {
			continue
		}
		result = append(result, t)
	}

	if result == nil {
		result = []*TeamTargets{}
	}

	return c.JSON(fiber.Map{
		"data":  result,
		"total": len(result),
	})
}

// GetTargets returns the targets for a specific account.
//
//	GET /api/v1/targets/:account_id
func GetTargets(c *fiber.Ctx) error {
	accountID := c.Params("account_id")

	targetStore.RLock()
	defer targetStore.RUnlock()

	targets, exists := targetStore.data[accountID]
	if !exists {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "No targets found for account: " + accountID,
		})
	}

	return c.JSON(targets)
}

// UpdateTargets sets or updates the targets for a specific account.
//
//	PUT /api/v1/targets/:account_id
func UpdateTargets(c *fiber.Ctx) error {
	accountID := c.Params("account_id")

	var req UpdateTargetsRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	// Get user info from auth middleware.
	updatedBy := "api"
	if user, ok := c.Locals("user").(middleware.MockUser); ok {
		updatedBy = user.Email
	}

	now := time.Now().UTC().Format(time.RFC3339)

	targetStore.Lock()
	defer targetStore.Unlock()

	targets, exists := targetStore.data[accountID]
	if !exists {
		// Create new targets with defaults.
		targets = &TeamTargets{
			AccountID:   accountID,
			SLOTarget:   99.9,
			MTTRTarget:  60,
			SLATarget:   99.95,
			ErrorBudget: 43.2,
			CostBudget:  10000,
			UpdatedAt:   now,
			UpdatedBy:   updatedBy,
		}
		targetStore.data[accountID] = targets
	}

	// Apply partial updates.
	if req.SLOTarget != nil {
		if *req.SLOTarget < 0 || *req.SLOTarget > 100 {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   "validation_error",
				"message": "SLO target must be between 0 and 100",
			})
		}
		targets.SLOTarget = *req.SLOTarget
	}
	if req.MTTRTarget != nil {
		if *req.MTTRTarget < 0 {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   "validation_error",
				"message": "MTTR target must be positive",
			})
		}
		targets.MTTRTarget = *req.MTTRTarget
	}
	if req.SLATarget != nil {
		if *req.SLATarget < 0 || *req.SLATarget > 100 {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   "validation_error",
				"message": "SLA target must be between 0 and 100",
			})
		}
		targets.SLATarget = *req.SLATarget
	}
	if req.ErrorBudget != nil {
		if *req.ErrorBudget < 0 {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   "validation_error",
				"message": "Error budget must be positive",
			})
		}
		targets.ErrorBudget = *req.ErrorBudget
	}
	if req.CostBudget != nil {
		if *req.CostBudget < 0 {
			return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
				"error":   "validation_error",
				"message": "Cost budget must be positive",
			})
		}
		targets.CostBudget = *req.CostBudget
	}

	targets.UpdatedAt = now
	targets.UpdatedBy = updatedBy

	return c.JSON(targets)
}
