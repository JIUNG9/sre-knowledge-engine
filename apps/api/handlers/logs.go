package handlers

import (
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/junegu/aegis/api/mock"
	"github.com/junegu/aegis/api/models"
	"github.com/junegu/aegis/api/store"
)

// LogHandlers holds dependencies for log query handlers.
type LogHandlers struct {
	Store        store.Store
	Logger       *zap.Logger
	savedQueries []models.SavedQuery
}

// NewLogHandlers creates a new LogHandlers instance.
// If the store is nil (e.g., no ClickHouse), handlers fall back to mock data.
func NewLogHandlers(s store.Store, logger *zap.Logger) *LogHandlers {
	return &LogHandlers{
		Store:  s,
		Logger: logger,
		savedQueries: []models.SavedQuery{
			{
				ID:   "sq-001",
				Name: "Production Errors",
				Query: "level:error",
				Filters: models.LogQuery{
					Levels: []string{"error", "fatal"},
				},
				CreatedAt: time.Date(2026, 4, 1, 10, 0, 0, 0, time.UTC),
			},
			{
				ID:   "sq-002",
				Name: "Payment Failures",
				Query: "payment failed",
				Filters: models.LogQuery{
					Services: []string{"payment-service"},
					Levels:   []string{"error"},
				},
				CreatedAt: time.Date(2026, 4, 3, 14, 30, 0, 0, time.UTC),
			},
			{
				ID:   "sq-003",
				Name: "Security Events",
				Query: "login attempt OR permission denied OR unusual",
				Filters: models.LogQuery{
					Levels: []string{"warn", "error"},
				},
				CreatedAt: time.Date(2026, 4, 5, 9, 15, 0, 0, time.UTC),
			},
			{
				ID:   "sq-004",
				Name: "Slow Queries",
				Query: "slow query",
				Filters: models.LogQuery{
					Services: []string{"user-service", "payment-service"},
					Levels:   []string{"warn"},
				},
				CreatedAt: time.Date(2026, 4, 7, 16, 0, 0, 0, time.UTC),
			},
		},
	}
}

// useClickHouse returns true if a ClickHouse connection is configured and available.
func (h *LogHandlers) useClickHouse() bool {
	return h.Store != nil && os.Getenv("CLICKHOUSE_URL") != ""
}

// QueryLogs returns log entries matching the query parameters.
// GET /api/v1/logs?q=&start=&end=&levels=&services=&limit=&offset=
func (h *LogHandlers) QueryLogs(c *fiber.Ctx) error {
	query := models.LogQuery{
		Query: c.Query("q"),
	}

	// Parse time range.
	if startStr := c.Query("start"); startStr != "" {
		if t, err := time.Parse(time.RFC3339, startStr); err == nil {
			query.StartTime = t
		}
	}
	if endStr := c.Query("end"); endStr != "" {
		if t, err := time.Parse(time.RFC3339, endStr); err == nil {
			query.EndTime = t
		}
	}

	// Parse levels (comma-separated).
	if levelsStr := c.Query("levels"); levelsStr != "" {
		for _, l := range strings.Split(levelsStr, ",") {
			l = strings.TrimSpace(l)
			if l != "" {
				query.Levels = append(query.Levels, l)
			}
		}
	}

	// Parse services (comma-separated).
	if servicesStr := c.Query("services"); servicesStr != "" {
		for _, s := range strings.Split(servicesStr, ",") {
			s = strings.TrimSpace(s)
			if s != "" {
				query.Services = append(query.Services, s)
			}
		}
	}

	// Parse pagination.
	if limitStr := c.Query("limit"); limitStr != "" {
		if l, err := strconv.Atoi(limitStr); err == nil && l > 0 {
			query.Limit = l
		}
	}
	if query.Limit <= 0 {
		query.Limit = 100
	}
	if query.Limit > 1000 {
		query.Limit = 1000
	}

	if offsetStr := c.Query("offset"); offsetStr != "" {
		if o, err := strconv.Atoi(offsetStr); err == nil && o >= 0 {
			query.Offset = o
		}
	}

	// If ClickHouse is connected, query real data.
	if h.useClickHouse() {
		entries, total, err := h.Store.QueryLogs(c.Context(), query)
		if err != nil {
			h.Logger.Error("Failed to query logs from ClickHouse", zap.Error(err))
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   "query_failed",
				"message": "Failed to query logs",
			})
		}
		return c.JSON(fiber.Map{
			"data":   entries,
			"total":  total,
			"limit":  query.Limit,
			"offset": query.Offset,
		})
	}

	// Fall back to mock data.
	mockEntries := mock.GenerateMockLogs(200)

	// Apply filters on mock data.
	filtered := make([]models.LogEntry, 0)
	for _, entry := range mockEntries {
		if query.Query != "" && !strings.Contains(strings.ToLower(entry.Message), strings.ToLower(query.Query)) {
			continue
		}
		if len(query.Levels) > 0 && !containsStr(query.Levels, entry.Level) {
			continue
		}
		if len(query.Services) > 0 && !containsStr(query.Services, entry.Service) {
			continue
		}
		if !query.StartTime.IsZero() && entry.Timestamp.Before(query.StartTime) {
			continue
		}
		if !query.EndTime.IsZero() && entry.Timestamp.After(query.EndTime) {
			continue
		}
		filtered = append(filtered, entry)
	}

	// Apply pagination.
	total := len(filtered)
	start := query.Offset
	if start > total {
		start = total
	}
	end := start + query.Limit
	if end > total {
		end = total
	}
	page := filtered[start:end]

	return c.JSON(fiber.Map{
		"data":   page,
		"total":  total,
		"limit":  query.Limit,
		"offset": query.Offset,
	})
}

