package middleware

import (
	"crypto/rand"
	"crypto/rsa"
	"encoding/base64"
	"encoding/json"
	"math/big"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/golang-jwt/jwt/v5"
)

const (
	testKid      = "test-key-1"
	testClientID = "aegis"
)

// jwksServer stands in for Keycloak: it serves the public half of a key we hold the
// private half of, so tests can mint genuinely-signed tokens.
func jwksServer(t *testing.T, pub *rsa.PublicKey, kid string) *httptest.Server {
	t.Helper()
	body, err := json.Marshal(jwks{Keys: []jwk{{
		Kid: kid,
		Kty: "RSA",
		Alg: "RS256",
		Use: "sig",
		N:   base64.RawURLEncoding.EncodeToString(pub.N.Bytes()),
		E:   base64.RawURLEncoding.EncodeToString(big.NewInt(int64(pub.E)).Bytes()),
	}}})
	if err != nil {
		t.Fatalf("marshal jwks: %v", err)
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/protocol/openid-connect/certs", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(body)
	})
	return httptest.NewServer(mux)
}

// resetKeyCache clears the package-level JWKS cache so each test starts clean.
func resetKeyCache(t *testing.T) {
	t.Helper()
	keyCache.mu.Lock()
	keyCache.keys = make(map[string]*rsa.PublicKey)
	keyCache.fetchedAt = time.Time{}
	keyCache.mu.Unlock()
}

func signToken(t *testing.T, priv *rsa.PrivateKey, kid string, claims jwt.MapClaims) string {
	t.Helper()
	tok := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
	tok.Header["kid"] = kid
	s, err := tok.SignedString(priv)
	if err != nil {
		t.Fatalf("sign: %v", err)
	}
	return s
}

func validClaims(issuer string) jwt.MapClaims {
	return jwt.MapClaims{
		"sub":   "user-42",
		"email": "someone@example.com",
		"name":  "Some One",
		"iss":   issuer,
		"aud":   testClientID,
		"exp":   time.Now().Add(time.Hour).Unix(),
		"iat":   time.Now().Unix(),
	}
}

// authApp mounts OIDCAuth and echoes back the role the middleware resolved, so a
// test can tell "allowed through as admin" from "rejected".
func authApp(issuer, clientID string) *fiber.App {
	app := fiber.New()
	app.Use(OIDCAuth(issuer, clientID))
	app.Get("/", func(c *fiber.Ctx) error {
		u, _ := c.Locals("user").(User)
		return c.JSON(fiber.Map{"role": u.Role, "id": u.ID})
	})
	return app
}

func get(t *testing.T, app *fiber.App, authHeader string) (int, string) {
	t.Helper()
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	if authHeader != "" {
		req.Header.Set("Authorization", authHeader)
	}
	resp, err := app.Test(req, 5000)
	if err != nil {
		t.Fatalf("request: %v", err)
	}
	defer func() { _ = resp.Body.Close() }()
	buf := make([]byte, 1024)
	n, _ := resp.Body.Read(buf)
	return resp.StatusCode, string(buf[:n])
}

func TestGenuinelySignedTokenIsAccepted(t *testing.T) {
	resetKeyCache(t)
	priv, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatalf("keygen: %v", err)
	}
	srv := jwksServer(t, &priv.PublicKey, testKid)
	defer srv.Close()

	app := authApp(srv.URL, testClientID)
	token := signToken(t, priv, testKid, validClaims(srv.URL))

	code, body := get(t, app, "Bearer "+token)
	if code != fiber.StatusOK {
		t.Fatalf("valid token rejected: %d %s", code, body)
	}
	if !strings.Contains(body, "user-42") {
		t.Errorf("claims not propagated to the handler: %s", body)
	}
}

