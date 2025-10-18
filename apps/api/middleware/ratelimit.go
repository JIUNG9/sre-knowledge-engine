package middleware

import (
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
)

// RateLimiter implements a simple token-bucket rate limiter per IP.
type RateLimiter struct {
	mu       sync.Mutex
	visitors map[string]*visitor
	limit    int
	window   time.Duration
}

type visitor struct {
	tokens    int
	lastReset time.Time
}

// NewRateLimiter creates a new rate limiter with the given requests per window.
func NewRateLimiter(limit int, window time.Duration) *RateLimiter {
	rl := &RateLimiter{
		visitors: make(map[string]*visitor),
		limit:    limit,
		window:   window,
	}

	// Periodically clean up stale entries.
	go rl.cleanup()

	return rl
}

// Handler returns a Fiber middleware handler for rate limiting.
func (rl *RateLimiter) Handler() fiber.Handler {
	return func(c *fiber.Ctx) error {
		ip := c.IP()

		rl.mu.Lock()
		v, exists := rl.visitors[ip]
		if !exists {
			rl.visitors[ip] = &visitor{
				tokens:    rl.limit - 1,
				lastReset: time.Now(),
			}
			rl.mu.Unlock()
			return c.Next()
		}

		// Reset tokens if the window has passed.
		if time.Since(v.lastReset) > rl.window {
			v.tokens = rl.limit - 1
			v.lastReset = time.Now()
			rl.mu.Unlock()
			return c.Next()
		}

		if v.tokens <= 0 {
			rl.mu.Unlock()
			return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
				"error":   "rate_limit_exceeded",
				"message": "Too many requests. Please try again later.",
			})
		}

		v.tokens--
		rl.mu.Unlock()
		return c.Next()
	}
}

// cleanup removes stale visitor entries every minute.
func (rl *RateLimiter) cleanup() {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		rl.mu.Lock()
		for ip, v := range rl.visitors {
			if time.Since(v.lastReset) > rl.window*2 {
				delete(rl.visitors, ip)
			}
		}
		rl.mu.Unlock()
	}
}
