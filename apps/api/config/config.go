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
