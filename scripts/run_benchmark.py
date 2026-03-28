#!/usr/bin/env python3
"""Run a local conversion benchmark across multiple sample documents.

Usage:
    python scripts/run_benchmark.py \
        --samples test-documents/word/sample.docx test-documents/powerpoint/sample.pptx \
        test-documents/excel/sample.xlsx test-documents/pdf/sample.pdf

The script loads the FastAPI app in-process via TestClient so it does not
require the Docker services to be running. Results are written to a JSON
report that captures status, latency, and lightweight previews.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SERVICE = REPO_ROOT / "python-service"
if str(PYTHON_SERVICE) not in sys.path:
    sys.path.insert(0, str(PYTHON_SERVICE))

from main import app  # noqa: E402


def _summarize_markdown(text: str, preview: int) -> dict[str, Any]:
    return {
        "length": len(text),
        "lines": text.count("\n") + (1 if text else 0),
        "preview": text[:preview],
    }


def _summarize_json(data: Any, preview: int) -> dict[str, Any]:
    summary: dict[str, Any] = {"type": type(data).__name__}
    if isinstance(data, dict):
        summary["key_count"] = len(data)
        summary["keys"] = list(data.keys())[:10]
        sheets = data.get("sheets")
        if isinstance(sheets, list):
            summary["sheet_count"] = len(sheets)
    try:
        serialized = json.dumps(data, ensure_ascii=False)
    except Exception:
        serialized = str(data)
    summary["preview"] = serialized[:preview]
    return summary


def _run_single(client: TestClient, file_path: Path, target: str, preview: int) -> dict[str, Any]:
    payload = {"status": "error"}
    start = time.perf_counter()
    with file_path.open("rb") as fh:
        response = client.post(
            f"/convert/{target}",
            files={"file": (file_path.name, fh, "application/octet-stream")},
        )
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    result: dict[str, Any] = {
        "status_code": response.status_code,
        "duration_ms": duration_ms,
    }

    try:
        payload = response.json()
    except Exception:
        payload = {"status": "error", "message": response.text}

    result["status"] = payload.get("status")

    if response.status_code == 200 and payload.get("status") == "success":
        if target == "markdown":
            text = payload.get("markdown", "")
            result.update(_summarize_markdown(text, preview))
        else:
            data = payload.get("data")
            result.update(_summarize_json(data, preview))
    else:
        result["error"] = payload

    return result


def run_benchmark(samples: list[Path], targets: list[str], output: Path, preview: int) -> dict[str, Any]:
    client = TestClient(app)
    entries: list[dict[str, Any]] = []

    for file_path in samples:
        entry: dict[str, Any] = {
            "file": str(file_path),
            "extension": file_path.suffix.lower(),
            "results": {},
        }
        for target in targets:
            entry["results"][target] = _run_single(client, file_path, target, preview)
        entries.append(entry)

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "targets": targets,
        "entries": entries,
    }

    output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark the DocForge Python service")
    parser.add_argument(
        "--samples",
        nargs="+",
        required=True,
        help="Paths to input documents (DOCX, PPTX, XLSX, PDF, etc.)",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        default=["markdown", "json"],
        choices=["markdown", "json"],
        help="Conversion targets to test",
    )
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "benchmark-results.json"),
        help="Where to write the JSON benchmark report",
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=400,
        help="Maximum number of characters to keep in each preview field",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sample_paths = [Path(p).expanduser().resolve() for p in args.samples]

    missing = [str(p) for p in sample_paths if not p.exists()]
    if missing:
        sys.exit(f"Missing sample files: {', '.join(missing)}")

    report = run_benchmark(sample_paths, args.targets, Path(args.output), args.preview)

    print(f"Benchmark completed for {len(report['entries'])} files.")
    print(f"Report written to {args.output}")


if __name__ == "__main__":
    main()
