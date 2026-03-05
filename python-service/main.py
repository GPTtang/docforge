from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tempfile, os, logging
from pathlib import Path

from converters.docling_converter import DoclingConverter
from converters.marker_converter import MarkerConverter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DocForge Python Service", version="1.0.0")

docling = DoclingConverter()
marker = MarkerConverter()

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"
}

def save_temp_file(file: UploadFile) -> str:
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件格式: {suffix}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        return tmp.name

@app.post("/convert/markdown")
async def convert_to_markdown(file: UploadFile = File(...)):
    tmp_path = None
    try:
        tmp_path = save_temp_file(file)
        suffix = Path(file.filename).suffix.lower()

        # PDF 优先用 Marker（排版更好），CPU 环境 Marker 不稳定时自动降级 Docling
        if suffix == ".pdf":
            try:
                result = marker.to_markdown(tmp_path)
            except Exception as marker_err:
                logger.warning(f"Marker 转换失败，降级使用 Docling: {marker_err}")
                result = docling.to_markdown(tmp_path)
        else:
            result = docling.to_markdown(tmp_path)

        return {"filename": file.filename, "markdown": result, "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"转换失败: {e}")
        raise HTTPException(500, str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.post("/convert/json")
async def convert_to_json(file: UploadFile = File(...)):
    tmp_path = None
    try:
        tmp_path = save_temp_file(file)
        result = docling.to_json(tmp_path)
        return {"filename": file.filename, "data": result, "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"转换失败: {e}")
        raise HTTPException(500, str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.get("/health")
def health():
    return {"status": "ok", "service": "docforge-python"}

@app.get("/formats")
def supported_formats():
    return {"formats": list(SUPPORTED_EXTENSIONS)}
