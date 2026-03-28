import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, File, HTTPException, UploadFile

from converters.docx_converter import DocxConverter
from converters.office_converter import OfficeConverter
from converters.opendataloader_converter import OpenDataLoaderConverter
from converters.pptx_converter import PptxConverter
from converters.spreadsheet_converter import SpreadsheetConverter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DocForge Python Service", version="1.0.0")

docx = DocxConverter()
pdf_converter = OpenDataLoaderConverter()
pptx = PptxConverter()
office = OfficeConverter()
spreadsheet = SpreadsheetConverter()

PDF_EXTENSION = ".pdf"
DOCX_EXTENSION = ".docx"
PPTX_EXTENSION = ".pptx"
SPREADSHEET_EXTENSIONS = {".xlsx"}
LEGACY_OFFICE_EXTENSIONS = {".doc", ".ppt", ".xls"}

OFFICE_CONVERSION_TARGETS = {
    ".doc": ".docx",
    ".ppt": ".pptx",
    ".xls": ".xlsx",
}

# Placeholder hook: OCR/cleanup preprocessors for PDFs can be appended here later.
PDF_PREPROCESSORS: list[Callable[[str, str], str]] = []


@dataclass
class EngineStep:
    name: str
    func: Callable[[str, str], Any]


@dataclass
class PipelineRoute:
    extensions: set[str]
    engines: list[EngineStep]
    preprocessors: list[Callable[[str, str], str]] = field(default_factory=list)


class PipelineRegistry:
    def __init__(
        self,
        *,
        docx_converter: DocxConverter,
        pdf_converter: OpenDataLoaderConverter,
        pptx_converter: PptxConverter,
        spreadsheet_converter: SpreadsheetConverter,
        legacy_enabled: bool,
    ):
        self._docx = docx_converter
        self._pdf = pdf_converter
        self._pptx = pptx_converter
        self._spreadsheet = spreadsheet_converter
        self._pipelines: dict[str, list[PipelineRoute]] = {}
        self._allowed_sets: dict[str, frozenset[str]] = {}
        self._allowed_lists: dict[str, list[str]] = {}
        self._legacy_enabled = legacy_enabled
        self._initialized = False

    def allowed_extensions_set(self, target: str) -> frozenset[str]:
        self._ensure_initialized()
        return self._allowed_sets[target]

    def allowed_extensions_list(self, target: str) -> list[str]:
        self._ensure_initialized()
        return self._allowed_lists[target]

    def convert(self, target: str, suffix: str, path: str):
        self._ensure_initialized()
        route = self._match_route(target, suffix)
        if route is None:
            supported = ", ".join(self._allowed_lists[target])
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {suffix}. Supported: {supported}",
            )

        processed_path = self._apply_preprocessors(route, path, suffix)
        last_error: Exception | None = None

        for engine in route.engines:
            try:
                return engine.func(processed_path, suffix)
            except HTTPException:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Engine %s failed for %s → %s: %s",
                    engine.name,
                    suffix,
                    target,
                    _safe_error_message(exc, "unknown error"),
                )

        if last_error is not None:
            raise HTTPException(
                status_code=502,
                detail=_safe_error_message(last_error, "Conversion pipeline failed"),
            )

        raise HTTPException(status_code=500, detail="No conversion engines configured")

    def _apply_preprocessors(self, route: PipelineRoute, path: str, suffix: str) -> str:
        processed = path
        for preprocess in route.preprocessors:
            processed = preprocess(processed, suffix)
        return processed

    def _match_route(self, target: str, suffix: str) -> PipelineRoute | None:
        for route in self._pipelines.get(target, []):
            if suffix in route.extensions:
                return route
        return None

    def _ensure_initialized(self):
        if self._initialized:
            return
        self._build()

    def _build(self):
        markdown_routes = self._build_markdown_routes()
        json_routes = self._build_json_routes()

        self._pipelines = {
            "markdown": markdown_routes,
            "json": json_routes,
        }

        markdown_allowed = self._collect_extensions(markdown_routes)
        json_allowed = self._collect_extensions(json_routes)

        if self._legacy_enabled:
            markdown_allowed |= LEGACY_OFFICE_EXTENSIONS
            json_allowed |= LEGACY_OFFICE_EXTENSIONS

        self._allowed_sets = {
            "markdown": frozenset(markdown_allowed),
            "json": frozenset(json_allowed),
        }
        self._allowed_lists = {
            key: sorted(value) for key, value in self._allowed_sets.items()
        }
        self._initialized = True

    def _collect_extensions(self, routes: list[PipelineRoute]) -> set[str]:
        collected: set[str] = set()
        for route in routes:
            collected.update(route.extensions)
        return collected

    def _build_markdown_routes(self) -> list[PipelineRoute]:
        routes: list[PipelineRoute] = []

        routes.append(
            PipelineRoute(
                extensions=set(SPREADSHEET_EXTENSIONS),
                engines=[
                    EngineStep(
                        "spreadsheet",
                        lambda path, _: self._spreadsheet.to_markdown(path),
                    )
                ],
            )
        )

        routes.append(
            PipelineRoute(
                extensions={PDF_EXTENSION},
                engines=[
                    EngineStep(
                        "opendataloader",
                        lambda path, _: self._pdf.to_markdown(path),
                    )
                ],
                preprocessors=list(PDF_PREPROCESSORS),
            )
        )

        routes.append(
            PipelineRoute(
                extensions={DOCX_EXTENSION},
                engines=[
                    EngineStep(
                        "docx",
                        lambda path, _: self._docx.to_markdown(path),
                    )
                ],
            )
        )

        routes.append(
            PipelineRoute(
                extensions={PPTX_EXTENSION},
                engines=[
                    EngineStep(
                        "pptx",
                        lambda path, _: self._pptx.to_markdown(path),
                    )
                ],
            )
        )

        return routes

    def _build_json_routes(self) -> list[PipelineRoute]:
        routes: list[PipelineRoute] = []

        routes.append(
            PipelineRoute(
                extensions=set(SPREADSHEET_EXTENSIONS),
                engines=[
                    EngineStep(
                        "spreadsheet",
                        lambda path, _: self._spreadsheet.to_json(path),
                    )
                ],
            )
        )

        routes.append(
            PipelineRoute(
                extensions={PDF_EXTENSION},
                engines=[
                    EngineStep(
                        "opendataloader",
                        lambda path, _: self._pdf.to_json(path),
                    )
                ],
                preprocessors=list(PDF_PREPROCESSORS),
            )
        )

        routes.append(
            PipelineRoute(
                extensions={DOCX_EXTENSION},
                engines=[
                    EngineStep(
                        "docx",
                        lambda path, _: self._docx.to_json(path),
                    )
                ],
            )
        )

        routes.append(
            PipelineRoute(
                extensions={PPTX_EXTENSION},
                engines=[
                    EngineStep(
                        "pptx",
                        lambda path, _: self._pptx.to_json(path),
                    )
                ],
            )
        )

        return routes