// The regression that matters most. The old implementation never verified the
// signature — it looked the key up, discarded it, and trusted the payload. A token
// signed by a key the provider has never heard of must be rejected.
func TestTokenSignedByAnUnknownKeyIsRejected(t *testing.T) {
	resetKeyCache(t)
	real, _ := rsa.GenerateKey(rand.Reader, 2048)
	attacker, _ := rsa.GenerateKey(rand.Reader, 2048)

	srv := jwksServer(t, &real.PublicKey, testKid)
	defer srv.Close()

	app := authApp(srv.URL, testClientID)
	// Correct kid, correct iss, correct aud, unexpired — only the signature is wrong.
	forged := signToken(t, attacker, testKid, validClaims(srv.URL))

	code, body := get(t, app, "Bearer "+forged)
	if code != fiber.StatusUnauthorized {
		t.Fatalf("forged token accepted with %d: %s", code, body)
	}
}

// An unsigned token with alg=none, which is the cheapest forgery there is.
func TestUnsignedTokenIsRejected(t *testing.T) {
	resetKeyCache(t)
	priv, _ := rsa.GenerateKey(rand.Reader, 2048)
	srv := jwksServer(t, &priv.PublicKey, testKid)
	defer srv.Close()

	header := base64.RawURLEncoding.EncodeToString(
		[]byte(`{"alg":"none","typ":"JWT","kid":"` + testKid + `"}`))
	payload, _ := json.Marshal(validClaims(srv.URL))
	unsigned := header + "." + base64.RawURLEncoding.EncodeToString(payload) + "."

	app := authApp(srv.URL, testClientID)
	if code, body := get(t, app, "Bearer "+unsigned); code != fiber.StatusUnauthorized {
		t.Fatalf("alg=none token accepted with %d: %s", code, body)
	}
}

// The other bypass: with OIDC configured, no header used to yield the dev mock user,
// which had role "admin". Omitting credentials was easier than supplying bad ones.
func TestMissingAuthHeaderIsUnauthorizedWhenOIDCConfigured(t *testing.T) {
	resetKeyCache(t)
	priv, _ := rsa.GenerateKey(rand.Reader, 2048)
	srv := jwksServer(t, &priv.PublicKey, testKid)
	defer srv.Close()

	app := authApp(srv.URL, testClientID)
	code, body := get(t, app, "")
	if code != fiber.StatusUnauthorized {
		t.Fatalf("missing header allowed through with %d: %s", code, body)
	}
	if strings.Contains(body, "admin") {
		t.Fatalf("missing header was granted an admin identity: %s", body)
	}
}

// JWKS unreachable used to return the claims anyway. It must fail closed.
func TestUnreachableJWKSFailsClosed(t *testing.T) {
	resetKeyCache(t)
	priv, _ := rsa.GenerateKey(rand.Reader, 2048)
	srv := jwksServer(t, &priv.PublicKey, testKid)
	issuer := srv.URL
	token := signToken(t, priv, testKid, validClaims(issuer))
	srv.Close() // provider is now down

	app := authApp(issuer, testClientID)
	if code, body := get(t, app, "Bearer "+token); code != fiber.StatusUnauthorized {
		t.Fatalf("token accepted while JWKS was unreachable: %d %s", code, body)
	}
}

func TestClaimValidation(t *testing.T) {
	resetKeyCache(t)
	priv, _ := rsa.GenerateKey(rand.Reader, 2048)
	srv := jwksServer(t, &priv.PublicKey, testKid)
	defer srv.Close()
	app := authApp(srv.URL, testClientID)

	cases := []struct {
		name   string
		mutate func(jwt.MapClaims)
	}{
		{"expired", func(c jwt.MapClaims) { c["exp"] = time.Now().Add(-time.Hour).Unix() }},
		{"no exp at all", func(c jwt.MapClaims) { delete(c, "exp") }},
		{"wrong issuer", func(c jwt.MapClaims) { c["iss"] = "https://evil.example" }},
		{"wrong audience", func(c jwt.MapClaims) { c["aud"] = "some-other-client" }},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			claims := validClaims(srv.URL)
			tc.mutate(claims)
			code, body := get(t, app, "Bearer "+signToken(t, priv, testKid, claims))
			if code != fiber.StatusUnauthorized {
				t.Errorf("accepted with %d: %s", code, body)
			}
		})
	}
}