// GetLogStats returns aggregate log statistics.
// GET /api/v1/logs/stats?range=24h
func (h *LogHandlers) GetLogStats(c *fiber.Ctx) error {
	timeRange := c.Query("range", "24h")

	if h.useClickHouse() {
		stats, err := h.Store.GetLogStats(c.Context(), timeRange)
		if err != nil {
			h.Logger.Error("Failed to get log stats from ClickHouse", zap.Error(err))
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   "stats_failed",
				"message": "Failed to get log statistics",
			})
		}
		return c.JSON(stats)
	}

	// Return mock stats.
	return c.JSON(models.LogStats{
		Total:     148293,
		Errors:    1247,
		Warnings:  5832,
		Rate:      1.72,
		TimeRange: timeRange,
	})
}

// GetServices returns a list of distinct service names.
// GET /api/v1/logs/services
func (h *LogHandlers) GetServices(c *fiber.Ctx) error {
	if h.useClickHouse() {
		services, err := h.Store.GetServices(c.Context())
		if err != nil {
			h.Logger.Error("Failed to get services from ClickHouse", zap.Error(err))
			return c.Status(fiber.StatusInternalServerError).JSON(fiber.Map{
				"error":   "services_failed",
				"message": "Failed to get services list",
			})
		}
		return c.JSON(fiber.Map{
			"services": services,
		})
	}

	// Return mock services.
	return c.JSON(fiber.Map{
		"services": mock.Services,
	})
}

// ListSavedQueries returns the list of saved log queries.
// GET /api/v1/logs/saved-queries
func (h *LogHandlers) ListSavedQueries(c *fiber.Ctx) error {
	return c.JSON(fiber.Map{
		"data":  h.savedQueries,
		"total": len(h.savedQueries),
	})
}

// CreateSavedQuery saves a new log query.
// POST /api/v1/logs/saved-queries
func (h *LogHandlers) CreateSavedQuery(c *fiber.Ctx) error {
	var req models.SavedQueryRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_payload",
			"message": "Failed to parse request body: " + err.Error(),
		})
	}

	if req.Name == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "missing_name",
			"message": "Saved query name is required",
		})
	}

	saved := models.SavedQuery{
		ID:        "sq-" + uuid.New().String()[:8],
		Name:      req.Name,
		Query:     req.Query,
		Filters:   req.Filters,
		CreatedAt: time.Now(),
	}

	h.savedQueries = append(h.savedQueries, saved)

	h.Logger.Info("Saved query created",
		zap.String("id", saved.ID),
		zap.String("name", saved.Name),
	)

	return c.Status(fiber.StatusCreated).JSON(saved)
}

// containsStr checks if a string slice contains a given string.
func containsStr(slice []string, s string) bool {
	for _, v := range slice {
		if v == s {
			return true
		}
	}
	return false
}
