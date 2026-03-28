import importlib.util
import io
import sys
import types
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile


def _load_main_module(
    monkeypatch,
    *,
    pdf_markdown: str = "opendataloader-markdown",
    pdf_json: dict | None = None,
    pdf_error: Exception | None = None,
    office_available: bool = True,
):
    service_dir = Path(__file__).resolve().parents[1]
    module_path = service_dir / "main.py"
    module_name = "docforge_main_test"

    if str(service_dir) not in sys.path:
        monkeypatch.syspath_prepend(str(service_dir))

    import converters  # noqa: F401

    python_multipart_module = types.ModuleType("python_multipart")
    python_multipart_module.__version__ = "0.0.20"
    monkeypatch.setitem(sys.modules, "python_multipart", python_multipart_module)

    multipart_package = types.ModuleType("multipart")
    multipart_package.__version__ = "0.0.20"
    monkeypatch.setitem(sys.modules, "multipart", multipart_package)

    multipart_submodule = types.ModuleType("multipart.multipart")
    multipart_submodule.parse_options_header = lambda value: ("", {})
    monkeypatch.setitem(sys.modules, "multipart.multipart", multipart_submodule)

    docx_module = types.ModuleType("converters.docx_converter")

    class FakeDocxConverter:
        def to_markdown(self, path: str) -> str:
            return "docx-markdown"

        def to_json(self, path: str) -> dict:
            return {"engine": "docx"}

    docx_module.DocxConverter = FakeDocxConverter
    monkeypatch.setitem(sys.modules, "converters.docx_converter", docx_module)

    opendataloader_module = types.ModuleType("converters.opendataloader_converter")

    class FakeOpenDataLoaderConverter:
        hybrid = "docling-fast"
        hybrid_url = "http://opendataloader-hybrid:5002"

        def to_markdown(self, path: str) -> str:
            if pdf_error is not None:
                raise pdf_error
            return pdf_markdown

        def to_json(self, path: str) -> dict:
            if pdf_error is not None:
                raise pdf_error
            return pdf_json or {"engine": "opendataloader"}

    opendataloader_module.OpenDataLoaderConverter = FakeOpenDataLoaderConverter
    monkeypatch.setitem(
        sys.modules,
        "converters.opendataloader_converter",
        opendataloader_module,
    )

    pptx_module = types.ModuleType("converters.pptx_converter")

    class FakePptxConverter:
        def to_markdown(self, path: str) -> str:
            return "pptx-markdown"

        def to_json(self, path: str) -> dict:
            return {"engine": "pptx"}

    pptx_module.PptxConverter = FakePptxConverter
    monkeypatch.setitem(sys.modules, "converters.pptx_converter", pptx_module)

    office_module = types.ModuleType("converters.office_converter")

    class FakeOfficeConverter:
        @property
        def available(self) -> bool:
            return office_available

        def convert(self, source_path: str, target_extension: str, out_dir: str) -> str:
            raise AssertionError("convert should not be called in this test")

    office_module.OfficeConverter = FakeOfficeConverter
    monkeypatch.setitem(sys.modules, "converters.office_converter", office_module)

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def test_formats_endpoint_keeps_markdown_and_json_contract(monkeypatch) -> None:
    module = _load_main_module(monkeypatch)
    client = TestClient(module.app)

    response = client.get("/formats")

    assert response.status_code == 200
    body = response.json()
    assert body["formats"] == body["markdown_formats"]
    assert body["markdown_formats"] == [".doc", ".docx", ".pdf", ".ppt", ".pptx", ".xls", ".xlsx"]
    assert body["json_formats"] == [".doc", ".docx", ".pdf", ".ppt", ".pptx", ".xls", ".xlsx"]
    assert body["office_converter_available"] is True


def test_convert_markdown_uploads_pdf_successfully(monkeypatch) -> None:
    module = _load_main_module(monkeypatch, pdf_markdown="# parsed")

    response = module.convert_to_markdown(
        UploadFile(
            filename="sample.pdf",
            file=io.BytesIO(b"%PDF-1.4"),
        )
    )

    assert response == {
        "filename": "sample.pdf",
        "markdown": "# parsed",
        "status": "success",
    }


def test_convert_markdown_rejects_unsupported_extension(monkeypatch) -> None:
    module = _load_main_module(monkeypatch)

    with pytest.raises(HTTPException, match="Unsupported file format: .txt"):
        module.convert_to_markdown(
            UploadFile(
                filename="sample.txt",
                file=io.BytesIO(b"text"),
            )
        )


def test_convert_markdown_surfaces_engine_failure_as_502(monkeypatch) -> None:
    module = _load_main_module(monkeypatch, pdf_error=RuntimeError("pdf failed"))

    with pytest.raises(HTTPException) as exc_info:
        module.convert_to_markdown(
            UploadFile(
                filename="sample.pdf",
                file=io.BytesIO(b"%PDF-1.4"),
            )
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "pdf failed"


def test_health_endpoint_hides_internal_urls(monkeypatch) -> None:
    module = _load_main_module(monkeypatch)
    client = TestClient(module.app)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "ok",
        "service": "docforge-python",
        "pdf_engine": "opendataloader-pdf",
        "pdf_hybrid_backend": "docling-fast",
        "office_converter_available": True,
    }
    # Internal service URLs must not be exposed via the health endpoint.
    assert "hybrid_url" not in body


def test_convert_markdown_rejects_oversized_file(monkeypatch) -> None:
    module = _load_main_module(monkeypatch)

    oversized = io.BytesIO(b"x" * (101 * 1024 * 1024))

    with pytest.raises(HTTPException) as exc_info:
        module.convert_to_markdown(
            UploadFile(
                filename="big.pdf",
                file=oversized,
            )
        )

    assert exc_info.value.status_code == 413


def test_convert_legacy_doc_routes_through_office(monkeypatch) -> None:
    """A .doc upload should be converted via OfficeConverter then routed as .docx."""
    service_dir = Path(__file__).resolve().parents[1]
    if str(service_dir) not in sys.path:
        monkeypatch.syspath_prepend(str(service_dir))

    import tempfile as _tempfile
    import os

    # Patch _load_main_module but override the FakeOfficeConverter so convert() works.
    module = _load_main_module(monkeypatch, office_available=True)

    # Create a real temp docx so the pipeline can route to it.
    tmp_docx = _tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tmp_docx.write(b"fake-docx")
    tmp_docx.close()

    try:
        # Override the office converter's convert method to return our temp file.
        original_office = module.office

        class PatchedOffice:
            available = True

            def convert(self, source_path: str, target_extension: str, out_dir: str) -> str:
                return tmp_docx.name

        module.office = PatchedOffice()

        response = module.convert_to_markdown(
            UploadFile(
                filename="document.doc",
                file=io.BytesIO(b"old-doc-bytes"),
            )
        )

        assert response["status"] == "success"
        assert response["filename"] == "document.doc"
        assert response["markdown"] == "docx-markdown"
    finally:
        module.office = original_office
        os.unlink(tmp_docx.name)