func TestMalformedAuthorizationHeader(t *testing.T) {
	resetKeyCache(t)
	priv, _ := rsa.GenerateKey(rand.Reader, 2048)
	srv := jwksServer(t, &priv.PublicKey, testKid)
	defer srv.Close()
	app := authApp(srv.URL, testClientID)

	for _, h := range []string{
		"just-a-token-no-scheme",
		"Basic dXNlcjpwYXNz",
		"Bearer",
		"Bearer not.a.jwt",
	} {
		t.Run(h, func(t *testing.T) {
			if code, body := get(t, app, h); code != fiber.StatusUnauthorized {
				t.Errorf("accepted %q with %d: %s", h, code, body)
			}
		})
	}
}

// A token with no kid gives us nothing to look up, so it can't be verified.
func TestTokenWithoutKidIsRejected(t *testing.T) {
	resetKeyCache(t)
	priv, _ := rsa.GenerateKey(rand.Reader, 2048)
	srv := jwksServer(t, &priv.PublicKey, testKid)
	defer srv.Close()

	tok := jwt.NewWithClaims(jwt.SigningMethodRS256, validClaims(srv.URL))
	signed, err := tok.SignedString(priv) // no kid header set
	if err != nil {
		t.Fatalf("sign: %v", err)
	}

	app := authApp(srv.URL, testClientID)
	if code, body := get(t, app, "Bearer "+signed); code != fiber.StatusUnauthorized {
		t.Fatalf("token without kid accepted with %d: %s", code, body)
	}
}

// Dev mode is entered by leaving the issuer empty — explicitly, in config — not by
// withholding a header from a configured deployment.
func TestEmptyIssuerUsesDevModeExplicitly(t *testing.T) {
	app := authApp("", "")
	code, body := get(t, app, "")
	if code != fiber.StatusOK {
		t.Fatalf("dev mode should allow through, got %d: %s", code, body)
	}
	if !strings.Contains(body, "admin") {
		t.Errorf("dev mode should inject the mock admin user, got %s", body)
	}
}

func TestUserFromClaimsRoleMapping(t *testing.T) {
	cases := []struct {
		name string
		in   jwtClaims
		want string
	}{
		{"no roles defaults to viewer", jwtClaims{Sub: "a"}, "viewer"},
		{"admin role", jwtClaims{Roles: []string{"admin"}}, "admin"},
		{"keycloak aegis-admin", jwtClaims{Roles: []string{"aegis-admin"}}, "admin"},
		{"member role", jwtClaims{Roles: []string{"member"}}, "member"},
		{"unrelated role stays viewer", jwtClaims{Roles: []string{"billing-reader"}}, "viewer"},
		{"admin wins over member", jwtClaims{Roles: []string{"member", "admin"}}, "admin"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			claims := tc.in
			if got := userFromClaims(&claims).Role; got != tc.want {
				t.Errorf("role = %q, want %q", got, tc.want)
			}
		})
	}
}

func TestUserFromClaimsNameFallback(t *testing.T) {
	cases := []struct {
		name string
		in   jwtClaims
		want string
	}{
		{"name preferred", jwtClaims{Name: "Full Name", PreferredUser: "pu", Email: "e@x"}, "Full Name"},
		{"falls back to preferred_username", jwtClaims{PreferredUser: "pu", Email: "e@x"}, "pu"},
		{"falls back to email", jwtClaims{Email: "e@x"}, "e@x"},
		{"all empty", jwtClaims{}, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			claims := tc.in
			if got := userFromClaims(&claims).Name; got != tc.want {
				t.Errorf("name = %q, want %q", got, tc.want)
			}
		})
	}
}
