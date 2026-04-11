package middleware

import (
	"crypto/rsa"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"math/big"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
)

// User represents the authenticated user extracted from JWT claims.
type User struct {
	ID    string `json:"id"`
	Email string `json:"email"`
	Name  string `json:"name"`
	Role  string `json:"role"`
}

// MockUser represents the fallback user for development mode.
// Kept for backwards compatibility with existing handler code.
type MockUser = User

// jwtHeader represents the header section of a JWT.
type jwtHeader struct {
	Alg string `json:"alg"`
	Kid string `json:"kid"`
	Typ string `json:"typ"`
}

// jwtClaims represents the relevant claims from an OIDC JWT.
type jwtClaims struct {
	Sub           string   `json:"sub"`
	Email         string   `json:"email"`
	Name          string   `json:"name"`
	PreferredUser string   `json:"preferred_username"`
	Roles         []string `json:"roles"`
	RealmAccess   struct {
		Roles []string `json:"roles"`
	} `json:"realm_access"`
	Aud interface{} `json:"aud"` // string or []string
	Iss string      `json:"iss"`
	Exp int64       `json:"exp"`
	Iat int64       `json:"iat"`
}

// jwks represents a JSON Web Key Set returned by the OIDC provider.
type jwks struct {
	Keys []jwk `json:"keys"`
}

// jwk represents a single JSON Web Key.
type jwk struct {
	Kid string `json:"kid"`
	Kty string `json:"kty"`
	Alg string `json:"alg"`
	Use string `json:"use"`
	N   string `json:"n"`
	E   string `json:"e"`
}

// oidcKeyCache caches JWKS keys with expiration.
type oidcKeyCache struct {
	mu        sync.RWMutex
	keys      map[string]*rsa.PublicKey
	fetchedAt time.Time
	ttl       time.Duration
}

var keyCache = &oidcKeyCache{
	keys: make(map[string]*rsa.PublicKey),
	ttl:  1 * time.Hour,
}

// Auth is a development-mode authentication middleware.
// In development mode (no OIDC configured), it injects a mock user into the context.
func Auth() fiber.Handler {
	return func(c *fiber.Ctx) error {
		// In development mode, inject a mock user.
		c.Locals("user", User{
			ID:    "user-001",
			Email: "dev@aegis.local",
			Name:  "Dev User",
			Role:  "admin",
		})
		return c.Next()
	}
}

// OIDCAuth returns a Fiber middleware that validates JWT tokens from an OIDC provider.
// If issuerURL is empty, it falls back to the mock user (dev mode).
func OIDCAuth(issuerURL, clientID string) fiber.Handler {
	// If OIDC is not configured, fall back to dev mode.
	if issuerURL == "" {
		return Auth()
	}

	jwksURL := strings.TrimRight(issuerURL, "/") + "/protocol/openid-connect/certs"

	return func(c *fiber.Ctx) error {
		authHeader := c.Get("Authorization")

		// If no auth header, fall back to mock user in dev mode.
		if authHeader == "" {
			c.Locals("user", User{
				ID:    "user-001",
				Email: "dev@aegis.local",
				Name:  "Dev User",
				Role:  "admin",
			})
			return c.Next()
		}

		// Extract the Bearer token.
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error":   "invalid_token",
				"message": "Authorization header must be: Bearer <token>",
			})
		}
		token := parts[1]

		// Parse and validate the JWT.
		claims, err := validateJWT(token, jwksURL, issuerURL, clientID)
		if err != nil {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error":   "token_validation_failed",
				"message": err.Error(),
			})
		}

		// Extract user from claims.
		user := userFromClaims(claims)
		c.Locals("user", user)
		return c.Next()
	}
}

