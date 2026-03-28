import json
import os
import subprocess
from functools import cached_property
from pathlib import Path
from tempfile import TemporaryDirectory


class OpenDataLoaderConverter:
    def __init__(self):
        self.hybrid = self._hybrid_backend()
        self.hybrid_mode = None
        self.hybrid_url = None
        self.hybrid_timeout = None
        self.hybrid_fallback = False

        if self.hybrid:
            self.hybrid_mode = self._normalized_env("DOCFORGE_OPENDATALOADER_HYBRID_MODE")
            self.hybrid_url = self._normalized_env("DOCFORGE_OPENDATALOADER_HYBRID_URL")
            self.hybrid_timeout = self._normalized_env("DOCFORGE_OPENDATALOADER_HYBRID_TIMEOUT")
            self.hybrid_fallback = self._bool_env("DOCFORGE_OPENDATALOADER_HYBRID_FALLBACK")

    def to_markdown(self, path: str) -> str:
        return self._convert_and_read(path, output_format="markdown", suffix=".md", image_output="embedded")

    def to_json(self, path: str) -> dict:
        payload = self._convert_and_read(path, output_format="json", suffix=".json")
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenDataLoader returned invalid JSON output") from exc

    def _convert_and_read(
        self,
        path: str,
        *,
        output_format: str,
        suffix: str,
        image_output: str | None = None,
    ) -> str:
        source = Path(path)
        with TemporaryDirectory(prefix="docforge-opendataloader-") as output_dir:
            self._run(
                input_path=str(source),
                output_dir=output_dir,
                output_format=output_format,
                image_output=image_output,
            )
            output_path = self._find_output_file(Path(output_dir), source.stem, suffix)
            try:
                return output_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise RuntimeError(
                    f"OpenDataLoader PDF output could not be read: {output_path.name}"
                ) from exc

    def _find_output_file(self, output_dir: Path, stem: str, suffix: str) -> Path:
        preferred = output_dir / f"{stem}{suffix}"
        if preferred.exists():
            return preferred

        candidates = sorted(output_dir.rglob(f"*{suffix}"))
        if len(candidates) == 1:
            return candidates[0]
        if candidates:
            for candidate in candidates:
                if candidate.stem == stem:
                    return candidate
            return candidates[0]

        raise RuntimeError(
            f"OpenDataLoader PDF did not produce {suffix} output for {stem}.pdf"
        )

    def _run(
        self,
        *,
        input_path: str,
        output_dir: str,
        output_format: str,
        image_output: str | None = None,
    ) -> None:
        kwargs: dict[str, object] = {
            "input_path": input_path,
            "output_dir": output_dir,
            "format": output_format,
            "quiet": True,
        }

        if image_output:
            kwargs["image_output"] = image_output

        if self.hybrid:
            kwargs["hybrid"] = self.hybrid
            if self.hybrid_mode:
                kwargs["hybrid_mode"] = self.hybrid_mode
            if self.hybrid_url:
                kwargs["hybrid_url"] = self.hybrid_url
            if self.hybrid_timeout:
                kwargs["hybrid_timeout"] = self.hybrid_timeout
            if self.hybrid_fallback:
                kwargs["hybrid_fallback"] = True

        try:
            self._runner(**kwargs)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "OpenDataLoader PDF requires Java 11+ to be installed and available on PATH"
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (
                getattr(exc, "output", None)
                or getattr(exc, "stderr", None)
                or ""
            ).strip()
            if detail:
                raise RuntimeError(f"OpenDataLoader PDF conversion failed: {detail}") from exc
            raise RuntimeError("OpenDataLoader PDF conversion failed") from exc

    @cached_property
    def _runner(self):
        try:
            from opendataloader_pdf import convert
        except ImportError as exc:
            raise RuntimeError(
                "opendataloader-pdf is not installed. Add it to the Python service environment."
            ) from exc
        return convert

    def _normalized_env(self, name: str) -> str | None:
        value = os.getenv(name)
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _hybrid_backend(self) -> str | None:
        value = self._normalized_env("DOCFORGE_OPENDATALOADER_HYBRID")
        if value is None:
            return None

        if value.lower() in {"0", "false", "no", "off"}:
            return None

        return value

    def _bool_env(self, name: str) -> bool:
        value = self._normalized_env(name)
        if value is None:
            return False
        return value.lower() in {"1", "true", "yes", "on"}
