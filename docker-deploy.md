# Docker 部署指南

## python-service/Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 系统依赖（Docling 需要）
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 预热模型（构建时下载，避免运行时延迟）
RUN python -c "from docling.document_converter import DocumentConverter; DocumentConverter()"

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

## java-service/Dockerfile

```dockerfile
FROM eclipse-temurin:17-jdk-alpine AS builder
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN ./mvnw package -DskipTests

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  docling-service:
    build: ./python-service
    container_name: docforge-python
    ports:
      - "8000:8000"
    volumes:
      - model-cache:/root/.cache/docling
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  docforge-java:
    build: ./java-service
    container_name: docforge-java
    ports:
      - "8080:8080"
    environment:
      - DOCFORGE_PYTHON_SERVICE_URL=http://docling-service:8000
    depends_on:
      docling-service:
        condition: service_healthy
    restart: unless-stopped

volumes:
  model-cache:  # Docling 模型持久化，避免重复下载
```

## 常用命令

```bash
# 启动全部服务
docker compose up -d

# 查看日志
docker compose logs -f docling-service
docker compose logs -f docforge-java

# 重建某个服务
docker compose up -d --build docling-service

# 测试接口
curl -X POST http://localhost:8080/api/convert/markdown \
  -F "file=@test.pdf" | jq '.markdown'
```
