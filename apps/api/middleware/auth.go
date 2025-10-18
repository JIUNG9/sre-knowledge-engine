package middleware

import (
	"github.com/gofiber/fiber/v2"
)

// MockUser represents the authenticated user injected by the auth middleware.
type MockUser struct {
	ID    string `json:"id"`
	Email string `json:"email"`
	Name  string `json:"name"`
	Role  string `json:"role"`
}

// Auth is a placeholder JWT authentication middleware.
// In production, this would validate a JWT token from the Authorization header.
func Auth() fiber.Handler {
	return func(c *fiber.Ctx) error {
		// TODO: Implement real JWT validation.
		// For now, inject a mock user into the context for development.
		authHeader := c.Get("Authorization")

		if authHeader == "" {
			// In development mode, allow unauthenticated requests with a mock user.
			c.Locals("user", MockUser{
				ID:    "user-001",
				Email: "dev@aegis.local",
				Name:  "Dev User",
				Role:  "admin",
			})
			return c.Next()
		}

		// TODO: Parse and validate JWT token.
		// For now, any non-empty Authorization header is accepted.
		c.Locals("user", MockUser{
			ID:    "user-001",
			Email: "dev@aegis.local",
			Name:  "Dev User",
			Role:  "admin",
		})

		return c.Next()
	}
}
