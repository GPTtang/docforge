import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from converters.docling_converter import DoclingConverter
from converters.marker_converter import MarkerConverter
from converters.office_converter import OfficeConverter
from converters.spreadsheet_converter import SpreadsheetConverter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DocForge Python Service", version="1.0.0")

docling = DoclingConverter()
marker = MarkerConverter()
office = OfficeConverter()
spreadsheet = SpreadsheetConverter()

DECLARED_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"}
PDF_EXTENSION = ".pdf"
SPREADSHEET_EXTENSIONS = {".xlsx", ".xls"}
LEGACY_OFFICE_EXTENSIONS = {".doc", ".ppt", ".xls"}

DOCLING_EXTENSIONS = docling.supported_extensions & DECLARED_EXTENSIONS

MARKDOWN_EXTENSIONS = set(DOCLING_EXTENSIONS) | {".xlsx"}
JSON_EXTENSIONS = set(DOCLING_EXTENSIONS) | {".xlsx"}

if office.available:
    MARKDOWN_EXTENSIONS |= LEGACY_OFFICE_EXTENSIONS
    JSON_EXTENSIONS |= LEGACY_OFFICE_EXTENSIONS

MARKDOWN_EXTENSIONS = sorted(MARKDOWN_EXTENSIONS)
JSON_EXTENSIONS = sorted(JSON_EXTENSIONS)


OFFICE_CONVERSION_TARGETS = {
    ".doc": ".docx",
    ".ppt": ".pptx",
    ".xls": ".xlsx",
}


def _safe_error_message(exc: Exception, fallback: str) -> str:
    message = str(exc).strip()
    return message if message else fallback


def _extract_suffix(file: UploadFile, allowed_extensions: set[str]) -> str:
    filename = (file.filename or "").strip()
    suffix = Path(filename).suffix.lower()

    if not suffix:
        raise HTTPException(status_code=400, detail="File extension is required")

    if suffix not in allowed_extensions:
        supported = ", ".join(sorted(allowed_extensions))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {suffix}. Supported: {supported}",
        )

    return suffix


def _save_temp_file(file: UploadFile, suffix: str) -> str:
    file.file.seek(0)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp, length=1024 * 1024)
        return tmp.name


def _cleanup_temp_file(tmp_path: str | None) -> None:
    if not tmp_path:
        return
    try:
        Path(tmp_path).unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Failed to remove temp file %s: %s", tmp_path, exc)


def _cleanup_temp_dir(tmp_dir: str | None) -> None:
    if not tmp_dir:
        return
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception as exc:
        logger.warning("Failed to remove temp directory %s: %s", tmp_dir, exc)


def _convert_legacy_if_needed(source_path: str, suffix: str) -> tuple[str, str | None]:
    if suffix not in OFFICE_CONVERSION_TARGETS:
        return source_path, None

    if not office.available:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file format: {suffix}. "
                "Legacy Office conversion requires LibreOffice (soffice)."
            ),
        )

    out_dir = tempfile.mkdtemp(prefix="docforge-office-")
    target_ext = OFFICE_CONVERSION_TARGETS[suffix]

    try:
        converted_path = office.convert(source_path, target_ext, out_dir)
        return converted_path, out_dir
    except Exception as exc:
        _cleanup_temp_dir(out_dir)
        raise HTTPException(status_code=500, detail=_safe_error_message(exc, "Legacy format conversion failed"))


def _to_markdown(convert_path: str, suffix: str) -> str:
    if suffix in SPREADSHEET_EXTENSIONS:
        return spreadsheet.to_markdown(convert_path)

    if suffix == PDF_EXTENSION:
        try:
            return marker.to_markdown(convert_path)
        except Exception as marker_err:
            logger.warning("Marker failed, fallback to Docling: %s", _safe_error_message(marker_err, "unknown error"))
            if not docling.supports_extension(PDF_EXTENSION):
                raise HTTPException(
                    status_code=502,
                    detail="PDF conversion failed in Marker and Docling PDF fallback is unavailable",
                )
            return docling.to_markdown(convert_path)

    return docling.to_markdown(convert_path)


def _to_json(convert_path: str, suffix: str) -> dict:
    if suffix in SPREADSHEET_EXTENSIONS:
        return spreadsheet.to_json(convert_path)

    return docling.to_json(convert_path)


@app.post("/convert/markdown")
def convert_to_markdown(file: UploadFile = File(...)):
    tmp_path = None
    legacy_tmp_dir = None

    try:
        suffix = _extract_suffix(file, set(MARKDOWN_EXTENSIONS))
        tmp_path = _save_temp_file(file, suffix)

        convert_path = tmp_path
        effective_suffix = suffix

        if suffix in OFFICE_CONVERSION_TARGETS:
            convert_path, legacy_tmp_dir = _convert_legacy_if_needed(tmp_path, suffix)
            effective_suffix = Path(convert_path).suffix.lower()

        markdown = _to_markdown(convert_path, effective_suffix)

        return {"filename": file.filename, "markdown": markdown, "status": "success"}
    except HTTPException:
        raise
    except Exception as exc:
        message = _safe_error_message(exc, "Conversion failed")
        logger.exception("Markdown conversion failed: %s", message)
        raise HTTPException(status_code=500, detail=message)
    finally:
        _cleanup_temp_file(tmp_path)
        _cleanup_temp_dir(legacy_tmp_dir)


@app.post("/convert/json")
def convert_to_json(file: UploadFile = File(...)):
    tmp_path = None
    legacy_tmp_dir = None

    try:
        suffix = _extract_suffix(file, set(JSON_EXTENSIONS))
        tmp_path = _save_temp_file(file, suffix)

        convert_path = tmp_path
        effective_suffix = suffix

        if suffix in OFFICE_CONVERSION_TARGETS:
            convert_path, legacy_tmp_dir = _convert_legacy_if_needed(tmp_path, suffix)
            effective_suffix = Path(convert_path).suffix.lower()

        data = _to_json(convert_path, effective_suffix)
        return {"filename": file.filename, "data": data, "status": "success"}
    except HTTPException:
        raise
    except Exception as exc:
        message = _safe_error_message(exc, "Conversion failed")
        logger.exception("JSON conversion failed: %s", message)
        raise HTTPException(status_code=500, detail=message)
    finally:
        _cleanup_temp_file(tmp_path)
        _cleanup_temp_dir(legacy_tmp_dir)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "docforge-python",
        "office_converter_available": office.available,
    }


@app.get("/formats")
def supported_formats():
    return {
        "formats": MARKDOWN_EXTENSIONS,
        "markdown_formats": MARKDOWN_EXTENSIONS,
        "json_formats": JSON_EXTENSIONS,
        "office_converter_available": office.available,
    }