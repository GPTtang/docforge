from pathlib import Path

from openpyxl import Workbook

from converters.spreadsheet_converter import SpreadsheetConverter


def _save_workbook(path: Path, rows: list[list[object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


def test_formula_without_cached_value_falls_back_to_formula_text(tmp_path: Path) -> None:
    path = tmp_path / "formula.xlsx"
    _save_workbook(path, [["=1+2", "label"]])

    converter = SpreadsheetConverter()
    payload = converter.to_json(str(path))
    first_cell = payload["sheets"][0]["rows"][0][0]

    assert first_cell["value"] == "=1+2"
    assert first_cell["formula"] == "=1+2"
    assert "| `=1+2` | label |" in converter.to_markdown(str(path))


def test_markdown_uses_first_row_as_header(tmp_path: Path) -> None:
    path = tmp_path / "table.xlsx"
    _save_workbook(path, [["Name", "Age"], ["Alice", 30]])

    markdown_lines = SpreadsheetConverter().to_markdown(str(path)).strip().splitlines()

    assert markdown_lines[1] == "| Name | Age |"
    assert markdown_lines[3] == "| Alice | 30 |"
