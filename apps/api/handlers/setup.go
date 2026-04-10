package handlers

import (
	"math/rand"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"

	"github.com/junegu/aegis/api/models"
)

// setupStore provides thread-safe in-memory storage for setup configuration.
var setupStore = struct {
	sync.RWMutex
	configs   []models.AegisConfig
	completed bool
}{
	configs:   []models.AegisConfig{},
	completed: false,
}

// defaultSteps returns the initial setup wizard steps.
func defaultSteps() []models.SetupStep {
	return []models.SetupStep{
		{Number: 1, Name: "AI Engine", Status: "pending"},
		{Number: 2, Name: "Cloud Accounts", Status: "pending"},
		{Number: 3, Name: "Integrations", Status: "pending"},
		{Number: 4, Name: "Team", Status: "pending"},
		{Number: 5, Name: "Review", Status: "pending"},
		{Number: 6, Name: "Complete", Status: "pending"},
	}
}

// computeCurrentStep determines which step the user is on based on saved configs.
func computeCurrentStep() int {
	setupStore.RLock()
	defer setupStore.RUnlock()

	sections := map[string]bool{}
	for _, cfg := range setupStore.configs {
		sections[cfg.Section] = true
	}

	if !sections["ai"] {
		return 1
	}
	if !sections["cloud"] {
		return 2
	}
	if !sections["integrations"] {
		return 3
	}
	if !sections["team"] {
		return 4
	}
	return 5
}

// GetSetupStatus returns the current setup wizard status.
func GetSetupStatus(c *fiber.Ctx) error {
	setupStore.RLock()
	completed := setupStore.completed
	setupStore.RUnlock()

	currentStep := computeCurrentStep()
	steps := defaultSteps()

	for i := range steps {
		if steps[i].Number < currentStep {
			steps[i].Status = "complete"
		} else if steps[i].Number == currentStep {
			steps[i].Status = "current"
		}
	}

	if completed {
		for i := range steps {
			steps[i].Status = "complete"
		}
	}

	return c.JSON(models.SetupStatus{
		Completed:   completed,
		CurrentStep: currentStep,
		Steps:       steps,
	})
}

// SaveConfig saves a configuration entry for a given section.
func SaveConfig(c *fiber.Ctx) error {
	var req models.SaveConfigRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	if req.Section == "" || req.Key == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "validation_error",
			"message": "Section and key are required",
		})
	}

	validSections := map[string]bool{
		"ai": true, "cloud": true, "integrations": true, "team": true, "general": true,
	}
	if !validSections[req.Section] {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "validation_error",
			"message": "Invalid section. Must be one of: ai, cloud, integrations, team, general",
		})
	}

	now := time.Now().UTC()

	setupStore.Lock()
	defer setupStore.Unlock()

	// Check if this config already exists (upsert).
	for i := range setupStore.configs {
		if setupStore.configs[i].Section == req.Section && setupStore.configs[i].Key == req.Key {
			setupStore.configs[i].Value = req.Value
			setupStore.configs[i].UpdatedAt = now
			return c.JSON(setupStore.configs[i])
		}
	}

	// Create new config entry.
	cfg := models.AegisConfig{
		ID:        uuid.New().String(),
		Section:   req.Section,
		Key:       req.Key,
		Value:     req.Value,
		CreatedAt: now,
		UpdatedAt: now,
	}
	setupStore.configs = append(setupStore.configs, cfg)

	return c.Status(fiber.StatusCreated).JSON(cfg)
}

// CompleteSetup marks the setup wizard as complete.
func CompleteSetup(c *fiber.Ctx) error {
	setupStore.Lock()
	setupStore.completed = true
	setupStore.Unlock()

	return c.JSON(fiber.Map{
		"message":   "Setup completed successfully",
		"completed": true,
	})
}

// TestConnection simulates testing a connection to an external service.
func TestConnection(c *fiber.Ctx) error {
	var req models.TestConnectionRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	if req.Type == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "validation_error",
			"message": "Connection type is required",
		})
	}

	// Simulate a 1-2 second connection test delay.
	delay := time.Duration(1000+rand.Intn(1000)) * time.Millisecond
	time.Sleep(delay)

	return c.JSON(models.ConnectionTestResult{
		Success: true,
		Message: "Connection to " + req.Type + " established successfully",
		Latency: int(delay.Milliseconds()),
	})
}
