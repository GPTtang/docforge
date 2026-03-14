# Test Documents

This folder stores reusable fixtures for DocForge conversion regression tests.

## Directory Layout

```
test-documents/
├── pdf/
│   ├── text/
│   └── scanned/
├── word/
│   ├── doc/
│   └── docx/
├── excel/
│   ├── xls/
│   └── xlsx/
├── powerpoint/
│   ├── ppt/
│   └── pptx/
├── manifest.csv
├── sources.csv
├── run-smoke-tests.ps1
└── reports/
```

## Coverage

- PDF (text-based)
- PDF (scanned / OCR-like)
- Word (`.doc`, `.docx`)
- Excel (`.xls`, `.xlsx`)
- PowerPoint (`.ppt`, `.pptx`)

## Source and License

- `sources.csv` records original URLs and source repositories.
- Files were downloaded from:
  - `docling-project/docling` test fixtures (MIT)
  - `apache/poi` test fixtures (Apache-2.0)

## Expected Results

- `manifest.csv` defines expected outcomes per endpoint (`success` / `fail`).
- The smoke test script compares actual results against `manifest.csv`.
- A case is marked `PASS` when actual behavior matches expected behavior.

## Run Smoke Test

```powershell
# Services should already be running
# docker compose up -d
.\test-documents\run-smoke-tests.ps1
```