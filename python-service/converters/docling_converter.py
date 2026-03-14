from typing import Set

from docling.document_converter import DocumentConverter


class DoclingConverter:
    def __init__(self):
        self.converter = DocumentConverter()
        self.supported_extensions = self._detect_supported_extensions()

    def _detect_supported_extensions(self) -> Set[str]:
        format_to_options = getattr(self.converter, "format_to_options", {}) or {}
        detected = set()

        for fmt in format_to_options.keys():
            value = getattr(fmt, "value", str(fmt))
            normalized = str(value).strip().lower()
            if not normalized:
                continue
            detected.add(normalized if normalized.startswith(".") else f".{normalized}")

        return detected

    def supports_extension(self, suffix: str) -> bool:
        return suffix.lower() in self.supported_extensions

    def to_markdown(self, path: str) -> str:
        result = self.converter.convert(path)
        return result.document.export_to_markdown()

    def to_json(self, path: str) -> dict:
        result = self.converter.convert(path)
        return result.document.export_to_dict()
