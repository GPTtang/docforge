FROM python:3.11-slim

WORKDIR /app

# System dependencies required by OpenDataLoader PDF, Docling hybrid mode, and legacy Office conversion.
RUN apt-get update && apt-get install -y \
    curl \
    libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 \
    openjdk-21-jre-headless \
    libreoffice-core libreoffice-writer libreoffice-calc libreoffice-impress \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
ENV DOCFORGE_PYTHON_WORKERS=1
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${DOCFORGE_PYTHON_WORKERS}"]
