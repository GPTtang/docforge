import shutil
import subprocess
from pathlib import Path


class OfficeConverter:
    def __init__(self, binary_name: str = "soffice"):
        self.binary_path = shutil.which(binary_name)

    @property
    def available(self) -> bool:
        return self.binary_path is not None

    def convert(self, source_path: str, target_extension: str, out_dir: str) -> str:
        if not self.available:
            raise RuntimeError("LibreOffice converter (soffice) is not available")

        src = Path(source_path)
        if not src.exists():
            raise RuntimeError(f"Source file not found: {source_path}")

        normalized_ext = target_extension.lower().lstrip(".")
        cmd = [
            self.binary_path,
            "--headless",
            "--convert-to",
            normalized_ext,
            "--outdir",
            out_dir,
            str(src),
        ]

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
            check=False,
        )

        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"LibreOffice conversion failed: {detail}")

        expected = Path(out_dir) / f"{src.stem}.{normalized_ext}"
        if expected.exists():
            return str(expected)

        candidates = sorted(Path(out_dir).glob(f"{src.stem}.*"))
        if candidates:
            return str(candidates[0])

        detail = (proc.stdout or proc.stderr or "").strip()
        raise RuntimeError(f"Converted file not found after LibreOffice conversion: {detail}")