// Package excel provides small helpers for building CSV and XLSX exports
// consistently across the Aegis API handlers.
//
// Design goals:
//   - CSV is RFC 4180-compliant (stdlib encoding/csv handles quoting of
//     commas, newlines, and embedded double-quotes).
//   - XLSX workbooks have a bold header row, frozen header, and auto-width
//     columns for a reasonable default look when handed to a CFO.
//   - Callers stream the resulting bytes straight onto a Fiber response.
//
// The package is intentionally thin — it wraps github.com/xuri/excelize/v2
// and encoding/csv without inventing new abstractions.
package excel

import (
	"bytes"
	"encoding/csv"
	"fmt"
	"io"

	"github.com/xuri/excelize/v2"
)

// MIME types for the two formats Aegis supports.
const (
	MimeCSV  = "text/csv; charset=utf-8"
	MimeXLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

// Row is a single row of cell values. Values may be any of string, int,
// int64, float64, or bool — excelize and csv both accept these via fmt.
type Row []any

// WriteCSV writes header + rows to w in RFC 4180 form. All values are
// rendered with fmt.Sprint so numeric cells stay unquoted and are still
// machine-parseable in downstream tools.
func WriteCSV(w io.Writer, header []string, rows []Row) error {
	cw := csv.NewWriter(w)
	if err := cw.Write(header); err != nil {
		return fmt.Errorf("csv header: %w", err)
	}
	strRow := make([]string, len(header))
	for _, r := range rows {
		// Pad / truncate to header length so every row is the same width.
		for i := range strRow {
			if i < len(r) {
				strRow[i] = fmt.Sprint(r[i])
			} else {
				strRow[i] = ""
			}
		}
		if err := cw.Write(strRow); err != nil {
			return fmt.Errorf("csv row: %w", err)
		}
	}
	cw.Flush()
	return cw.Error()
}

// WriteXLSX builds a single-sheet workbook and returns its bytes. The
// workbook has:
//   - A bold header row.
//   - The first row frozen so it stays visible while scrolling.
//   - Column widths sized roughly to the widest value in each column.
func WriteXLSX(sheet string, header []string, rows []Row) ([]byte, error) {
	if sheet == "" {
		sheet = "Sheet1"
	}

	f := excelize.NewFile()
	defer func() { _ = f.Close() }()

	// Rename the default sheet rather than adding a new one and deleting
	// "Sheet1" — simpler and avoids index races.
	defaultName := f.GetSheetName(0)
	if defaultName != sheet {
		if err := f.SetSheetName(defaultName, sheet); err != nil {
			return nil, fmt.Errorf("rename sheet: %w", err)
		}
	}

	// Header row.
	headerStyle, err := f.NewStyle(&excelize.Style{
		Font: &excelize.Font{Bold: true, Color: "FFFFFF"},
		Fill: excelize.Fill{
			Type:    "pattern",
			Color:   []string{"111827"},
			Pattern: 1,
		},
		Alignment: &excelize.Alignment{Horizontal: "left", Vertical: "center"},
	})
	if err != nil {
		return nil, fmt.Errorf("header style: %w", err)
	}

	for i, h := range header {
		cell, err := excelize.CoordinatesToCellName(i+1, 1)
		if err != nil {
			return nil, fmt.Errorf("coord(%d,1): %w", i+1, err)
		}
		if err := f.SetCellValue(sheet, cell, h); err != nil {
			return nil, fmt.Errorf("set header cell %s: %w", cell, err)
		}
	}
	lastCol, _ := excelize.CoordinatesToCellName(maxInt(len(header), 1), 1)
	firstCol, _ := excelize.CoordinatesToCellName(1, 1)
	if err := f.SetCellStyle(sheet, firstCol, lastCol, headerStyle); err != nil {
		return nil, fmt.Errorf("apply header style: %w", err)
	}

	// Freeze first row.
	if err := f.SetPanes(sheet, &excelize.Panes{
		Freeze:      true,
		Split:       false,
		XSplit:      0,
		YSplit:      1,
		TopLeftCell: "A2",
		ActivePane:  "bottomLeft",
	}); err != nil {
		return nil, fmt.Errorf("freeze pane: %w", err)
	}

	// Data rows + track column widths (in characters, clamped).
	widths := make([]int, len(header))
	for i, h := range header {
		widths[i] = len(h)
	}
	for rIdx, r := range rows {
		row := rIdx + 2 // row 1 is header
		for cIdx := range header {
			cell, err := excelize.CoordinatesToCellName(cIdx+1, row)
			if err != nil {
				return nil, fmt.Errorf("coord(%d,%d): %w", cIdx+1, row, err)
			}
			var val any
			if cIdx < len(r) {
				val = r[cIdx]
			} else {
				val = ""
			}
			if err := f.SetCellValue(sheet, cell, val); err != nil {
				return nil, fmt.Errorf("set cell %s: %w", cell, err)
			}
			s := fmt.Sprint(val)
			if len(s) > widths[cIdx] {
				widths[cIdx] = len(s)
			}
		}
	}

	// Apply column widths. Clamp so one huge value doesn't blow up the
	// layout (min 8, max 48 chars).
	for i, w := range widths {
		col, err := excelize.ColumnNumberToName(i + 1)
		if err != nil {
			return nil, fmt.Errorf("col name %d: %w", i+1, err)
		}
		width := float64(w) + 2
		if width < 10 {
			width = 10
		}
		if width > 50 {
			width = 50
		}
		if err := f.SetColWidth(sheet, col, col, width); err != nil {
			return nil, fmt.Errorf("set col width %s: %w", col, err)
		}
	}

	var buf bytes.Buffer
	if err := f.Write(&buf); err != nil {
		return nil, fmt.Errorf("write xlsx: %w", err)
	}
	return buf.Bytes(), nil
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}
