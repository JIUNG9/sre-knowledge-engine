package store

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	"go.uber.org/zap"
)

// PostgresStore implements a PostgreSQL-backed store for Aegis configuration,
// targets, and other relational data. Log data remains in ClickHouse.
type PostgresStore struct {
	db     *sql.DB
	logger *zap.Logger
}

// NewPostgresStore creates a new PostgresStore connected to the given DSN.
// DSN format: postgres://user:password@host:port/database?sslmode=disable
func NewPostgresStore(dsn string, logger *zap.Logger) (*PostgresStore, error) {
	db, err := sql.Open("postgres", dsn)
	if err != nil {
		return nil, fmt.Errorf("failed to open PostgreSQL connection: %w", err)
	}

	// Configure connection pool.
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)
	db.SetConnMaxIdleTime(1 * time.Minute)

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := db.PingContext(ctx); err != nil {
		return nil, fmt.Errorf("failed to ping PostgreSQL: %w", err)
	}

	store := &PostgresStore{
		db:     db,
		logger: logger,
	}

	// Run schema migrations on startup.
	if err := store.migrate(ctx); err != nil {
		return nil, fmt.Errorf("failed to run migrations: %w", err)
	}

	return store, nil
}

// DB returns the underlying *sql.DB for use by sub-stores.
func (s *PostgresStore) DB() *sql.DB {
	return s.db
}

// HealthCheck verifies the database connection is alive.
func (s *PostgresStore) HealthCheck(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

// Close closes the database connection pool.
func (s *PostgresStore) Close() error {
	return s.db.Close()
}

// migrate runs all required DDL statements to ensure tables exist.
func (s *PostgresStore) migrate(ctx context.Context) error {
	migrations := []string{
		CreateConfigTableQuery,
		CreateTargetsTableQuery,
	}

	for _, ddl := range migrations {
		if _, err := s.db.ExecContext(ctx, ddl); err != nil {
			return fmt.Errorf("migration failed: %w", err)
		}
	}

	s.logger.Info("PostgreSQL schema migrations complete")
	return nil
}

// CreateConfigTableQuery is the DDL for the aegis_config table.
const CreateConfigTableQuery = `
CREATE TABLE IF NOT EXISTS aegis_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section VARCHAR(64) NOT NULL,
    key VARCHAR(128) NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(section, key)
);
`

// CreateTargetsTableQuery is the DDL for the team_targets table.
const CreateTargetsTableQuery = `
CREATE TABLE IF NOT EXISTS team_targets (
    account_id VARCHAR(128) PRIMARY KEY,
    slo_target DOUBLE PRECISION NOT NULL DEFAULT 99.9,
    mttr_target DOUBLE PRECISION NOT NULL DEFAULT 60,
    sla_target DOUBLE PRECISION NOT NULL DEFAULT 99.95,
    error_budget DOUBLE PRECISION NOT NULL DEFAULT 43.2,
    cost_budget DOUBLE PRECISION NOT NULL DEFAULT 10000,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(256) NOT NULL DEFAULT 'system'
);
`
