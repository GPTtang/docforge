FROM python:3.11-slim

WORKDIR /app

# 系统依赖（Docling 需要）
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 预热模型（构建时下载，避免运行时延迟）
RUN python -c "from docling.document_converter import DocumentConverter; DocumentConverter()"

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
