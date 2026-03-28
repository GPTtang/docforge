from types import SimpleNamespace

from converters.pptx_converter import PptxConverter


def test_pptx_converter_json_preserves_title_blocks_tables_and_notes() -> None:
    class FakeShapes:
        def __init__(self, title, shapes):
            self.title = title
            self._shapes = shapes

        def __iter__(self):
            return iter(self._shapes)

    title_shape = SimpleNamespace(text="Intro")
    text_shape = SimpleNamespace(
        has_text_frame=True,
        has_table=False,
        text_frame=SimpleNamespace(
            paragraphs=[
                SimpleNamespace(text="First point", level=0),
                SimpleNamespace(text="Nested point", level=1),
            ]
        ),
    )
    table_shape = SimpleNamespace(
        has_text_frame=False,
        has_table=True,
        table=SimpleNamespace(
            rows=[
                SimpleNamespace(cells=[SimpleNamespace(text="A"), SimpleNamespace(text="B")]),
                SimpleNamespace(cells=[SimpleNamespace(text="1"), SimpleNamespace(text="2")]),
            ]
        ),
    )
    slide = SimpleNamespace(
        shapes=FakeShapes(title_shape, [title_shape, text_shape, table_shape]),
        has_notes_slide=True,
        notes_slide=SimpleNamespace(notes_text_frame=SimpleNamespace(text="Speaker note")),
    )
    presentation = SimpleNamespace(
        core_properties=SimpleNamespace(title="", subject="deck", author="alice", keywords="demo"),
        slides=[slide],
    )

    converter = PptxConverter()
    converter.__dict__["_presentation_class"] = lambda path: presentation

    result = converter.to_json("example.pptx")

    assert result["title"] == "Intro"
    assert result["metadata"] == {
        "subject": "deck",
        "author": "alice",
        "keywords": "demo",
    }
    assert result["slides"] == [
        {
            "slide_number": 1,
            "title": "Intro",
            "blocks": [
                {
                    "type": "bullets",
                    "items": [
                        {"text": "First point", "level": 0},
                        {"text": "Nested point", "level": 1},
                    ],
                },
                {
                    "type": "table",
                    "rows": [["A", "B"], ["1", "2"]],
                },
            ],
            "notes": "Speaker note",
        }
    ]


def test_pptx_converter_markdown_renders_slide_content() -> None:
    converter = PptxConverter()
    converter.to_json = lambda path: {
        "title": "Deck",
        "slides": [
            {
                "slide_number": 1,
                "title": "Intro",
                "blocks": [
                    {"type": "text", "text": "Overview"},
                    {
                        "type": "bullets",
                        "items": [
                            {"text": "First point", "level": 0},
                            {"text": "Nested point", "level": 1},
                        ],
                    },
                    {"type": "table", "rows": [["A", "B"], ["1", "2"]]},
                ],
                "notes": "Speaker note",
            }
        ],
    }

    assert converter.to_markdown("example.pptx") == (
        "# Deck\n\n"
        "## Slide 1\n"
        "### Intro\n"
        "Overview\n"
        "- First point\n"
        "  - Nested point\n"
        "| A | B |\n"
        "| --- | --- |\n"
        "| 1 | 2 |\n"
        "### Notes\n"
        "Speaker note\n"
    )


def test_pptx_converter_keeps_multi_paragraph_text_as_text() -> None:
    class FakeParagraphProperties:
        def find(self, path, namespaces=None):
            return None

    shape = SimpleNamespace(
        text_frame=SimpleNamespace(
            paragraphs=[
                SimpleNamespace(text="Executive summary", level=0, _pPr=FakeParagraphProperties()),
                SimpleNamespace(text="Release date: 2026-03-29", level=0, _pPr=FakeParagraphProperties()),
            ]
        )
    )

    converter = PptxConverter()

    assert converter._text_block(shape) == {
        "type": "text",
        "text": "Executive summary\n\nRelease date: 2026-03-29",
    }
