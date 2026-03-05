from marker.convert import convert_single_pdf
from marker.models import load_all_models

class MarkerConverter:
    def __init__(self):
        self.models = load_all_models()

    def to_markdown(self, path: str) -> str:
        full_text, images, metadata = convert_single_pdf(
            path, self.models, max_pages=None
        )
        return full_text
