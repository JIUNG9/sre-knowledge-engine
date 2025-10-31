package store

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/ClickHouse/clickhouse-go/v2"
	"github.com/ClickHouse/clickhouse-go/v2/lib/driver"

	"github.com/junegu/aegis/api/models"
)

// CreateTableQuery is the DDL for the logs table in ClickHouse.
const CreateTableQuery = `
CREATE TABLE IF NOT EXISTS logs (
    timestamp DateTime64(9),
    level Enum8('trace'=0, 'debug'=1, 'info'=2, 'warn'=3, 'error'=4, 'fatal'=5),
    message String,
    service String,
    trace_id String DEFAULT '',
    span_id String DEFAULT '',
    attributes Map(String, String),
    INDEX idx_message message TYPE tokenbf_v1(10240, 3, 0) GRANULARITY 4,
    INDEX idx_service service TYPE set(100) GRANULARITY 4
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (service, level, timestamp)
TTL timestamp + INTERVAL 30 DAY;
`

// ClickHouseStore implements the Store interface backed by ClickHouse.
type ClickHouseStore struct {
	conn driver.Conn
}

// NewClickHouseStore creates a new ClickHouseStore connected to the given DSN.
// DSN format: clickhouse://user:password@host:port/database
func NewClickHouseStore(dsn string) (*ClickHouseStore, error) {
	opts, err := clickhouse.ParseDSN(dsn)
	if err != nil {
		return nil, fmt.Errorf("failed to parse ClickHouse DSN: %w", err)
	}

	conn, err := clickhouse.Open(opts)
	if err != nil {
		return nil, fmt.Errorf("failed to open ClickHouse connection: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := conn.Ping(ctx); err != nil {
		return nil, fmt.Errorf("failed to ping ClickHouse: %w", err)
	}

	// Ensure the logs table exists.
	if err := conn.Exec(ctx, CreateTableQuery); err != nil {
		return nil, fmt.Errorf("failed to create logs table: %w", err)
	}

	return &ClickHouseStore{conn: conn}, nil
}

// QueryLogs retrieves log entries matching the given query parameters.
func (s *ClickHouseStore) QueryLogs(ctx context.Context, query models.LogQuery) ([]models.LogEntry, int64, error) {
	var conditions []string
	var args []interface{}

	if !query.StartTime.IsZero() {
		conditions = append(conditions, "timestamp >= ?")
		args = append(args, query.StartTime)
	}
	if !query.EndTime.IsZero() {
		conditions = append(conditions, "timestamp <= ?")
		args = append(args, query.EndTime)
	}
	if query.Query != "" {
		conditions = append(conditions, "message ILIKE ?")
		args = append(args, "%"+query.Query+"%")
	}
	if len(query.Levels) > 0 {
		placeholders := make([]string, len(query.Levels))
		for i, lvl := range query.Levels {
			placeholders[i] = "?"
			args = append(args, lvl)
		}
		conditions = append(conditions, fmt.Sprintf("level IN (%s)", strings.Join(placeholders, ",")))
	}
	if len(query.Services) > 0 {
		placeholders := make([]string, len(query.Services))
		for i, svc := range query.Services {
			placeholders[i] = "?"
			args = append(args, svc)
		}
		conditions = append(conditions, fmt.Sprintf("service IN (%s)", strings.Join(placeholders, ",")))
	}

	where := ""
	if len(conditions) > 0 {
		where = "WHERE " + strings.Join(conditions, " AND ")
	}

	// Get total count.
	countQuery := fmt.Sprintf("SELECT count() FROM logs %s", where)
	var total int64
	row := s.conn.QueryRow(ctx, countQuery, args...)
	if err := row.Scan(&total); err != nil {
		return nil, 0, fmt.Errorf("failed to count logs: %w", err)
	}

	// Clamp limit.
	limit := query.Limit
	if limit <= 0 || limit > 1000 {
		limit = 100
	}
	offset := query.Offset
	if offset < 0 {
		offset = 0
	}

	dataQuery := fmt.Sprintf(
		"SELECT timestamp, level, message, service, trace_id, span_id, attributes FROM logs %s ORDER BY timestamp DESC LIMIT %d OFFSET %d",
		where, limit, offset,
	)

	rows, err := s.conn.Query(ctx, dataQuery, args...)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to query logs: %w", err)
	}
	defer rows.Close()

	var entries []models.LogEntry
	for rows.Next() {
		var e models.LogEntry
		if err := rows.Scan(&e.Timestamp, &e.Level, &e.Message, &e.Service, &e.TraceID, &e.SpanID, &e.Attributes); err != nil {
			return nil, 0, fmt.Errorf("failed to scan log row: %w", err)
		}
		entries = append(entries, e)
	}
	if err := rows.Err(); err != nil {
		return nil, 0, fmt.Errorf("error iterating log rows: %w", err)
	}

	return entries, total, nil
}

