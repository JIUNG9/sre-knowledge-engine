package store

import (
	"context"
	"database/sql"
	"fmt"
	"time"
)

// ConfigStore provides PostgreSQL-backed configuration storage for Aegis.
// Falls back to in-memory storage when PostgreSQL is not available.
type ConfigStore struct {
	db *sql.DB
}

// NewConfigStore creates a new ConfigStore. If db is nil, operations will return
// graceful errors that callers can handle by falling back to defaults.
func NewConfigStore(db *sql.DB) *ConfigStore {
	return &ConfigStore{db: db}
}

// SaveConfig inserts or updates a configuration entry.
func (s *ConfigStore) SaveConfig(ctx context.Context, section, key, value string) error {
	if s.db == nil {
		return fmt.Errorf("database not available")
	}

	query := `
		INSERT INTO aegis_config (section, key, value, updated_at)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (section, key)
		DO UPDATE SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
	`

	_, err := s.db.ExecContext(ctx, query, section, key, value, time.Now().UTC())
	if err != nil {
		return fmt.Errorf("failed to save config [%s/%s]: %w", section, key, err)
	}
	return nil
}

// GetConfig retrieves a single configuration value by section and key.
func (s *ConfigStore) GetConfig(ctx context.Context, section, key string) (string, error) {
	if s.db == nil {
		return "", fmt.Errorf("database not available")
	}

	query := `SELECT value FROM aegis_config WHERE section = $1 AND key = $2`

	var value string
	err := s.db.QueryRowContext(ctx, query, section, key).Scan(&value)
	if err == sql.ErrNoRows {
		return "", fmt.Errorf("config not found: %s/%s", section, key)
	}
	if err != nil {
		return "", fmt.Errorf("failed to get config [%s/%s]: %w", section, key, err)
	}
	return value, nil
}

// GetSection retrieves all key-value pairs for a given section.
func (s *ConfigStore) GetSection(ctx context.Context, section string) (map[string]string, error) {
	if s.db == nil {
		return nil, fmt.Errorf("database not available")
	}

	query := `SELECT key, value FROM aegis_config WHERE section = $1 ORDER BY key`

	rows, err := s.db.QueryContext(ctx, query, section)
	if err != nil {
		return nil, fmt.Errorf("failed to get section [%s]: %w", section, err)
	}
	defer rows.Close()

	result := make(map[string]string)
	for rows.Next() {
		var k, v string
		if err := rows.Scan(&k, &v); err != nil {
			return nil, fmt.Errorf("failed to scan config row: %w", err)
		}
		result[k] = v
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating config rows: %w", err)
	}
	return result, nil
}

// DeleteConfig removes a configuration entry by section and key.
func (s *ConfigStore) DeleteConfig(ctx context.Context, section, key string) error {
	if s.db == nil {
		return fmt.Errorf("database not available")
	}

	query := `DELETE FROM aegis_config WHERE section = $1 AND key = $2`

	result, err := s.db.ExecContext(ctx, query, section, key)
	if err != nil {
		return fmt.Errorf("failed to delete config [%s/%s]: %w", section, key, err)
	}

	rows, _ := result.RowsAffected()
	if rows == 0 {
		return fmt.Errorf("config not found: %s/%s", section, key)
	}
	return nil
}

// IsSetupComplete checks if the setup wizard has been marked as complete.
func (s *ConfigStore) IsSetupComplete(ctx context.Context) bool {
	if s.db == nil {
		return false
	}

	val, err := s.GetConfig(ctx, "general", "setup_complete")
	if err != nil {
		return false
	}
	return val == "true"
}

// MarkSetupComplete sets the setup_complete flag to true.
func (s *ConfigStore) MarkSetupComplete(ctx context.Context) error {
	return s.SaveConfig(ctx, "general", "setup_complete", "true")
}

// ListSections returns all distinct sections that have configuration entries.
func (s *ConfigStore) ListSections(ctx context.Context) ([]string, error) {
	if s.db == nil {
		return nil, fmt.Errorf("database not available")
	}

	query := `SELECT DISTINCT section FROM aegis_config ORDER BY section`

	rows, err := s.db.QueryContext(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("failed to list sections: %w", err)
	}
	defer rows.Close()

	var sections []string
	for rows.Next() {
		var section string
		if err := rows.Scan(&section); err != nil {
			return nil, fmt.Errorf("failed to scan section: %w", err)
		}
		sections = append(sections, section)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating sections: %w", err)
	}
	return sections, nil
}
