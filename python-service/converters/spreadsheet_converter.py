from typing import Any

from openpyxl import load_workbook


class SpreadsheetConverter:
    def to_json(self, path: str) -> dict[str, Any]:
        workbook = load_workbook(path, data_only=True, read_only=True)
        sheets: list[dict[str, Any]] = []

        try:
            for sheet in workbook.worksheets:
                rows = self._extract_rows(sheet)
                sheets.append({
                    "name": sheet.title,
                    "rows": rows,
                })
        finally:
            workbook.close()

        return {"sheets": sheets}

    def to_markdown(self, path: str) -> str:
        payload = self.to_json(path)
        parts: list[str] = []

        for sheet in payload["sheets"]:
            name = sheet["name"]
            rows = sheet["rows"]
            parts.append(f"## Sheet: {name}")

            if not rows:
                parts.append("_(empty)_")
                parts.append("")
                continue

            table = self._rows_to_markdown_table(rows)
            parts.append(table)
            parts.append("")

        return "\n".join(parts).strip() + "\n"

    def _extract_rows(self, sheet) -> list[list[str]]:
        rows: list[list[str]] = []

        for row in sheet.iter_rows(values_only=True):
            normalized = [self._normalize_cell(v) for v in row]

            while normalized and normalized[-1] == "":
                normalized.pop()

            if normalized:
                rows.append(normalized)

        return rows

    def _rows_to_markdown_table(self, rows: list[list[str]]) -> str:
        width = max(len(r) for r in rows)
        padded = [self._pad_row(r, width) for r in rows]

        header = padded[0]
        if all(not h for h in header):
            header = [f"Column {i + 1}" for i in range(width)]
            body = padded
        else:
            body = padded[1:] if len(padded) > 1 else []

        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * width) + " |",
        ]

        for row in body:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    def _pad_row(self, row: list[str], width: int) -> list[str]:
        padded = list(row)
        while len(padded) < width:
            padded.append("")
        return [self._escape_md(cell) for cell in padded]

    def _normalize_cell(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    def _escape_md(self, text: str) -> str:
        return text.replace("|", "\\|").replace("\n", " ").replace("\r", " ").strip()