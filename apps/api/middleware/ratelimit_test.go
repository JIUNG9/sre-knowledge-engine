package middleware

import (
	"net/http"
	"net/http/httptest"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/gofiber/fiber/v2"
)

// newTestApp wires the limiter behind a trivial handler. ProxyHeader is set so
// c.IP() reads X-Forwarded-For, which is the only way to simulate distinct
// clients through fiber's in-process test transport.
func newTestApp(limit int, window time.Duration) *fiber.App {
	app := fiber.New(fiber.Config{ProxyHeader: fiber.HeaderXForwardedFor})
	rl := NewRateLimiter(limit, window)
	app.Use(rl.Handler())
	app.Get("/", func(c *fiber.Ctx) error { return c.SendString("ok") })
	return app
}

func doGet(t *testing.T, app *fiber.App, ip string) int {
	t.Helper()
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set(fiber.HeaderXForwardedFor, ip)
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("request: %v", err)
	}
	defer func() { _ = resp.Body.Close() }()
	return resp.StatusCode
}

func TestAllowsExactlyLimitThenBlocks(t *testing.T) {
	const limit = 3
	app := newTestApp(limit, time.Minute)

	for i := 1; i <= limit; i++ {
		if code := doGet(t, app, "10.0.0.1"); code != fiber.StatusOK {
			t.Fatalf("request %d/%d: got %d, want 200", i, limit, code)
		}
	}
	if code := doGet(t, app, "10.0.0.1"); code != fiber.StatusTooManyRequests {
		t.Errorf("request %d: got %d, want 429", limit+1, code)
	}
}

func TestBudgetResetsAfterWindow(t *testing.T) {
	const limit = 2
	window := 60 * time.Millisecond
	app := newTestApp(limit, window)

	for i := 0; i < limit; i++ {
		if code := doGet(t, app, "10.0.0.2"); code != fiber.StatusOK {
			t.Fatalf("warmup request %d: got %d", i, code)
		}
	}
	if code := doGet(t, app, "10.0.0.2"); code != fiber.StatusTooManyRequests {
		t.Fatalf("expected to be limited before the window elapses, got %d", code)
	}

	// The reset is `time.Since(lastReset) > window`, so wait past the boundary.
	time.Sleep(window * 2)

	if code := doGet(t, app, "10.0.0.2"); code != fiber.StatusOK {
		t.Errorf("after the window elapsed: got %d, want 200", code)
	}
}

// One noisy client must not consume another client's budget.
func TestLimitIsPerIP(t *testing.T) {
	const limit = 2
	app := newTestApp(limit, time.Minute)

	for i := 0; i < limit; i++ {
		doGet(t, app, "10.0.0.3")
	}
	if code := doGet(t, app, "10.0.0.3"); code != fiber.StatusTooManyRequests {
		t.Fatalf("first IP should be exhausted, got %d", code)
	}
	if code := doGet(t, app, "10.0.0.4"); code != fiber.StatusOK {
		t.Errorf("second IP was affected by the first: got %d, want 200", code)
	}
}

// The counter is shared mutable state. Run with -race: this fails loudly if the
// mutex is ever dropped, and the exact-count assertion catches a lost update even
// when the race detector doesn't fire.
func TestConcurrentRequestsAllowExactlyLimit(t *testing.T) {
	const (
		limit    = 20
		attempts = 200
	)
	app := newTestApp(limit, time.Minute)

	var allowed, limited int64
	var wg sync.WaitGroup
	wg.Add(attempts)
	for i := 0; i < attempts; i++ {
		go func() {
			defer wg.Done()
			req := httptest.NewRequest(http.MethodGet, "/", nil)
			req.Header.Set(fiber.HeaderXForwardedFor, "10.0.0.5")
			resp, err := app.Test(req, 10_000)
			if err != nil {
				return
			}
			defer func() { _ = resp.Body.Close() }()
			switch resp.StatusCode {
			case fiber.StatusOK:
				atomic.AddInt64(&allowed, 1)
			case fiber.StatusTooManyRequests:
				atomic.AddInt64(&limited, 1)
			}
		}()
	}
	wg.Wait()

	if allowed != limit {
		t.Errorf("allowed %d requests, want exactly %d (lost update under concurrency)", allowed, limit)
	}
	if allowed+limited != attempts {
		t.Errorf("accounted for %d of %d requests", allowed+limited, attempts)
	}
}

func TestLimitedResponseCarriesMachineReadableError(t *testing.T) {
	app := newTestApp(1, time.Minute)
	doGet(t, app, "10.0.0.6")

	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.Header.Set(fiber.HeaderXForwardedFor, "10.0.0.6")
	resp, err := app.Test(req)
	if err != nil {
		t.Fatalf("request: %v", err)
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode != fiber.StatusTooManyRequests {
		t.Fatalf("got %d, want 429", resp.StatusCode)
	}
	buf := make([]byte, 512)
	n, _ := resp.Body.Read(buf)
	body := string(buf[:n])
	// Clients branch on the code, not the prose, so the code is what's asserted.
	if !contains(body, "rate_limit_exceeded") {
		t.Errorf("body missing the rate_limit_exceeded code: %s", body)
	}
}

func contains(haystack, needle string) bool {
	return len(haystack) >= len(needle) && func() bool {
		for i := 0; i+len(needle) <= len(haystack); i++ {
			if haystack[i:i+len(needle)] == needle {
				return true
			}
		}
		return false
	}()
}
