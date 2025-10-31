package store

import (
	"context"

	"github.com/junegu/aegis/api/models"
)

// Store defines the interface for log storage backends.
type Store interface {
	// QueryLogs retrieves log entries matching the given query parameters.
	// Returns the matching entries, total count, and any error.
	QueryLogs(ctx context.Context, query models.LogQuery) ([]models.LogEntry, int64, error)

	// InsertLogs inserts a batch of log entries into the store.
	InsertLogs(ctx context.Context, entries []models.LogEntry) error

	// GetLogStats returns aggregate log statistics for the given time range.
	// timeRange accepts values like "1h", "6h", "24h", "7d".
	GetLogStats(ctx context.Context, timeRange string) (*models.LogStats, error)

	// GetServices returns a list of distinct service names present in the logs.
	GetServices(ctx context.Context) ([]string, error)
}
