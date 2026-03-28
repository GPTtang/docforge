from __future__ import annotations

from functools import cached_property
import re
from typing import Any


class DocxConverter:
    def to_markdown(self, path: str) -> str:
        with open(path, "rb") as source:
            result = self._mammoth.convert_to_html(source)

        html = (result.value or "").strip()
        if not html:
            with open(path, "rb") as source:
                text = self._mammoth.extract_raw_text(source).value.strip()
            return f"{text}\n" if text else ""

        markdown = self._markdownify(
            html,
            heading_style="ATX",
            bullets="-",
            strip=["span"],
        ).strip()
        return f"{markdown}\n" if markdown else ""

    def to_json(self, path: str) -> dict[str, Any]:
        document = self._document_class(path)
        blocks = self._extract_blocks(document)
        tables = [block["rows"] for block in blocks if block["type"] == "table"]
        title = self._resolve_title(document, blocks)

        return {
            "title": title,
            "blocks": blocks,
            "tables": tables,
            "metadata": {
                "subject": self._normalize_text(document.core_properties.subject),
                "author": self._normalize_text(document.core_properties.author),
                "keywords": self._normalize_text(document.core_properties.keywords),
            },
        }

    def _extract_blocks(self, document) -> list[dict[str, Any]]:
        paragraphs = self._paragraph_class
        tables = self._table_class
        ct_paragraph = self._ct_paragraph
        ct_table = self._ct_table
        blocks: list[dict[str, Any]] = []

        for child in document.element.body.iterchildren():
            if isinstance(child, ct_paragraph):
                paragraph = paragraphs(child, document)
                payload = self._paragraph_to_block(paragraph)
                if payload is not None:
                    blocks.append(payload)
            elif isinstance(child, ct_table):
                table = tables(child, document)
                payload = self._table_to_block(table)
                if payload is not None:
                    blocks.append(payload)

        return blocks

    def _paragraph_to_block(self, paragraph) -> dict[str, Any] | None:
        text = self._normalize_text(paragraph.text)
        if not text:
            return None

        style_name = self._normalize_text(getattr(getattr(paragraph, "style", None), "name", None))
        level = self._heading_level(style_name)
        block_type = "heading" if level is not None else "paragraph"

        runs: list[dict[str, Any]] = []
        for run in getattr(paragraph, "runs", []):
            run_text = self._normalize_text(getattr(run, "text", None))
            if not run_text:
                continue
            runs.append(
                {
                    "text": run_text,
                    "bold": bool(getattr(run, "bold", False)),
                    "italic": bool(getattr(run, "italic", False)),
                    "underline": bool(getattr(run, "underline", False)),
                }
            )

        payload: dict[str, Any] = {
            "type": block_type,
            "text": text,
            "style": style_name,
            "runs": runs,
        }
        if level is not None:
            payload["level"] = level
        return payload

    def _table_to_block(self, table) -> dict[str, Any] | None:
        rows: list[list[str]] = []
        for row in getattr(table, "rows", []):
            values = [self._normalize_text(cell.text) for cell in getattr(row, "cells", [])]
            if any(values):
                rows.append(values)

        if not rows:
            return None

        return {
            "type": "table",
            "rows": rows,
        }

    def _resolve_title(self, document, blocks: list[dict[str, Any]]) -> str:
        core_title = self._normalize_text(document.core_properties.title)
        if core_title:
            return core_title

        for block in blocks:
            if block["type"] == "heading":
                return block["text"]

        for block in blocks:
            if block["type"] == "paragraph":
                return block["text"]

        return ""

    def _heading_level(self, style_name: str) -> int | None:
        if not style_name:
            return None

        normalized = self._normalize_style_name(style_name)
        for pattern in (
            r"^heading\s+(\d+)$",
            r"^标题\s*(\d+)$",
            r"^見出し\s*(\d+)$",
        ):
            match = re.match(pattern, normalized)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return None

        return None

    def _normalize_style_name(self, style_name: str) -> str:
        normalized = style_name.strip().replace("\u3000", " ").lower()
        return normalized.translate(str.maketrans("０１２３４５６７８９", "0123456789"))

    def _normalize_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @cached_property
    def _mammoth(self):
        import mammoth

        return mammoth

    @cached_property
    def _markdownify(self):
        from markdownify import markdownify

        return markdownify

    @cached_property
    def _document_class(self):
        from docx import Document

        return Document

    @cached_property
    def _paragraph_class(self):
        from docx.text.paragraph import Paragraph

        return Paragraph

    @cached_property
    def _table_class(self):
        from docx.table import Table

        return Table

    @cached_property
    def _ct_paragraph(self):
        from docx.oxml.text.paragraph import CT_P

        return CT_P

    @cached_property
    def _ct_table(self):
        from docx.oxml.table import CT_Tbl

        return CT_Tbl
