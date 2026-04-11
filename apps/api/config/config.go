package config

import (
	"os"
	"strconv"
)

// Config holds all configuration for the Aegis API server.
type Config struct {
	Port        string
	Environment string
	LogLevel    string
	CORSOrigins string
	RateLimit   int
	JWTSecret   string

	// Database connections.
	PostgresURL   string
	ClickHouseURL string

	// OIDC authentication.
	OIDCIssuerURL string
	OIDCClientID  string

	// Encryption key for API secrets at rest.
	EncryptionKey string
}

// Load reads configuration from environment variables with sensible defaults.
func Load() *Config {
	return &Config{
		Port:        getEnv("PORT", "8080"),
		Environment: getEnv("ENVIRONMENT", "development"),
		LogLevel:    getEnv("LOG_LEVEL", "info"),
		CORSOrigins: getEnv("CORS_ORIGINS", "*"),
		RateLimit:   getEnvInt("RATE_LIMIT", 100),
		JWTSecret:   getEnv("JWT_SECRET", "aegis-dev-secret-change-me"),

		PostgresURL:   getEnv("POSTGRES_URL", ""),
		ClickHouseURL: getEnv("CLICKHOUSE_URL", ""),

		OIDCIssuerURL: getEnv("OIDC_ISSUER_URL", ""),
		OIDCClientID:  getEnv("OIDC_CLIENT_ID", ""),

		EncryptionKey: getEnv("ENCRYPTION_KEY", "aegis-dev-encryption-key"),
	}
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	if value, ok := os.LookupEnv(key); ok {
		if i, err := strconv.Atoi(value); err == nil {
			return i
		}
	}
	return fallback
}
