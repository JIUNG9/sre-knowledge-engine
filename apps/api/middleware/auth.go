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
	"github.com/golang-jwt/jwt/v5"
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

		// A missing header is unauthenticated, full stop. This used to inject the
		// dev mock user — an admin — which meant that with OIDC configured, sending
		// a bad token got you 401 but sending no token at all got you admin. Dev
		// mode is reached by leaving issuerURL empty, not by omitting a header.
		if authHeader == "" {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error":   "missing_token",
				"message": "Authorization header is required",
			})
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

// allowedSigningAlgs is an allow-list, not a hint. Accepting whatever the token's
// own header asks for is how alg-confusion attacks work: a forged token declaring
// alg=none or alg=HS256 (with the RSA public key used as an HMAC secret) would
// otherwise validate.
var allowedSigningAlgs = []string{"RS256", "RS384", "RS512"}

// validateJWT parses a JWT and verifies its signature against the provider's JWKS,
// then validates exp, iss and aud.
//
// This previously decoded the token without verifying the signature at all — the
// old code fetched the public key, assigned it to `_`, and returned the claims from
// the *unverified* payload. Any attacker could mint a token by base64-encoding a
// header and a claims blob with the right iss/aud and a future exp; no key
// required. It also returned success when the JWKS endpoint was unreachable.
// Both are closed now: verification is mandatory and every failure path returns an
// error.
func validateJWT(token, jwksURL, issuerURL, clientID string) (*jwtClaims, error) {
	keyFunc := func(t *jwt.Token) (interface{}, error) {
		kid, ok := t.Header["kid"].(string)
		if !ok || kid == "" {
			return nil, fmt.Errorf("token header has no kid; cannot select a verification key")
		}
		// A JWKS we can't reach is a verification failure, not a pass.
		pubKey, err := getPublicKey(jwksURL, kid)
		if err != nil {
			return nil, fmt.Errorf("could not resolve signing key %q: %w", kid, err)
		}
		return pubKey, nil
	}

	parserOpts := []jwt.ParserOption{
		jwt.WithValidMethods(allowedSigningAlgs),
		jwt.WithExpirationRequired(),
	}
	if issuerURL != "" {
		parserOpts = append(parserOpts, jwt.WithIssuer(issuerURL))
	}
	if clientID != "" {
		parserOpts = append(parserOpts, jwt.WithAudience(clientID))
	}

	parsed, err := jwt.Parse(token, keyFunc, parserOpts...)
	if err != nil {
		return nil, fmt.Errorf("token verification failed: %w", err)
	}
	if !parsed.Valid {
		return nil, fmt.Errorf("token is not valid")
	}

	// Re-marshal the verified claims into the project's own struct so the rest of
	// the package keeps its existing shape (roles, realm_access, preferred_username).
	raw, err := json.Marshal(parsed.Claims)
	if err != nil {
		return nil, fmt.Errorf("failed to re-encode verified claims: %w", err)
	}
	var claims jwtClaims
	if err := json.Unmarshal(raw, &claims); err != nil {
		return nil, fmt.Errorf("failed to parse verified claims: %w", err)
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
