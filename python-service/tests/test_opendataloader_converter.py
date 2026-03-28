import json
import sys
import types
from pathlib import Path

import pytest

from converters.opendataloader_converter import OpenDataLoaderConverter


def _install_fake_module(monkeypatch, convert_func) -> None:
    fake_module = types.ModuleType("opendataloader_pdf")
    fake_module.convert = convert_func
    monkeypatch.setitem(sys.modules, "opendataloader_pdf", fake_module)


def test_opendataloader_converter_uses_hybrid_env(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_convert(**kwargs):
        captured.update(kwargs)
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "example.md").write_text("# converted markdown", encoding="utf-8")

    _install_fake_module(monkeypatch, fake_convert)
    monkeypatch.setenv("DOCFORGE_OPENDATALOADER_HYBRID", "docling-fast")
    monkeypatch.setenv("DOCFORGE_OPENDATALOADER_HYBRID_URL", "http://hybrid:5002")
    monkeypatch.setenv("DOCFORGE_OPENDATALOADER_HYBRID_MODE", "full")
    monkeypatch.setenv("DOCFORGE_OPENDATALOADER_HYBRID_TIMEOUT", "30000")
    monkeypatch.setenv("DOCFORGE_OPENDATALOADER_HYBRID_FALLBACK", "true")

    converter = OpenDataLoaderConverter()

    result = converter.to_markdown("/tmp/example.pdf")

    assert result == "# converted markdown"
    assert captured == {
        "input_path": "/tmp/example.pdf",
        "output_dir": captured["output_dir"],
        "format": "markdown",
        "quiet": True,
        "image_output": "embedded",
        "hybrid": "docling-fast",
        "hybrid_mode": "full",
        "hybrid_url": "http://hybrid:5002",
        "hybrid_timeout": "30000",
        "hybrid_fallback": True,
    }


def test_opendataloader_converter_parses_json(monkeypatch) -> None:
    def fake_convert(**kwargs):
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "example.json").write_text(
            json.dumps({"engine": "opendataloader"}),
            encoding="utf-8",
        )

    _install_fake_module(monkeypatch, fake_convert)

    converter = OpenDataLoaderConverter()

    assert converter.to_json("/tmp/example.pdf") == {"engine": "opendataloader"}


def test_opendataloader_converter_ignores_hybrid_params_when_disabled(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_convert(**kwargs):
        captured.update(kwargs)
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "example.md").write_text("# converted markdown", encoding="utf-8")

    _install_fake_module(monkeypatch, fake_convert)
    monkeypatch.setenv("DOCFORGE_OPENDATALOADER_HYBRID", "off")
    monkeypatch.setenv("DOCFORGE_OPENDATALOADER_HYBRID_URL", "http://hybrid:5002")
    monkeypatch.setenv("DOCFORGE_OPENDATALOADER_HYBRID_MODE", "full")
    monkeypatch.setenv("DOCFORGE_OPENDATALOADER_HYBRID_TIMEOUT", "30000")
    monkeypatch.setenv("DOCFORGE_OPENDATALOADER_HYBRID_FALLBACK", "true")

    converter = OpenDataLoaderConverter()

    result = converter.to_markdown("/tmp/example.pdf")

    assert result == "# converted markdown"
    assert converter.hybrid is None
    assert converter.hybrid_url is None
    assert converter.hybrid_mode is None
    assert captured == {
        "input_path": "/tmp/example.pdf",
        "output_dir": captured["output_dir"],
        "format": "markdown",
        "quiet": True,
        "image_output": "embedded",
    }


def test_opendataloader_converter_surfaces_invalid_json(monkeypatch) -> None:
    def fake_convert(**kwargs):
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "example.json").write_text("not-json", encoding="utf-8")

    _install_fake_module(monkeypatch, fake_convert)

    converter = OpenDataLoaderConverter()

    with pytest.raises(RuntimeError, match="invalid JSON"):
        converter.to_json("/tmp/example.pdf")


def test_opendataloader_converter_requires_expected_output(monkeypatch) -> None:
    def fake_convert(**kwargs):
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

    _install_fake_module(monkeypatch, fake_convert)

    converter = OpenDataLoaderConverter()

    with pytest.raises(RuntimeError, match="did not produce \\.md output"):
        converter.to_markdown("/tmp/example.pdf")
