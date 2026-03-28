from types import SimpleNamespace

from converters.docx_converter import DocxConverter


def test_docx_converter_markdown_uses_mammoth_and_markdownify(tmp_path) -> None:
    path = tmp_path / "example.docx"
    path.write_bytes(b"docx")

    converter = DocxConverter()
    converter.__dict__["_mammoth"] = SimpleNamespace(
        convert_to_html=lambda source: SimpleNamespace(value="<h1>Title</h1><p>Hello</p>"),
        extract_raw_text=lambda source: SimpleNamespace(value="Hello"),
    )
    converter.__dict__["_markdownify"] = (
        lambda html, **kwargs: "# Title\n\nHello"
    )

    assert converter.to_markdown(str(path)) == "# Title\n\nHello\n"


def test_docx_converter_json_preserves_heading_paragraph_and_table() -> None:
    class FakeCTParagraph:
        def __init__(self, value):
            self.value = value

    class FakeCTTable:
        def __init__(self, value):
            self.value = value

    heading = SimpleNamespace(
        text="Document Title",
        style=SimpleNamespace(name="Heading 1"),
        runs=[SimpleNamespace(text="Document Title", bold=True, italic=False, underline=False)],
    )
    paragraph = SimpleNamespace(
        text="Body paragraph",
        style=SimpleNamespace(name="Normal"),
        runs=[SimpleNamespace(text="Body paragraph", bold=False, italic=False, underline=False)],
    )
    table = SimpleNamespace(
        rows=[
            SimpleNamespace(cells=[SimpleNamespace(text="A1"), SimpleNamespace(text="B1")]),
            SimpleNamespace(cells=[SimpleNamespace(text="A2"), SimpleNamespace(text="B2")]),
        ]
    )

    document = SimpleNamespace(
        core_properties=SimpleNamespace(title="", subject="spec", author="alice", keywords="demo"),
        element=SimpleNamespace(
            body=SimpleNamespace(
                iterchildren=lambda: [
                    FakeCTParagraph(heading),
                    FakeCTParagraph(paragraph),
                    FakeCTTable(table),
                ]
            )
        ),
    )

    converter = DocxConverter()
    converter.__dict__["_document_class"] = lambda path: document
    converter.__dict__["_paragraph_class"] = lambda child, doc: child.value
    converter.__dict__["_table_class"] = lambda child, doc: child.value
    converter.__dict__["_ct_paragraph"] = FakeCTParagraph
    converter.__dict__["_ct_table"] = FakeCTTable

    result = converter.to_json("example.docx")

    assert result["title"] == "Document Title"
    assert result["metadata"] == {
        "subject": "spec",
        "author": "alice",
        "keywords": "demo",
    }
    assert result["blocks"] == [
        {
            "type": "heading",
            "text": "Document Title",
            "style": "Heading 1",
            "runs": [
                {
                    "text": "Document Title",
                    "bold": True,
                    "italic": False,
                    "underline": False,
                }
            ],
            "level": 1,
        },
        {
            "type": "paragraph",
            "text": "Body paragraph",
            "style": "Normal",
            "runs": [
                {
                    "text": "Body paragraph",
                    "bold": False,
                    "italic": False,
                    "underline": False,
                }
            ],
        },
        {
            "type": "table",
            "rows": [["A1", "B1"], ["A2", "B2"]],
        },
    ]
    assert result["tables"] == [
        [["A1", "B1"], ["A2", "B2"]],
    ]


def test_docx_converter_recognizes_localized_heading_styles() -> None:
    converter = DocxConverter()

    assert converter._heading_level("Heading 2") == 2
    assert converter._heading_level("标题 1") == 1
    assert converter._heading_level("标题　２") == 2
    assert converter._heading_level("見出し 3") == 3
    assert converter._heading_level("Normal") is None
