package handlers

import (
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"

	"github.com/junegu/aegis/api/mock"
	"github.com/junegu/aegis/api/models"
)

// incidentStore provides thread-safe in-memory storage for incidents.
var incidentStore = struct {
	sync.RWMutex
	data    []models.Incident
	counter int
}{
	data:    mock.Incidents(),
	counter: 10, // start after mock INC-010
}

// nextIncidentID generates the next sequential incident ID.
func nextIncidentID() string {
	incidentStore.counter++
	return fmt.Sprintf("INC-%03d", incidentStore.counter)
}

// ListIncidents returns incidents with optional filters for status, severity, service, and assignee.
func ListIncidents(c *fiber.Ctx) error {
	statusFilter := c.Query("status")
	severityFilter := c.Query("severity")
	serviceFilter := c.Query("service")
	assigneeFilter := c.Query("assignee")

	incidentStore.RLock()
	defer incidentStore.RUnlock()

	var filtered []models.Incident
	for _, inc := range incidentStore.data {
		if statusFilter != "" && string(inc.Status) != statusFilter {
			continue
		}
		if severityFilter != "" && string(inc.Severity) != severityFilter {
			continue
		}
		if serviceFilter != "" && inc.Service != serviceFilter {
			continue
		}
		if assigneeFilter != "" && !strings.EqualFold(inc.Assignee, assigneeFilter) {
			continue
		}
		filtered = append(filtered, inc)
	}

	if filtered == nil {
		filtered = []models.Incident{}
	}

	return c.JSON(fiber.Map{
		"data":  filtered,
		"total": len(filtered),
	})
}

// GetIncident returns a single incident by ID with the full timeline.
func GetIncident(c *fiber.Ctx) error {
	id := c.Params("id")

	incidentStore.RLock()
	defer incidentStore.RUnlock()

	for _, inc := range incidentStore.data {
		if inc.ID == id {
			return c.JSON(inc)
		}
	}
	return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
		"error":   "not_found",
		"message": "Incident not found",
	})
}

// CreateIncident creates a new incident and initializes its timeline.
func CreateIncident(c *fiber.Ctx) error {
	var req models.CreateIncidentRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	if req.Title == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "validation_error",
			"message": "Title is required",
		})
	}
	if req.Severity == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "validation_error",
			"message": "Severity is required",
		})
	}

	now := time.Now().UTC()

	incidentStore.Lock()
	defer incidentStore.Unlock()

	incID := nextIncidentID()
	incident := models.Incident{
		ID:            incID,
		Title:         req.Title,
		Description:   req.Description,
		Severity:      req.Severity,
		Status:        models.IncidentStatusOpen,
		Service:       req.Service,
		Assignee:      req.Assignee,
		RelatedAlerts: []string{},
		Timeline: []models.TimelineEvent{
			{
				ID:         uuid.New().String(),
				IncidentID: incID,
				Type:       models.TimelineEventAlertFired,
				Actor:      "system",
				Message:    "Incident created",
				Timestamp:  now,
			},
		},
		CreatedAt: now,
		UpdatedAt: now,
		Duration:  0,
	}

	incidentStore.data = append(incidentStore.data, incident)

	return c.Status(fiber.StatusCreated).JSON(incident)
}

// UpdateIncident applies a partial update to an existing incident.
func UpdateIncident(c *fiber.Ctx) error {
	id := c.Params("id")

	var req models.UpdateIncidentRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	incidentStore.Lock()
	defer incidentStore.Unlock()

	var found *models.Incident
	for i := range incidentStore.data {
		if incidentStore.data[i].ID == id {
			found = &incidentStore.data[i]
			break
		}
	}

	if found == nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Incident not found",
		})
	}

	now := time.Now().UTC()

	if req.Title != nil {
		found.Title = *req.Title
	}
	if req.Description != nil {
		found.Description = *req.Description
	}
	if req.Severity != nil {
		found.Severity = *req.Severity
	}
	if req.Status != nil {
		oldStatus := found.Status
		found.Status = *req.Status
		found.Timeline = append(found.Timeline, models.TimelineEvent{
			ID:         uuid.New().String(),
			IncidentID: found.ID,
			Type:       models.TimelineEventStatusChange,
			Actor:      "api",
			Message:    fmt.Sprintf("Status changed from %s to %s", oldStatus, *req.Status),
			Metadata:   map[string]string{"from": string(oldStatus), "to": string(*req.Status)},
			Timestamp:  now,
		})
		if *req.Status == models.IncidentStatusResolved {
			found.ResolvedAt = &now
			found.Duration = now.Sub(found.CreatedAt).Seconds()
		}
	}
	if req.Service != nil {
		found.Service = *req.Service
	}
	if req.Assignee != nil {
		found.Assignee = *req.Assignee
	}
	if req.RootCause != nil {
		found.RootCause = *req.RootCause
	}
	if req.Remediation != nil {
		found.Remediation = *req.Remediation
	}
	found.UpdatedAt = now

	return c.JSON(found)
}

// AddTimelineEvent adds a new event (note, status change, etc.) to an incident's timeline.
func AddTimelineEvent(c *fiber.Ctx) error {
	id := c.Params("id")

	var req models.TimelineAddRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "invalid_request",
			"message": "Failed to parse request body",
		})
	}

	if req.Message == "" {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error":   "validation_error",
			"message": "Message is required",
		})
	}

	incidentStore.Lock()
	defer incidentStore.Unlock()

	var found *models.Incident
	for i := range incidentStore.data {
		if incidentStore.data[i].ID == id {
			found = &incidentStore.data[i]
			break
		}
	}

	if found == nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Incident not found",
		})
	}

	now := time.Now().UTC()
	event := models.TimelineEvent{
		ID:         uuid.New().String(),
		IncidentID: found.ID,
		Type:       req.Type,
		Actor:      req.Actor,
		Message:    req.Message,
		Metadata:   req.Metadata,
		Timestamp:  now,
	}

	found.Timeline = append(found.Timeline, event)
	found.UpdatedAt = now

	return c.Status(fiber.StatusCreated).JSON(event)
}

