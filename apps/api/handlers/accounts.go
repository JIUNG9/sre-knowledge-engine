package handlers

import (
	"math/rand"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"

	"github.com/junegu/aegis/api/models"
)

// accountStore provides thread-safe in-memory storage for cloud accounts.
var accountStore = struct {
	sync.RWMutex
	data []models.CloudAccount
}{
	data: []models.CloudAccount{},
}

// ListAccounts returns all registered cloud accounts.
func ListAccounts(c *fiber.Ctx) error {
	accountStore.RLock()
	defer accountStore.RUnlock()

	data := accountStore.data
	if data == nil {
		data = []models.CloudAccount{}
	}

	return c.JSON(fiber.Map{
		"data":  data,
		"total": len(data),
	})
}

// CreateAccount adds a new cloud account.
func CreateAccount(c *fiber.Ctx) error {
	var req models.CreateAccountRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	if req.Name == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "validation_error",
			"message": "Account name is required",
		})
	}

	if req.Provider == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "validation_error",
			"message": "Provider is required",
		})
	}

	validProviders := map[string]bool{
		"aws": true, "gcp": true, "azure": true, "ncloud": true, "custom": true,
	}
	if !validProviders[req.Provider] {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "validation_error",
			"message": "Invalid provider. Must be one of: aws, gcp, azure, ncloud, custom",
		})
	}

	now := time.Now().UTC()
	account := models.CloudAccount{
		ID:             uuid.New().String(),
		Name:           req.Name,
		Alias:          req.Alias,
		Provider:       req.Provider,
		AccountID:      req.AccountID,
		Region:         req.Region,
		Role:           req.Role,
		Status:         "disconnected",
		ConnectionType: req.ConnectionType,
		CreatedAt:      now,
	}

	// Default role and connection type.
	if account.Role == "" {
		account.Role = "standalone"
	}
	if account.ConnectionType == "" {
		account.ConnectionType = "access_key"
	}

	accountStore.Lock()
	accountStore.data = append(accountStore.data, account)
	accountStore.Unlock()

	return c.Status(fiber.StatusCreated).JSON(account)
}

// UpdateAccount updates an existing cloud account.
func UpdateAccount(c *fiber.Ctx) error {
	id := c.Params("id")

	var req models.UpdateAccountRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	accountStore.Lock()
	defer accountStore.Unlock()

	var found *models.CloudAccount
	for i := range accountStore.data {
		if accountStore.data[i].ID == id {
			found = &accountStore.data[i]
			break
		}
	}

	if found == nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Account not found",
		})
	}

	if req.Name != nil {
		found.Name = *req.Name
	}
	if req.Alias != nil {
		found.Alias = *req.Alias
	}
	if req.Provider != nil {
		found.Provider = *req.Provider
	}
	if req.AccountID != nil {
		found.AccountID = *req.AccountID
	}
	if req.Region != nil {
		found.Region = *req.Region
	}
	if req.Role != nil {
		found.Role = *req.Role
	}
	if req.ConnectionType != nil {
		found.ConnectionType = *req.ConnectionType
	}

	return c.JSON(found)
}

// DeleteAccount removes a cloud account by ID.
func DeleteAccount(c *fiber.Ctx) error {
	id := c.Params("id")

	accountStore.Lock()
	defer accountStore.Unlock()

	idx := -1
	for i := range accountStore.data {
		if accountStore.data[i].ID == id {
			idx = i
			break
		}
	}

	if idx == -1 {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Account not found",
		})
	}

	accountStore.data = append(accountStore.data[:idx], accountStore.data[idx+1:]...)

	return c.JSON(fiber.Map{
		"message": "Account deleted successfully",
	})
}

// TestAccountConnection simulates testing connectivity to a cloud account.
func TestAccountConnection(c *fiber.Ctx) error {
	id := c.Params("id")

	accountStore.RLock()
	var found *models.CloudAccount
	for i := range accountStore.data {
		if accountStore.data[i].ID == id {
			found = &accountStore.data[i]
			break
		}
	}
	accountStore.RUnlock()

	if found == nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Account not found",
		})
	}

	// Simulate a 1-2 second connection test delay.
	delay := time.Duration(1000+rand.Intn(1000)) * time.Millisecond
	time.Sleep(delay)

	// Update account status to connected.
	accountStore.Lock()
	for i := range accountStore.data {
		if accountStore.data[i].ID == id {
			accountStore.data[i].Status = "connected"
			break
		}
	}
	accountStore.Unlock()

	return c.JSON(models.ConnectionTestResult{
		Success: true,
		Message: "Successfully connected to " + found.Provider + " account " + found.Name,
		Latency: int(delay.Milliseconds()),
	})
}
