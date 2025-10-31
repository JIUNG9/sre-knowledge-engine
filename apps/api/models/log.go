package models

import "time"

// LogEntry represents a single log entry stored in ClickHouse.
type LogEntry struct {
	Timestamp  time.Time         `json:"timestamp"`
	Level      string            `json:"level"`
	Message    string            `json:"message"`
	Service    string            `json:"service"`
	TraceID    string            `json:"trace_id,omitempty"`
	SpanID     string            `json:"span_id,omitempty"`
	Attributes map[string]string `json:"attributes,omitempty"`
}

// LogQuery represents the parameters for querying logs.
type LogQuery struct {
	Query     string    `json:"query"`
	StartTime time.Time `json:"start_time"`
	EndTime   time.Time `json:"end_time"`
	Levels    []string  `json:"levels"`
	Services  []string  `json:"services"`
	Limit     int       `json:"limit"`
	Offset    int       `json:"offset"`
}

// LogStats represents aggregate log statistics.
type LogStats struct {
	Total     int64   `json:"total"`
	Errors    int64   `json:"errors"`
	Warnings  int64   `json:"warnings"`
	Rate      float64 `json:"rate"` // logs per second
	TimeRange string  `json:"time_range"`
}

// SavedQuery represents a saved log query with its filters.
type SavedQuery struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Query     string    `json:"query"`
	Filters   LogQuery  `json:"filters"`
	CreatedAt time.Time `json:"created_at"`
}

// SavedQueryRequest represents the request payload for saving a query.
type SavedQueryRequest struct {
	Name    string   `json:"name"`
	Query   string   `json:"query"`
	Filters LogQuery `json:"filters"`
}

// IngestLogsRequest represents a batch log ingestion payload.
type IngestLogsRequest struct {
	Logs []LogEntry `json:"logs"`
}

// IngestResponse represents the response after log ingestion.
type IngestResponse struct {
	Status   string `json:"status"`
	Accepted int    `json:"accepted"`
	Message  string `json:"message"`
}
