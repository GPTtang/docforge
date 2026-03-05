from docling.document_converter import DocumentConverter

class DoclingConverter:
    def __init__(self):
        self.converter = DocumentConverter()

    def to_markdown(self, path: str) -> str:
        result = self.converter.convert(path)
        return result.document.export_to_markdown()

    def to_json(self, path: str) -> dict:
        result = self.converter.convert(path)
        return result.document.export_to_dict()
