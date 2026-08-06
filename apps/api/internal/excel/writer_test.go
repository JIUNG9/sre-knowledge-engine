package excel

import (
	"bytes"
	"encoding/csv"
	"errors"
	"strings"
	"testing"

	"github.com/xuri/excelize/v2"
)

func writeCSVString(t *testing.T, header []string, rows []Row) string {
	t.Helper()
	var buf bytes.Buffer
	if err := WriteCSV(&buf, header, rows); err != nil {
		t.Fatalf("WriteCSV: %v", err)
	}
	return buf.String()
}

func TestWriteCSVRoundTripsThroughAParser(t *testing.T) {
	header := []string{"service", "monthly_usd", "flagged"}
	rows := []Row{
		{"checkout", 1234.56, true},
		{"search", 0, false},
	}

	got := writeCSVString(t, header, rows)
	records, err := csv.NewReader(strings.NewReader(got)).ReadAll()
	if err != nil {
		t.Fatalf("output is not parseable CSV: %v", err)
	}
	if len(records) != 3 {
		t.Fatalf("got %d records, want 3 (header + 2 rows)", len(records))
	}
	if records[0][0] != "service" || records[1][1] != "1234.56" || records[2][2] != "false" {
		t.Errorf("unexpected values: %v", records)
	}
}

// Values containing commas, quotes or newlines must survive as one cell rather
// than shifting every column after them. This is the whole reason to use
// encoding/csv instead of joining with commas.
func TestWriteCSVQuotesAwkwardValues(t *testing.T) {
	header := []string{"name", "note"}
	rows := []Row{
		{"a,b", `he said "hi"`},
		{"multi\nline", "trailing space "},
	}

	records, err := csv.NewReader(strings.NewReader(writeCSVString(t, header, rows))).ReadAll()
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	if records[1][0] != "a,b" {
		t.Errorf("comma value mangled: %q", records[1][0])
	}
	if records[1][1] != `he said "hi"` {
		t.Errorf("quoted value mangled: %q", records[1][1])
	}
	if records[2][0] != "multi\nline" {
		t.Errorf("newline value mangled: %q", records[2][0])
	}
}

// The doc comment promises every row is padded or truncated to the header width.
// A ragged export silently misaligns columns in whatever the CFO opens it with.
func TestWriteCSVNormalisesRowWidth(t *testing.T) {
	header := []string{"a", "b", "c"}
	rows := []Row{
		{"only-one"},
		{"one", "two", "three", "four-is-extra"},
	}

	records, err := csv.NewReader(strings.NewReader(writeCSVString(t, header, rows))).ReadAll()
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	for i, rec := range records {
		if len(rec) != len(header) {
			t.Errorf("record %d has width %d, want %d: %v", i, len(rec), len(header), rec)
		}
	}
	if records[1][1] != "" || records[1][2] != "" {
		t.Errorf("short row not padded with empties: %v", records[1])
	}
	if records[2][2] != "three" {
		t.Errorf("long row truncated at the wrong point: %v", records[2])
	}
}

func TestWriteCSVEmptyRows(t *testing.T) {
	got := writeCSVString(t, []string{"a", "b"}, nil)
	if got != "a,b\n" {
		t.Errorf("got %q, want just the header line", got)
	}
}

type failingWriter struct{}

func (failingWriter) Write([]byte) (int, error) { return 0, errors.New("disk full") }

// A failed export must surface as an error rather than a truncated file the
// recipient can't tell is incomplete.
func TestWriteCSVPropagatesWriteErrors(t *testing.T) {
	err := WriteCSV(failingWriter{}, []string{"a"}, []Row{{"x"}})
	if err == nil {
		t.Fatal("expected an error from a failing writer, got nil")
	}
	if !strings.Contains(err.Error(), "disk full") {
		t.Errorf("underlying error not wrapped: %v", err)
	}
}

func TestWriteXLSXProducesAReadableWorkbook(t *testing.T) {
	header := []string{"service", "monthly_usd"}
	rows := []Row{
		{"checkout", 1234.56},
		{"search", 42},
	}

	data, err := WriteXLSX("Costs", header, rows)
	if err != nil {
		t.Fatalf("WriteXLSX: %v", err)
	}
	if len(data) == 0 {
		t.Fatal("no bytes returned")
	}

	f, err := excelize.OpenReader(bytes.NewReader(data))
	if err != nil {
		t.Fatalf("output is not a readable xlsx: %v", err)
	}
	defer func() { _ = f.Close() }()

	cells, err := f.GetRows("Costs")
	if err != nil {
		t.Fatalf("GetRows: %v", err)
	}
	if len(cells) != 3 {
		t.Fatalf("got %d rows, want 3", len(cells))
	}
	if cells[0][0] != "service" {
		t.Errorf("header cell A1 = %q, want %q", cells[0][0], "service")
	}
	if cells[1][0] != "checkout" {
		t.Errorf("A2 = %q, want %q", cells[1][0], "checkout")
	}
}

func TestWriteXLSXDefaultsSheetName(t *testing.T) {
	data, err := WriteXLSX("", []string{"a"}, []Row{{"x"}})
	if err != nil {
		t.Fatalf("WriteXLSX: %v", err)
	}
	f, err := excelize.OpenReader(bytes.NewReader(data))
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	defer func() { _ = f.Close() }()

	if _, err := f.GetRows("Sheet1"); err != nil {
		t.Errorf("empty sheet name should default to Sheet1: %v", err)
	}
}

func TestWriteXLSXHeaderRowIsFrozen(t *testing.T) {
	data, err := WriteXLSX("Costs", []string{"a", "b"}, []Row{{1, 2}})
	if err != nil {
		t.Fatalf("WriteXLSX: %v", err)
	}
	f, err := excelize.OpenReader(bytes.NewReader(data))
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	defer func() { _ = f.Close() }()

	panes, err := f.GetPanes("Costs")
	if err != nil {
		t.Fatalf("GetPanes: %v", err)
	}
	if !panes.Freeze {
		t.Error("header row is not frozen; the doc comment says it should be")
	}
}

func TestMimeTypesAreTheRegisteredOnes(t *testing.T) {
	if MimeCSV != "text/csv; charset=utf-8" {
		t.Errorf("MimeCSV = %q", MimeCSV)
	}
	const wantXLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
	if MimeXLSX != wantXLSX {
		t.Errorf("MimeXLSX = %q, want the OOXML spreadsheet type", MimeXLSX)
	}
}