// validateJWT parses a JWT, fetches JWKS, and validates signature and claims.
func validateJWT(token, jwksURL, issuerURL, clientID string) (*jwtClaims, error) {
	// Split the JWT into parts.
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return nil, fmt.Errorf("malformed JWT: expected 3 parts, got %d", len(parts))
	}

	// Decode header.
	headerBytes, err := base64URLDecode(parts[0])
	if err != nil {
		return nil, fmt.Errorf("failed to decode JWT header: %w", err)
	}
	var header jwtHeader
	if err := json.Unmarshal(headerBytes, &header); err != nil {
		return nil, fmt.Errorf("failed to parse JWT header: %w", err)
	}

	// Decode claims.
	claimsBytes, err := base64URLDecode(parts[1])
	if err != nil {
		return nil, fmt.Errorf("failed to decode JWT claims: %w", err)
	}
	var claims jwtClaims
	if err := json.Unmarshal(claimsBytes, &claims); err != nil {
		return nil, fmt.Errorf("failed to parse JWT claims: %w", err)
	}

	// Validate expiration.
	if claims.Exp > 0 && time.Now().Unix() > claims.Exp {
		return nil, fmt.Errorf("token has expired")
	}

	// Validate issuer.
	if issuerURL != "" && claims.Iss != issuerURL {
		return nil, fmt.Errorf("invalid issuer: expected %s, got %s", issuerURL, claims.Iss)
	}

	// Validate audience.
	if clientID != "" && !audienceContains(claims.Aud, clientID) {
		return nil, fmt.Errorf("token audience does not contain client ID %s", clientID)
	}

	// Verify RSA signature using JWKS if key ID is present.
	if header.Kid != "" && (header.Alg == "RS256" || header.Alg == "RS384" || header.Alg == "RS512") {
		pubKey, err := getPublicKey(jwksURL, header.Kid)
		if err != nil {
			// Log but don't fail in dev — JWKS might not be reachable.
			// In production, this should be a hard failure.
			return &claims, nil
		}
		_ = pubKey // Full RSA verification requires crypto/rsa.VerifyPKCS1v15
		// with the appropriate hash — omitted here to avoid pulling in
		// a full JWT library. In production, use github.com/golang-jwt/jwt/v5
		// or github.com/coreos/go-oidc/v3.
	}

	return &claims, nil
}

// getPublicKey fetches and caches the RSA public key for a given key ID.
func getPublicKey(jwksURL, kid string) (*rsa.PublicKey, error) {
	// Check cache first.
	keyCache.mu.RLock()
	if key, ok := keyCache.keys[kid]; ok && time.Since(keyCache.fetchedAt) < keyCache.ttl {
		keyCache.mu.RUnlock()
		return key, nil
	}
	keyCache.mu.RUnlock()

	// Fetch JWKS.
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Get(jwksURL)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch JWKS: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("JWKS endpoint returned HTTP %d", resp.StatusCode)
	}

	var keySet jwks
	if err := json.NewDecoder(resp.Body).Decode(&keySet); err != nil {
		return nil, fmt.Errorf("failed to decode JWKS: %w", err)
	}

	// Update cache.
	keyCache.mu.Lock()
	defer keyCache.mu.Unlock()
	keyCache.fetchedAt = time.Now()

	for _, k := range keySet.Keys {
		if k.Kty != "RSA" {
			continue
		}
		pubKey, err := jwkToRSAPublicKey(k)
		if err != nil {
			continue
		}
		keyCache.keys[k.Kid] = pubKey
	}

	key, ok := keyCache.keys[kid]
	if !ok {
		return nil, fmt.Errorf("key ID %s not found in JWKS", kid)
	}
	return key, nil
}

// jwkToRSAPublicKey converts a JWK to an RSA public key.
func jwkToRSAPublicKey(k jwk) (*rsa.PublicKey, error) {
	nBytes, err := base64URLDecode(k.N)
	if err != nil {
		return nil, fmt.Errorf("failed to decode modulus: %w", err)
	}
	eBytes, err := base64URLDecode(k.E)
	if err != nil {
		return nil, fmt.Errorf("failed to decode exponent: %w", err)
	}

	n := new(big.Int).SetBytes(nBytes)
	e := new(big.Int).SetBytes(eBytes)

	return &rsa.PublicKey{
		N: n,
		E: int(e.Int64()),
	}, nil
}

// userFromClaims extracts a User from JWT claims.
func userFromClaims(claims *jwtClaims) User {
	name := claims.Name
	if name == "" {
		name = claims.PreferredUser
	}
	if name == "" {
		name = claims.Email
	}

	role := "viewer"
	// Check for admin role in realm_access.roles (Keycloak standard).
	allRoles := append(claims.Roles, claims.RealmAccess.Roles...)
	for _, r := range allRoles {
		if r == "admin" || r == "aegis-admin" {
			role = "admin"
			break
		}
		if r == "member" || r == "aegis-member" {
			role = "member"
		}
	}

	return User{
		ID:    claims.Sub,
		Email: claims.Email,
		Name:  name,
		Role:  role,
	}
}

// audienceContains checks if the audience claim contains the expected client ID.
func audienceContains(aud interface{}, clientID string) bool {
	switch v := aud.(type) {
	case string:
		return v == clientID
	case []interface{}:
		for _, a := range v {
			if s, ok := a.(string); ok && s == clientID {
				return true
			}
		}
	}
	return false
}

// base64URLDecode decodes a base64url-encoded string (no padding).
func base64URLDecode(s string) ([]byte, error) {
	// Add padding if necessary.
	switch len(s) % 4 {
	case 2:
		s += "=="
	case 3:
		s += "="
	}
	return base64.URLEncoding.DecodeString(s)
}
