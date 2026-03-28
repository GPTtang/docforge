import importlib.util
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient


def _load_main_module(monkeypatch):
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

    docling_module = types.ModuleType("converters.docling_converter")

    class FakeDoclingConverter:
        @property
        def supported_extensions(self):
            return {".pdf", ".docx", ".pptx", ".xlsx"}

        def supports_extension(self, suffix: str) -> bool:
            return suffix in self.supported_extensions

        def to_markdown(self, path: str) -> str:
            return "docling-markdown"

        def to_json(self, path: str) -> dict:
            return {"engine": "docling"}

    docling_module.DoclingConverter = FakeDoclingConverter
    monkeypatch.setitem(sys.modules, "converters.docling_converter", docling_module)

    marker_module = types.ModuleType("converters.marker_converter")

    class FakeMarkerConverter:
        def to_markdown(self, path: str) -> str:
            return "marker-markdown"

    marker_module.MarkerConverter = FakeMarkerConverter
    monkeypatch.setitem(sys.modules, "converters.marker_converter", marker_module)

    office_module = types.ModuleType("converters.office_converter")

    class FakeOfficeConverter:
        @property
        def available(self) -> bool:
            return True

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