// InsertLogs inserts a batch of log entries into ClickHouse.
func (s *ClickHouseStore) InsertLogs(ctx context.Context, entries []models.LogEntry) error {
	batch, err := s.conn.PrepareBatch(ctx, "INSERT INTO logs (timestamp, level, message, service, trace_id, span_id, attributes)")
	if err != nil {
		return fmt.Errorf("failed to prepare batch: %w", err)
	}

	for _, e := range entries {
		attrs := e.Attributes
		if attrs == nil {
			attrs = map[string]string{}
		}
		if err := batch.Append(e.Timestamp, e.Level, e.Message, e.Service, e.TraceID, e.SpanID, attrs); err != nil {
			return fmt.Errorf("failed to append to batch: %w", err)
		}
	}

	if err := batch.Send(); err != nil {
		return fmt.Errorf("failed to send batch: %w", err)
	}

	return nil
}

// GetLogStats returns aggregate log statistics for the given time range.
func (s *ClickHouseStore) GetLogStats(ctx context.Context, timeRange string) (*models.LogStats, error) {
	duration, err := parseTimeRange(timeRange)
	if err != nil {
		return nil, err
	}

	since := time.Now().Add(-duration)

	query := `
		SELECT
			count() AS total,
			countIf(level = 'error') + countIf(level = 'fatal') AS errors,
			countIf(level = 'warn') AS warnings
		FROM logs
		WHERE timestamp >= ?
	`

	var stats models.LogStats
	row := s.conn.QueryRow(ctx, query, since)
	if err := row.Scan(&stats.Total, &stats.Errors, &stats.Warnings); err != nil {
		return nil, fmt.Errorf("failed to query log stats: %w", err)
	}

	stats.TimeRange = timeRange
	if duration.Seconds() > 0 {
		stats.Rate = float64(stats.Total) / duration.Seconds()
	}

	return &stats, nil
}

// GetServices returns a list of distinct service names from the logs table.
func (s *ClickHouseStore) GetServices(ctx context.Context) ([]string, error) {
	rows, err := s.conn.Query(ctx, "SELECT DISTINCT service FROM logs ORDER BY service")
	if err != nil {
		return nil, fmt.Errorf("failed to query services: %w", err)
	}
	defer rows.Close()

	var services []string
	for rows.Next() {
		var svc string
		if err := rows.Scan(&svc); err != nil {
			return nil, fmt.Errorf("failed to scan service: %w", err)
		}
		services = append(services, svc)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating services: %w", err)
	}

	return services, nil
}

// parseTimeRange converts a time range string like "1h", "6h", "24h", "7d" to a duration.
func parseTimeRange(tr string) (time.Duration, error) {
	if tr == "" {
		return 24 * time.Hour, nil // default to 24h
	}

	switch tr {
	case "1h":
		return 1 * time.Hour, nil
	case "6h":
		return 6 * time.Hour, nil
	case "12h":
		return 12 * time.Hour, nil
	case "24h":
		return 24 * time.Hour, nil
	case "7d":
		return 7 * 24 * time.Hour, nil
	case "30d":
		return 30 * 24 * time.Hour, nil
	default:
		return 0, fmt.Errorf("unsupported time range: %s (use 1h, 6h, 12h, 24h, 7d, 30d)", tr)
	}
}