pipeline_registry = PipelineRegistry(
    docx_converter=docx,
    pdf_converter=pdf_converter,
    pptx_converter=pptx,
    spreadsheet_converter=spreadsheet,
    legacy_enabled=office.available,
)


def _safe_error_message(exc: Exception, fallback: str) -> str:
    message = str(exc).strip()
    return message if message else fallback


def _extract_suffix(file: UploadFile, allowed_extensions: frozenset[str]) -> str:
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


_MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB


def _save_temp_file(file: UploadFile, suffix: str) -> str:
    file.file.seek(0)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        buf_size = 1024 * 1024
        total = 0
        while True:
            chunk = file.file.read(buf_size)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_UPLOAD_BYTES:
                tmp.close()
                Path(tmp.name).unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum allowed size is {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
                )
            tmp.write(chunk)
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


def _handle_conversion(file: UploadFile, target: str):
    allowed = pipeline_registry.allowed_extensions_set(target)
    suffix = _extract_suffix(file, allowed)

    tmp_path = None
    legacy_tmp_dir = None

    try:
        tmp_path = _save_temp_file(file, suffix)
        convert_path = tmp_path
        effective_suffix = suffix

        if suffix in OFFICE_CONVERSION_TARGETS:
            convert_path, legacy_tmp_dir = _convert_legacy_if_needed(tmp_path, suffix)
            effective_suffix = Path(convert_path).suffix.lower()

        result = pipeline_registry.convert(target, effective_suffix, convert_path)
        return result
    finally:
        _cleanup_temp_file(tmp_path)
        _cleanup_temp_dir(legacy_tmp_dir)


@app.post("/convert/markdown")
def convert_to_markdown(file: UploadFile = File(...)):
    try:
        markdown = _handle_conversion(file, "markdown")
        return {"filename": file.filename, "markdown": markdown, "status": "success"}
    except HTTPException:
        raise
    except Exception as exc:
        message = _safe_error_message(exc, "Conversion failed")
        logger.exception("Markdown conversion failed: %s", message)
        raise HTTPException(status_code=500, detail=message)


@app.post("/convert/json")
def convert_to_json(file: UploadFile = File(...)):
    try:
        data = _handle_conversion(file, "json")
        return {"filename": file.filename, "data": data, "status": "success"}
    except HTTPException:
        raise
    except Exception as exc:
        message = _safe_error_message(exc, "Conversion failed")
        logger.exception("JSON conversion failed: %s", message)
        raise HTTPException(status_code=500, detail=message)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "docforge-python",
        "pdf_engine": "opendataloader-pdf",
        "pdf_hybrid_backend": pdf_converter.hybrid or "off",
        "office_converter_available": office.available,
    }


@app.get("/formats")
def supported_formats():
    markdown_formats = pipeline_registry.allowed_extensions_list("markdown")
    json_formats = pipeline_registry.allowed_extensions_list("json")
    return {
        "formats": markdown_formats,
        "markdown_formats": markdown_formats,
        "json_formats": json_formats,
        "office_converter_available": office.available,
    }
