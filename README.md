# DocForge

> Document conversion pipeline: Office & PDF → Markdown / JSON

**[English](#english) | [中文](#中文) | [日本語](#日本語)**

---

## English

### Overview

DocForge converts Word, Excel, PowerPoint, and PDF files into structured Markdown or JSON via a two-tier architecture:

```
Client → Java Spring Boot (port 8080) → Python FastAPI (port 8000) → Markdown / JSON
```

- **Python service**: Docling + Marker engines for document parsing
- **Java service**: Spring Boot REST API as the public-facing gateway
- **Swagger UI**: Interactive API documentation powered by springdoc-openapi

### Document Parsing Engines

DocForge relies on two open-source document parsing engines:

#### Docling

[Docling](https://github.com/DS4SD/docling) is an open-source document parsing library developed by **IBM Research**. It provides advanced document understanding capabilities, converting complex documents into structured data.

- **Supported formats**: PDF, Word (`.docx` / `.doc`), Excel (`.xlsx` / `.xls`), PowerPoint (`.pptx` / `.ppt`)
- **Key features**: Table extraction, OCR for scanned documents, layout analysis, multi-language support
- **License**: [MIT License](https://github.com/DS4SD/docling/blob/main/LICENSE) — permissive open-source license allowing commercial use
- **Repository**: [https://github.com/DS4SD/docling](https://github.com/DS4SD/docling)

#### Marker

[Marker](https://github.com/VikParuchuri/marker) is a high-quality PDF-to-Markdown conversion tool developed by **Vik Paruchuri**. It uses deep learning models to accurately extract text, tables, and formatting from PDF documents.

- **Supported formats**: PDF (`.pdf`)
- **Key features**: High-accuracy text extraction, table recognition, formula support, superior layout preservation
- **License**: [GPL-3.0 License](https://github.com/VikParuchuri/marker/blob/master/LICENSE) — open-source license requiring derivative works to also be open-sourced under GPL-3.0
- **Repository**: [https://github.com/VikParuchuri/marker](https://github.com/VikParuchuri/marker)

> **License Notice**: Marker is licensed under GPL-3.0. If you distribute derivative works based on DocForge that include Marker, you must comply with the GPL-3.0 license terms. For commercial use without GPL obligations, consider using Docling only or contact the Marker author for alternative licensing options.

### Supported Formats

| Format | Extension | Engine |
|--------|-----------|--------|
| PDF (text-based) | `.pdf` | Marker |
| PDF (scanned / OCR) | `.pdf` | Docling |
| Word | `.docx` `.doc` | Docling |
| Excel | `.xlsx` `.xls` | Docling |
| PowerPoint | `.pptx` `.ppt` | Docling |

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Disk | 20 GB free | 40+ GB free |
| GPU | Not required | NVIDIA GPU (speeds up Marker 10×) |

> **Notes:**
> - Docling and Marker both load large ML models into memory. Running without enough RAM will cause worker crashes.
> - Without a GPU, Marker falls back to CPU inference, which is slow (~60s per page). DocForge automatically falls back to Docling if Marker fails.
> - The `model-cache` Docker volume stores downloaded models (~5 GB). Ensure sufficient disk space before first run.

### Quick Start

**Prerequisites**: Docker and Docker Compose

```bash
# Clone and start all services
git clone https://github.com/GPTtang/docforge.git
cd docforge
docker compose up -d

# Check health
curl http://localhost:8080/api/convert/health
```

### Swagger UI

After starting the application, you can access the interactive API documentation:

| URL | Description |
|-----|-------------|
| `http://localhost:8080/swagger-ui/index.html` | Swagger UI - Interactive API documentation |
| `http://localhost:8080/v3/api-docs` | OpenAPI 3.0 JSON specification |

Swagger UI provides a visual interface to explore and test all API endpoints directly from your browser.

### API Reference

#### Convert to Markdown
```bash
POST http://localhost:8080/api/convert/markdown
Content-Type: multipart/form-data

curl -X POST http://localhost:8080/api/convert/markdown \
  -F "file=@document.pdf"
```

Response:
```json
{
  "filename": "document.pdf",
  "markdown": "# Introduction\n\n## Section 1\n\nThis is the first paragraph of the document.\n\n## Section 2\n\n| Column A | Column B | Column C |\n|----------|----------|----------|\n| Cell 1   | Cell 2   | Cell 3   |\n| Cell 4   | Cell 5   | Cell 6   |\n",
  "status": "success",
  "processing_time_ms": 3500
}
```

The `markdown` field contains standard Markdown. Rendered, it looks like:

```markdown
# Introduction

## Section 1

This is the first paragraph of the document.

## Section 2

| Column A | Column B | Column C |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
```

#### Convert to JSON
```bash
POST http://localhost:8080/api/convert/json
Content-Type: multipart/form-data

curl -X POST http://localhost:8080/api/convert/json \
  -F "file=@document.docx"
```

Response:
```json
{
  "filename": "document.docx",
  "data": {
    "title": "Document Title",
    "sections": [
      { "heading": "Section 1", "content": "..." }
    ],
    "tables": [
      { "headers": ["Column A", "Column B"], "rows": [["Cell 1", "Cell 2"]] }
    ]
  },
  "status": "success",
  "processing_time_ms": 2100
}
```

#### Health Check
```bash
GET http://localhost:8080/api/convert/health
```

Response:
```json
{
  "status": "ok",
  "python_service": "reachable",
  "marker_model_loaded": true
}
```

### Project Structure

```
docforge/
├── python-service/
│   ├── main.py
│   ├── converters/
│   │   ├── docling_converter.py
│   │   └── marker_converter.py
│   ├── requirements.txt
│   └── Dockerfile
├── java-service/
│   ├── src/main/java/com/docforge/
│   │   ├── controller/DocForgeController.java
│   │   ├── service/DocConvertService.java
│   │   ├── config/
│   │   │   ├── RestTemplateConfig.java
│   │   │   └── SwaggerConfig.java
│   │   ├── model/ConvertResponse.java
│   │   └── util/MultipartInputStreamFileResource.java
│   ├── pom.xml
│   └── Dockerfile
└── docker-compose.yml
```

### Configuration

Edit `java-service/src/main/resources/application.yml`:

```yaml
docforge:
  python:
    service-url: http://localhost:8000
    connect-timeout: 10000   # 10 seconds
    read-timeout: 120000     # 120 seconds (large files)
```

### Development (without Docker)

```bash
# Start Python service
cd python-service
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start Java service (separate terminal)
cd java-service
mvn spring-boot:run
```

### Notes

- Marker model loading takes ~30 seconds on first start; it is pre-loaded at startup.
- Docling model files are cached in a Docker volume (`model-cache`) to avoid repeated downloads.
- For files larger than 20 MB, consider the async endpoint pattern described in `format-strategy.md`.

---

## 中文

### 概述

DocForge 将 Word、Excel、PowerPoint 和 PDF 文件转换为结构化的 Markdown 或 JSON，采用两层架构：

```
客户端 → Java Spring Boot（端口 8080）→ Python FastAPI（端口 8000）→ Markdown / JSON
```

- **Python 服务**：基于 Docling + Marker 引擎进行文档解析
- **Java 服务**：Spring Boot REST API，作为对外暴露的网关层
- **Swagger UI**：基于 springdoc-openapi 的交互式 API 文档

### 文档解析引擎说明

DocForge 依赖以下两个开源文档解析引擎：

#### Docling

[Docling](https://github.com/DS4SD/docling) 是由 **IBM Research** 开发的开源文档解析库，提供高级文档理解能力，可将复杂文档转换为结构化数据。

- **支持格式**：PDF、Word（`.docx` / `.doc`）、Excel（`.xlsx` / `.xls`）、PowerPoint（`.pptx` / `.ppt`）
- **核心特性**：表格提取、扫描件 OCR、版面分析、多语言支持
- **开源许可**：[MIT License](https://github.com/DS4SD/docling/blob/main/LICENSE) — 宽松型开源许可，允许商业使用
- **项目地址**：[https://github.com/DS4SD/docling](https://github.com/DS4SD/docling)

#### Marker

[Marker](https://github.com/VikParuchuri/marker) 是由 **Vik Paruchuri** 开发的高质量 PDF 转 Markdown 工具，使用深度学习模型从 PDF 文档中精准提取文本、表格和格式。

- **支持格式**：PDF（`.pdf`）
- **核心特性**：高精度文本提取、表格识别、公式支持、优秀的版面保留
- **开源许可**：[GPL-3.0 License](https://github.com/VikParuchuri/marker/blob/master/LICENSE) — 开源许可，要求衍生作品同样以 GPL-3.0 开源
- **项目地址**：[https://github.com/VikParuchuri/marker](https://github.com/VikParuchuri/marker)

> **许可证声明**：Marker 使用 GPL-3.0 许可证。如果您分发包含 Marker 的 DocForge 衍生作品，必须遵守 GPL-3.0 许可证条款。若需在商业项目中使用且不希望受 GPL 约束，可考虑仅使用 Docling 引擎，或联系 Marker 作者获取替代许可。

### 支持的文件格式

| 格式 | 扩展名 | 使用引擎 |
|------|--------|---------|
| PDF（文字版） | `.pdf` | Marker |
| PDF（扫描版/OCR） | `.pdf` | Docling |
| Word 文档 | `.docx` `.doc` | Docling |
| Excel 表格 | `.xlsx` `.xls` | Docling |
| PowerPoint 演示 | `.pptx` `.ppt` | Docling |

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 4 核 | 8 核以上 |
| 内存 | 8 GB | 16 GB 以上 |
| 磁盘 | 20 GB 可用空间 | 40 GB 以上 |
| GPU | 不必须 | NVIDIA GPU（Marker 速度提升 10 倍） |

> **说明：**
> - Docling 和 Marker 均需加载大型机器学习模型，内存不足会导致 Worker 进程崩溃。
> - 无 GPU 时 Marker 使用 CPU 推理，速度较慢（每页约 60 秒）。DocForge 在 Marker 失败时会自动降级使用 Docling。
> - `model-cache` Docker Volume 存储下载的模型文件（约 5 GB），首次运行前请确保磁盘空间充足。

### 快速启动

**前置条件**：已安装 Docker 和 Docker Compose

```bash
# 克隆仓库并启动所有服务
git clone https://github.com/GPTtang/docforge.git
cd docforge
docker compose up -d

# 检查服务状态
curl http://localhost:8080/api/convert/health
```

### Swagger UI

启动应用后，可通过以下地址访问交互式 API 文档：

| 地址 | 说明 |
|------|------|
| `http://localhost:8080/swagger-ui/index.html` | Swagger UI — 交互式 API 文档页面 |
| `http://localhost:8080/v3/api-docs` | OpenAPI 3.0 JSON 规范文件 |

Swagger UI 提供可视化界面，可直接在浏览器中浏览和测试所有 API 端点。

### API 接口说明

#### 转换为 Markdown
```bash
POST http://localhost:8080/api/convert/markdown
Content-Type: multipart/form-data

curl -X POST http://localhost:8080/api/convert/markdown \
  -F "file=@文档.pdf"
```

返回示例：
```json
{
  "filename": "文档.pdf",
  "markdown": "# 简介\n\n## 第一章\n\n这是文档的第一段正文内容。\n\n## 第二章\n\n| 列A | 列B | 列C |\n|-----|-----|-----|\n| 数据1 | 数据2 | 数据3 |\n| 数据4 | 数据5 | 数据6 |\n",
  "status": "success",
  "processing_time_ms": 3500
}
```

`markdown` 字段包含标准 Markdown 文本，渲染后效果如下：

```markdown
# 简介

## 第一章

这是文档的第一段正文内容。

## 第二章

| 列A  | 列B  | 列C  |
|------|------|------|
| 数据1 | 数据2 | 数据3 |
| 数据4 | 数据5 | 数据6 |
```

#### 转换为 JSON
```bash
POST http://localhost:8080/api/convert/json
Content-Type: multipart/form-data

curl -X POST http://localhost:8080/api/convert/json \
  -F "file=@文档.docx"
```

返回示例：
```json
{
  "filename": "文档.docx",
  "data": {
    "title": "文档标题",
    "sections": [
      { "heading": "第一章", "content": "..." }
    ],
    "tables": [
      { "headers": ["列A", "列B"], "rows": [["数据1", "数据2"]] }
    ]
  },
  "status": "success",
  "processing_time_ms": 2100
}
```

#### 健康检查
```bash
GET http://localhost:8080/api/convert/health
```

返回示例：
```json
{
  "status": "ok",
  "python_service": "reachable",
  "marker_model_loaded": true
}
```

### 项目结构

```
docforge/
├── python-service/
│   ├── main.py                      # FastAPI 入口
│   ├── converters/
│   │   ├── docling_converter.py     # Docling 引擎
│   │   └── marker_converter.py      # Marker 引擎
│   ├── requirements.txt
│   └── Dockerfile
├── java-service/
│   ├── src/main/java/com/docforge/
│   │   ├── controller/DocForgeController.java
│   │   ├── service/DocConvertService.java
│   │   ├── config/
│   │   │   ├── RestTemplateConfig.java  # RestTemplate 配置
│   │   │   └── SwaggerConfig.java       # Swagger OpenAPI 配置
│   │   ├── model/ConvertResponse.java
│   │   └── util/MultipartInputStreamFileResource.java
│   ├── pom.xml
│   └── Dockerfile
└── docker-compose.yml
```

### 配置说明

编辑 `java-service/src/main/resources/application.yml`：

```yaml
docforge:
  python:
    service-url: http://localhost:8000
    connect-timeout: 10000   # 连接超时：10 秒
    read-timeout: 120000     # 读取超时：120 秒（大文件）
```

### 本地开发（不使用 Docker）

```bash
# 启动 Python 服务
cd python-service
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动 Java 服务（另开终端）
cd java-service
mvn spring-boot:run
```

### 注意事项

- Marker 模型首次启动加载约需 30 秒，已在服务启动时预加载，请勿每次请求重复加载。
- Docling 模型文件通过 Docker volume（`model-cache`）持久化，避免重复下载。
- 文件大于 20 MB 时，建议参考 `format-strategy.md` 中的异步处理方案。

---

## 日本語

### 概要

DocForge は、Word / Excel / PowerPoint / PDF を構造化された Markdown または JSON に変換するドキュメント変換パイプラインです。

```
クライアント → Java Spring Boot（8080）→ Python FastAPI（8000）→ Markdown / JSON
```

- **Python サービス**: Docling + Marker による文書解析
- **Java サービス**: 外部公開用 REST API ゲートウェイ
- **Swagger UI**: ブラウザから API を直接試せるドキュメント

### 対応フォーマット

| 種別 | 拡張子 | 変換エンジン |
|------|--------|-------------|
| PDF（テキスト） | `.pdf` | Marker（失敗時は Docling へフォールバック） |
| PDF（スキャン/OCR） | `.pdf` | Docling |
| Word | `.docx` | Docling |
| Word（旧形式） | `.doc` | LibreOffice で `.docx` に変換後 Docling |
| Excel | `.xlsx` | Spreadsheet Converter（openpyxl） |
| Excel（旧形式） | `.xls` | LibreOffice で `.xlsx` に変換後 openpyxl |
| PowerPoint | `.pptx` | Docling |
| PowerPoint（旧形式） | `.ppt` | LibreOffice で `.pptx` に変換後 Docling |

### クイックスタート

前提: Docker / Docker Compose

```bash
git clone https://github.com/GPTtang/docforge.git
cd docforge
docker compose up -d

# ヘルスチェック
curl http://localhost:8080/api/convert/health
```

### API

#### Markdown 変換
```bash
curl -X POST http://localhost:8080/api/convert/markdown \
  -F "file=@document.pdf"
```

#### JSON 変換
```bash
curl -X POST http://localhost:8080/api/convert/json \
  -F "file=@document.docx"
```

#### 利用可能形式の確認（Python サービス）
```bash
curl http://localhost:8000/formats
```

### Swagger UI

- `http://localhost:8080/swagger-ui/index.html`
- `http://localhost:8080/v3/api-docs`

### 備考

- 初回起動時はモデル読み込みのため時間がかかる場合があります。
- `model-cache` ボリュームにモデルを保存するため、再起動時のダウンロードを削減できます。
- 大きなファイルを処理する場合は、メモリと CPU に余裕のある環境を推奨します。

---
## Acknowledgements / 致谢

This project is built upon the following outstanding open-source projects:

本项目基于以下优秀的开源项目构建：

| Project | Author | License | Description |
|---------|--------|---------|-------------|
| [Docling](https://github.com/DS4SD/docling) | IBM Research | MIT | Document parsing library for PDF, Word, Excel, PowerPoint |
| [Marker](https://github.com/VikParuchuri/marker) | Vik Paruchuri | GPL-3.0 | High-quality PDF to Markdown converter using deep learning |
| [Spring Boot](https://github.com/spring-projects/spring-boot) | VMware / Pivotal | Apache-2.0 | Java framework for building production-ready applications |
| [FastAPI](https://github.com/tiangolo/fastapi) | Sebastián Ramírez | MIT | Modern Python web framework for building APIs |
| [springdoc-openapi](https://github.com/springdoc/springdoc-openapi) | springdoc | Apache-2.0 | OpenAPI 3.0 documentation for Spring Boot |