// AcknowledgeIncident marks an incident as acknowledged and moves it to investigating.
func AcknowledgeIncident(c *fiber.Ctx) error {
	id := c.Params("id")

	type ackRequest struct {
		Actor string `json:"actor"`
	}
	var req ackRequest
	// actor is optional — default to "api"
	_ = c.BodyParser(&req)
	actor := req.Actor
	if actor == "" {
		actor = "api"
	}

	incidentStore.Lock()
	defer incidentStore.Unlock()

	var found *models.Incident
	for i := range incidentStore.data {
		if incidentStore.data[i].ID == id {
			found = &incidentStore.data[i]
			break
		}
	}

	if found == nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Incident not found",
		})
	}

	if found.Status == models.IncidentStatusResolved {
		return c.Status(fiber.StatusConflict).JSON(fiber.Map{
			"error":   "conflict",
			"message": "Cannot acknowledge a resolved incident",
		})
	}

	now := time.Now().UTC()
	oldStatus := found.Status
	found.Status = models.IncidentStatusInvestigating
	found.UpdatedAt = now

	found.Timeline = append(found.Timeline, models.TimelineEvent{
		ID:         uuid.New().String(),
		IncidentID: found.ID,
		Type:       models.TimelineEventAcknowledged,
		Actor:      actor,
		Message:    fmt.Sprintf("Incident acknowledged by %s", actor),
		Metadata:   map[string]string{"from": string(oldStatus), "to": string(models.IncidentStatusInvestigating)},
		Timestamp:  now,
	})

	return c.JSON(found)
}

// ResolveIncident marks an incident as resolved and records resolution details.
func ResolveIncident(c *fiber.Ctx) error {
	id := c.Params("id")

	type resolveRequest struct {
		Actor       string `json:"actor"`
		RootCause   string `json:"root_cause,omitempty"`
		Remediation string `json:"remediation,omitempty"`
		Message     string `json:"message,omitempty"`
	}
	var req resolveRequest
	_ = c.BodyParser(&req)
	actor := req.Actor
	if actor == "" {
		actor = "api"
	}

	incidentStore.Lock()
	defer incidentStore.Unlock()

	var found *models.Incident
	for i := range incidentStore.data {
		if incidentStore.data[i].ID == id {
			found = &incidentStore.data[i]
			break
		}
	}

	if found == nil {
		return c.Status(fiber.StatusNotFound).JSON(fiber.Map{
			"error":   "not_found",
			"message": "Incident not found",
		})
	}

	if found.Status == models.IncidentStatusResolved {
		return c.Status(fiber.StatusConflict).JSON(fiber.Map{
			"error":   "conflict",
			"message": "Incident is already resolved",
		})
	}

	now := time.Now().UTC()
	found.Status = models.IncidentStatusResolved
	found.ResolvedAt = &now
	found.Duration = now.Sub(found.CreatedAt).Seconds()
	found.UpdatedAt = now

	if req.RootCause != "" {
		found.RootCause = req.RootCause
	}
	if req.Remediation != "" {
		found.Remediation = req.Remediation
	}

	msg := req.Message
	if msg == "" {
		msg = fmt.Sprintf("Incident resolved by %s", actor)
	}

	found.Timeline = append(found.Timeline, models.TimelineEvent{
		ID:         uuid.New().String(),
		IncidentID: found.ID,
		Type:       models.TimelineEventResolved,
		Actor:      actor,
		Message:    msg,
		Timestamp:  now,
	})

	return c.JSON(found)
}

// GetIncidentStats returns aggregated incident statistics.
func GetIncidentStats(c *fiber.Ctx) error {
	incidentStore.RLock()
	defer incidentStore.RUnlock()

	todayStart := time.Now().UTC().Truncate(24 * time.Hour)

	stats := models.IncidentStats{}
	var totalResolveDuration float64
	var resolvedCount int

	for _, inc := range incidentStore.data {
		// Count active (non-resolved) incidents by severity.
		if inc.Status != models.IncidentStatusResolved {
			stats.TotalActive++
			switch inc.Severity {
			case models.SeverityCritical:
				stats.Critical++
			case models.SeverityHigh:
				stats.High++
			case models.SeverityMedium:
				stats.Medium++
			case models.SeverityLow:
				stats.Low++
			}
		}

		// Count opened today.
		if inc.CreatedAt.After(todayStart) || inc.CreatedAt.Equal(todayStart) {
			stats.OpenedToday++
		}

		// Count resolved today and accumulate MTTR.
		if inc.Status == models.IncidentStatusResolved && inc.ResolvedAt != nil {
			if inc.ResolvedAt.After(todayStart) || inc.ResolvedAt.Equal(todayStart) {
				stats.ResolvedToday++
			}
			resolvedCount++
			totalResolveDuration += inc.Duration
		}
	}

	// Calculate MTTR (mean time to resolve) in seconds.
	if resolvedCount > 0 {
		stats.MTTR = totalResolveDuration / float64(resolvedCount)
	}

	// Calculate resolution rate.
	total := len(incidentStore.data)
	if total > 0 {
		stats.ResolutionRate = float64(resolvedCount) / float64(total)
	}

	return c.JSON(stats)
}
