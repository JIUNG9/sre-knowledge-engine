package handlers

import (
	"encoding/json"
	"math/rand"
	"strings"
	"sync"
	"time"

	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"

	"github.com/junegu/aegis/api/mock"
	"github.com/junegu/aegis/api/models"
)

// WSHub manages active WebSocket connections for log streaming.
type WSHub struct {
	mu      sync.RWMutex
	clients map[*websocket.Conn]wsFilter
	logger  *zap.Logger
}

// wsFilter holds per-connection filter criteria.
type wsFilter struct {
	Levels   map[string]bool
	Services map[string]bool
}

// NewWSHub creates a new WebSocket hub.
func NewWSHub(logger *zap.Logger) *WSHub {
	return &WSHub{
		clients: make(map[*websocket.Conn]wsFilter),
		logger:  logger,
	}
}

// UpgradeMiddleware returns a Fiber middleware that upgrades HTTP to WebSocket.
func UpgradeMiddleware() fiber.Handler {
	return func(c *fiber.Ctx) error {
		if websocket.IsWebSocketUpgrade(c) {
			return c.Next()
		}
		return fiber.ErrUpgradeRequired
	}
}

// HandleStreamLogs is the WebSocket handler for live log streaming.
// It accepts optional query parameters for filtering: levels (comma-separated), services (comma-separated).
func (h *WSHub) HandleStreamLogs(c *websocket.Conn) {
	// Parse filter parameters from the initial request.
	levelsParam := c.Query("levels")
	servicesParam := c.Query("services")

	filter := wsFilter{
		Levels:   make(map[string]bool),
		Services: make(map[string]bool),
	}

	if levelsParam != "" {
		for _, l := range strings.Split(levelsParam, ",") {
			l = strings.TrimSpace(l)
			if l != "" {
				filter.Levels[l] = true
			}
		}
	}
	if servicesParam != "" {
		for _, s := range strings.Split(servicesParam, ",") {
			s = strings.TrimSpace(s)
			if s != "" {
				filter.Services[s] = true
			}
		}
	}

	// Register this client.
	h.mu.Lock()
	h.clients[c] = filter
	h.mu.Unlock()

	h.logger.Info("WebSocket client connected",
		zap.Int("total_clients", h.clientCount()),
		zap.String("levels", levelsParam),
		zap.String("services", servicesParam),
	)

	// Clean up on disconnect.
	defer func() {
		h.mu.Lock()
		delete(h.clients, c)
		h.mu.Unlock()
		c.Close()
		h.logger.Info("WebSocket client disconnected",
			zap.Int("remaining_clients", h.clientCount()),
		)
	}()

	// Start a goroutine that sends mock log entries at random intervals.
	done := make(chan struct{})
	go func() {
		defer close(done)
		for {
			// Random interval between 1 and 3 seconds.
			interval := time.Duration(1000+rand.Intn(2000)) * time.Millisecond
			time.Sleep(interval)

			entry := mock.GenerateSingleMockLog()
			entry.Timestamp = time.Now()

			// Apply filters.
			if len(filter.Levels) > 0 && !filter.Levels[entry.Level] {
				continue
			}
			if len(filter.Services) > 0 && !filter.Services[entry.Service] {
				continue
			}

			data, err := json.Marshal(entry)
			if err != nil {
				h.logger.Error("Failed to marshal log entry", zap.Error(err))
				continue
			}

			if err := c.WriteMessage(websocket.TextMessage, data); err != nil {
				// Client disconnected.
				return
			}
		}
	}()

	// Read loop to keep the connection alive and detect client disconnect.
	for {
		_, _, err := c.ReadMessage()
		if err != nil {
			// Client disconnected or error.
			break
		}
	}
}

// clientCount returns the number of active clients.
func (h *WSHub) clientCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.clients)
}

// BroadcastLog sends a log entry to all connected clients whose filters match.
func (h *WSHub) BroadcastLog(entry models.LogEntry) {
	data, err := json.Marshal(entry)
	if err != nil {
		return
	}

	h.mu.RLock()
	defer h.mu.RUnlock()

	for conn, filter := range h.clients {
		// Check level filter.
		if len(filter.Levels) > 0 && !filter.Levels[entry.Level] {
			continue
		}
		// Check service filter.
		if len(filter.Services) > 0 && !filter.Services[entry.Service] {
			continue
		}

		if err := conn.WriteMessage(websocket.TextMessage, data); err != nil {
			// Will be cleaned up by the read loop.
			continue
		}
	}
}
