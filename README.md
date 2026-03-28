# DocForge

> Document conversion pipeline: Office & PDF → Markdown / JSON

**[English](#english) | [中文](#中文) | [日本語](#日本語)**

---

## English

### Overview

DocForge converts Word, Excel, PowerPoint, and PDF files into structured Markdown or JSON via a gateway + local-engine architecture:

```
Client
  → Java Spring Boot gateway (port 8080)
  → Python FastAPI conversion service (internal port 8000)
  → Local conversion engines by file type
  → Markdown / JSON
```

- **Python service**: OpenDataLoader PDF for PDF parsing, specialized local converters for Office formats
- **Java service**: Spring Boot REST API as the public-facing gateway
- **Hybrid backend**: optional `opendataloader-hybrid` service for OCR / difficult PDF pages
- **Swagger UI**: Interactive API documentation powered by springdoc-openapi

### Document Parsing Engines

DocForge relies on OpenDataLoader PDF as the PDF engine and uses Docling only as the optional hybrid backend for difficult PDF pages.

#### OpenDataLoader PDF

[OpenDataLoader PDF](https://github.com/opendataloader-project/opendataloader-pdf) is an open-source PDF extraction engine focused on reading order, structured JSON, and hybrid PDF understanding.

- **Supported formats**: PDF (`.pdf`)
- **Key features**: Markdown/JSON output, layout-aware reading order, optional hybrid Docling backend for OCR and complex pages
- **License**: [Apache-2.0](https://github.com/opendataloader-project/opendataloader-pdf/blob/main/LICENSE)
- **Repository**: [https://github.com/opendataloader-project/opendataloader-pdf](https://github.com/opendataloader-project/opendataloader-pdf)

#### Docling

[Docling](https://github.com/DS4SD/docling) is an open-source document parsing library developed by **IBM Research**. It provides advanced document understanding capabilities, converting complex documents into structured data.

- **Role in DocForge**: optional hybrid backend for OCR, scanned PDFs, and difficult layouts
- **Key features**: OCR for scanned documents, layout analysis, multi-language support
- **License**: [MIT License](https://github.com/DS4SD/docling/blob/main/LICENSE) — permissive open-source license allowing commercial use
- **Repository**: [https://github.com/DS4SD/docling](https://github.com/DS4SD/docling)

### Supported Formats

| Format | Extension | Engine |
|--------|-----------|--------|
| PDF (text-based) | `.pdf` | OpenDataLoader PDF |
| PDF (scanned / OCR) | `.pdf` | OpenDataLoader PDF + Hybrid Docling Backend |
| Word | `.docx` `.doc` | Mammoth + python-docx |
| Excel | `.xlsx` `.xls` | openpyxl |
| PowerPoint | `.pptx` `.ppt` | python-pptx |

#### Spreadsheet JSON Schema

Excel conversions expose a richer schema tailored for downstream LLM/RAG use:

```json
{
  "sheets": [
    {
      "name": "Sheet1",
      "columns": ["A", "B", "C"],
      "rows": [
        [
          {
            "value": "42",
            "formula": "=SUM(A1:A3)",
            "raw_value": "=SUM(A1:A3)",
            "number_format": "0",
            "hyperlink": null,
            "comment": null,
            "merged": "A1:B2"
          }
        ]
      ]
    }
  ]
}
```

Each cell carries the rendered value (computed via Excel's cached result), the original formula, number format, hyperlinks, comments, and merged range metadata. The Markdown exporter reuses this information to annotate formulas (`=...`), hyperlinks, and merged ranges inline.

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Disk | 20 GB free | 40+ GB free |
| GPU | Not required | Optional |

> **Notes:**
> - PDF conversion now uses OpenDataLoader PDF locally and can route difficult pages to the `opendataloader-hybrid` Docling backend.
> - The `model-cache` Docker volume stores downloaded Docling/OCR models (~5 GB). Ensure sufficient disk space before first run.

### Quick Start

**Prerequisites**: Docker and Docker Compose

```bash
# Clone and build/start all services
git clone https://github.com/GPTtang/docforge.git
cd docforge
docker compose up -d --build

# Check health
curl http://localhost:8080/api/convert/health
```

### Deployment Layout

After `docker compose up -d --build`, DocForge starts these containers:

| Container | Port | Responsibility |
|-----------|------|----------------|
| `docforge-java` | `8080` (host-exposed) | Public REST gateway and Swagger UI |
| `docforge-python` | `8000` (internal only) | Main conversion service and file-type routing |
| `docforge-opendataloader-hybrid` | `5002` (internal only) | Optional PDF hybrid backend for OCR / difficult pages |

Request flow by document type:

- `PDF`: `client -> java-service -> python-service -> OpenDataLoader PDF`
- `PDF` with hybrid enabled: `client -> java-service -> python-service -> opendataloader-hybrid`
- `DOCX/DOC`: `client -> java-service -> python-service -> Mammoth + python-docx`
- `PPTX/PPT`: `client -> java-service -> python-service -> python-pptx`
- `XLSX/XLS`: `client -> java-service -> python-service -> openpyxl`

Legacy Office formats (`.doc`, `.ppt`, `.xls`) are first converted with LibreOffice inside the Python service and then routed to the modern-format converter.

### Deployment Profiles

Use the following profiles as the starting point for production or local deployment:

| Profile | CPU / RAM | PDF Hybrid | `DOCFORGE_PYTHON_WORKERS` | Recommended Use |
|---------|-----------|------------|---------------------------|-----------------|
| Minimum | 4 cores / 8 GB | `off` | `1` | Office documents and text-based PDFs; lowest resource footprint |
| Recommended | 8+ cores / 16+ GB | `docling-fast` | `2` | Mixed Office/PDF workloads, including scanned PDFs and OCR-heavy cases |

Parameter guidance:

- `DOCFORGE_PYTHON_WORKERS`: set to `1` on the minimum profile and `2` on the recommended profile.
- `DOCFORGE_OPENDATALOADER_HYBRID`: set to `off` for the minimum profile; set to `docling-fast` for the recommended profile.
- `DOCFORGE_OPENDATALOADER_HYBRID_SERVER_ARGS`: leave empty by default; add OCR-specific flags only when required by your documents.

Example commands:

```bash
# Recommended profile
DOCFORGE_PYTHON_WORKERS=2 \
DOCFORGE_OPENDATALOADER_HYBRID=docling-fast \
docker compose up -d --build

# Recommended profile with explicit OCR flags
DOCFORGE_PYTHON_WORKERS=2 \
DOCFORGE_OPENDATALOADER_HYBRID=docling-fast \
DOCFORGE_OPENDATALOADER_HYBRID_SERVER_ARGS="--force-ocr --ocr-lang en" \
docker compose up -d --build

# Minimum profile
DOCFORGE_PYTHON_WORKERS=1 \
DOCFORGE_OPENDATALOADER_HYBRID=off \
docker compose up -d --build docforge-java docling-service
```

### Swagger UI

After starting the application, you can access the interactive API documentation:

| URL | Description |
|-----|-------------|
| `http://localhost:8080/` | Redirects to Swagger UI |
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
  "status": "success"
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
  "status": "success"
}
```

#### Health Check
```bash
GET http://localhost:8080/api/convert/health
```

Response:
```json
{
  "java": "ok",
  "python": "ok"
}
```

### Project Structure

```
docforge/
├── README.md
├── docker-compose.yml
├── python-service/
│   ├── main.py                      # FastAPI entrypoint and routing
│   ├── converters/
│   │   ├── opendataloader_converter.py  # PDF -> OpenDataLoader PDF
│   │   ├── office_converter.py          # Legacy Office -> LibreOffice bridge
│   │   ├── docx_converter.py            # DOCX -> Mammoth + python-docx
│   │   ├── pptx_converter.py            # PPTX -> python-pptx
│   │   └── spreadsheet_converter.py     # XLSX -> openpyxl
│   ├── tests/                       # Python regression tests
│   ├── requirements.txt
│   └── Dockerfile
├── java-service/
│   ├── src/main/java/com/docforge/
│   │   ├── controller/DocForgeController.java   # Public REST endpoints
│   │   ├── controller/HomeController.java       # Root -> Swagger redirect
│   │   ├── service/DocConvertService.java       # Gateway -> Python forwarding
│   │   ├── config/
│   │   │   ├── RestTemplateConfig.java
│   │   │   └── SwaggerConfig.java
│   │   ├── model/ConvertResponse.java
│   │   └── util/MultipartInputStreamFileResource.java
│   ├── pom.xml
│   └── Dockerfile
├── scripts/
│   ├── run_benchmark.py             # In-process benchmark helper
│   └── generate_test_documents.py   # Regenerates Office fixtures
└── test-documents/                  # Curated PDF samples and generated Office fixtures
```

### Benchmarking Quality

Use the `scripts/run_benchmark.py` helper to reproduce the four-document evaluation mentioned in the comparison article. It loads the FastAPI app in-process via `TestClient`, so Docker is not required:

```bash
python scripts/run_benchmark.py \
  --samples ./path/to/sample.docx ./path/to/sample.pptx \
           ./path/to/sample.xlsx ./path/to/sample.pdf \
  --output benchmark-results.json
```

The script records per-document status codes, latency, and compact previews for both Markdown and JSON targets. Inspect `benchmark-results.json` to compare heading stability, table fidelity, reading order, and schema consistency across converter combinations.

### Configuration

For local development, when the Java service talks to a separately started Python service, edit `java-service/src/main/resources/application.yml`:

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

- `opendataloader-hybrid` is optional at runtime. Leave it enabled for OCR / difficult PDFs, or disable it with `DOCFORGE_OPENDATALOADER_HYBRID=off`.
- Docling model files are cached in a Docker volume (`model-cache`) to avoid repeated downloads.
- For files larger than 20 MB, consider the async endpoint pattern described in `format-strategy.md`.

---

## 中文

### 概述

DocForge 将 Word、Excel、PowerPoint 和 PDF 文件转换为结构化的 Markdown 或 JSON，采用“Java 网关 + 本地转换引擎”的架构：

```
客户端
  → Java Spring Boot 网关（8080）
  → Python FastAPI 转换服务（内部端口 8000）
  → 按文件类型选择本地转换引擎
  → Markdown / JSON
```

- **Python 服务**：PDF 使用 OpenDataLoader PDF，Office 文档使用专用本地转换器
- **Java 服务**：Spring Boot REST API，作为对外暴露的网关层
- **Hybrid 后端**：可选的 `opendataloader-hybrid`，用于 OCR 与复杂 PDF 页面
- **Swagger UI**：基于 springdoc-openapi 的交互式 API 文档

### 文档解析引擎说明

DocForge 的 PDF 主引擎是 OpenDataLoader PDF；Docling 只作为可选 hybrid backend 使用，不再承担 Office 主链转换。

#### Docling

[Docling](https://github.com/DS4SD/docling) 是由 **IBM Research** 开发的开源文档解析库，提供高级文档理解能力，可将复杂文档转换为结构化数据。

- **在 DocForge 中的角色**：可选 hybrid backend，用于 OCR、扫描 PDF 和复杂版面
- **核心特性**：扫描件 OCR、版面分析、多语言支持
- **开源许可**：[MIT License](https://github.com/DS4SD/docling/blob/main/LICENSE) — 宽松型开源许可，允许商业使用
- **项目地址**：[https://github.com/DS4SD/docling](https://github.com/DS4SD/docling)

#### OpenDataLoader PDF

[OpenDataLoader PDF](https://github.com/opendataloader-project/opendataloader-pdf) 是面向 PDF 结构化提取的开源引擎，强调阅读顺序、结构化 JSON 以及 hybrid 文档理解。

- **支持格式**：PDF（`.pdf`）
- **核心特性**：Markdown/JSON 输出、版面感知阅读顺序、可选 hybrid Docling backend 处理 OCR 与复杂页面
- **开源许可**：[Apache-2.0](https://github.com/opendataloader-project/opendataloader-pdf/blob/main/LICENSE)
- **项目地址**：[https://github.com/opendataloader-project/opendataloader-pdf](https://github.com/opendataloader-project/opendataloader-pdf)

### 支持的文件格式

| 格式 | 扩展名 | 使用引擎 |
|------|--------|---------|
| PDF（文字版） | `.pdf` | OpenDataLoader PDF |
| PDF（扫描版/OCR） | `.pdf` | OpenDataLoader PDF + Hybrid Docling Backend |
| Word 文档 | `.docx` `.doc` | Mammoth + python-docx |
| Excel 表格 | `.xlsx` `.xls` | openpyxl |
| PowerPoint 演示 | `.pptx` `.ppt` | python-pptx |

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 4 核 | 8 核以上 |
| 内存 | 8 GB | 16 GB 以上 |
| 磁盘 | 20 GB 可用空间 | 40 GB 以上 |
| GPU | 不必须 | 可选 |

> **说明：**
> - PDF 转换默认使用 OpenDataLoader PDF，本地解析与 hybrid Docling backend 可组合使用。
> - `model-cache` Docker Volume 存储下载的 Docling/OCR 模型文件（约 5 GB），首次运行前请确保磁盘空间充足。

### 快速启动

**前置条件**：已安装 Docker 和 Docker Compose

```bash
# 克隆仓库并构建/启动所有服务
git clone https://github.com/GPTtang/docforge.git
cd docforge
docker compose up -d --build

# 检查服务状态
curl http://localhost:8080/api/convert/health
```

### 部署后的容器结构

执行 `docker compose up -d --build` 后，默认会启动以下 3 个容器：

| 容器名 | 端口 | 作用 |
|--------|------|------|
| `docforge-java` | `8080`（宿主机暴露） | 对外 REST 网关和 Swagger UI |
| `docforge-python` | `8000`（仅容器内部） | 主转换服务和格式路由 |
| `docforge-opendataloader-hybrid` | `5002`（仅容器内部） | 可选 PDF hybrid backend，用于 OCR / 复杂页面 |

按文件类型的真实请求链路如下：

- `PDF`：`client -> java-service -> python-service -> OpenDataLoader PDF`
- `PDF + hybrid`：`client -> java-service -> python-service -> opendataloader-hybrid`
- `DOCX/DOC`：`client -> java-service -> python-service -> Mammoth + python-docx`
- `PPTX/PPT`：`client -> java-service -> python-service -> python-pptx`
- `XLSX/XLS`：`client -> java-service -> python-service -> openpyxl`

旧版 Office 格式（`.doc`、`.ppt`、`.xls`）会先在 Python 服务内部通过 LibreOffice 转换成新格式，再进入对应转换器。

### 部署配置建议

建议按下面两档资源配置来部署：

| 配置档位 | CPU / 内存 | PDF Hybrid | `DOCFORGE_PYTHON_WORKERS` | 适用场景 |
|---------|------------|------------|---------------------------|---------|
| 最低配置 | 4 核 / 8 GB | `off` | `1` | 以 Office 文档和文字版 PDF 为主，追求最低资源占用 |
| 建议配置 | 8 核以上 / 16 GB 以上 | `docling-fast` | `2` | 混合 Office/PDF 负载，包含扫描件、OCR、复杂版面 |

参数调整建议：

- `DOCFORGE_PYTHON_WORKERS`：最低配置设为 `1`，建议配置设为 `2`。
- `DOCFORGE_OPENDATALOADER_HYBRID`：最低配置设为 `off`，建议配置设为 `docling-fast`。
- `DOCFORGE_OPENDATALOADER_HYBRID_SERVER_ARGS`：默认留空；只有在文档确实需要 OCR 或额外增强时再追加参数。

启动示例：

```bash
# 建议配置
DOCFORGE_PYTHON_WORKERS=2 \
DOCFORGE_OPENDATALOADER_HYBRID=docling-fast \
docker compose up -d --build

# 建议配置 + 显式 OCR 参数
DOCFORGE_PYTHON_WORKERS=2 \
DOCFORGE_OPENDATALOADER_HYBRID=docling-fast \
DOCFORGE_OPENDATALOADER_HYBRID_SERVER_ARGS="--force-ocr --ocr-lang en" \
docker compose up -d --build

# 最低配置
DOCFORGE_PYTHON_WORKERS=1 \
DOCFORGE_OPENDATALOADER_HYBRID=off \
docker compose up -d --build docforge-java docling-service
```

### Swagger UI

启动应用后，可通过以下地址访问交互式 API 文档：

| 地址 | 说明 |
|------|------|
| `http://localhost:8080/` | 自动跳转到 Swagger UI |
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
  "status": "success"
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
  "status": "success"
}
```

#### 健康检查
```bash
GET http://localhost:8080/api/convert/health
```

返回示例：
```json
{
  "java": "ok",
  "python": "ok"
}
```

### 项目结构

```
docforge/
├── README.md
├── docker-compose.yml
├── python-service/
│   ├── main.py                      # FastAPI 入口
│   ├── converters/
│   │   ├── opendataloader_converter.py  # PDF -> OpenDataLoader PDF
│   │   ├── office_converter.py      # 旧 Office -> LibreOffice 桥接
│   │   ├── docx_converter.py        # DOCX -> Mammoth + python-docx
│   │   ├── pptx_converter.py        # PPTX -> python-pptx
│   │   └── spreadsheet_converter.py # XLSX -> openpyxl
│   ├── tests/                       # Python 回归测试
│   ├── requirements.txt
│   └── Dockerfile
├── java-service/
│   ├── src/main/java/com/docforge/
│   │   ├── controller/DocForgeController.java   # 对外 REST 接口
│   │   ├── controller/HomeController.java       # 根路径跳转到 Swagger
│   │   ├── service/DocConvertService.java       # 网关转发到 Python
│   │   ├── config/
│   │   │   ├── RestTemplateConfig.java  # RestTemplate 配置
│   │   │   └── SwaggerConfig.java       # Swagger OpenAPI 配置
│   │   ├── model/ConvertResponse.java
│   │   └── util/MultipartInputStreamFileResource.java
│   ├── pom.xml
│   └── Dockerfile
├── scripts/
│   ├── run_benchmark.py             # 本地基准测试
│   └── generate_test_documents.py   # 生成 Office 测试夹具
└── test-documents/                  # PDF 样本和 Office 回归样本
```

### 配置说明

如果是在本地开发模式下单独启动 Java 和 Python 服务，可编辑 `java-service/src/main/resources/application.yml`：

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

- `opendataloader-hybrid` 是运行时可选组件。需要 OCR/复杂 PDF 时保持开启；若只需本地基础 PDF 解析，可设置 `DOCFORGE_OPENDATALOADER_HYBRID=off`。
- Docling 模型文件通过 Docker volume（`model-cache`）持久化，避免重复下载。
- 文件大于 20 MB 时，建议参考 `format-strategy.md` 中的异步处理方案。

---

## 日本語

### 概要

DocForge は、Word / Excel / PowerPoint / PDF を構造化された Markdown または JSON に変換する、Java ゲートウェイ + ローカル変換エンジン構成のドキュメント変換パイプラインです。

```
クライアント
  → Java Spring Boot ゲートウェイ（8080）
  → Python FastAPI 変換サービス（内部ポート 8000）
  → ファイル形式ごとのローカル変換エンジン
  → Markdown / JSON
```

- **Python サービス**: PDF は OpenDataLoader PDF、Office 文書は専用のローカル変換器を使用
- **Java サービス**: 外部公開用 REST API ゲートウェイ
- **Hybrid バックエンド**: OCR や難しい PDF ページ向けの `opendataloader-hybrid`
- **Swagger UI**: ブラウザから API を直接試せるドキュメント

### デプロイ後の構成

`docker compose up -d --build` 実行後、デフォルトでは次の 3 コンテナが起動します。

| コンテナ | ポート | 役割 |
|---------|--------|------|
| `docforge-java` | `8080`（ホスト公開） | 公開 REST ゲートウェイと Swagger UI |
| `docforge-python` | `8000`（コンテナ内部のみ） | メイン変換サービスと形式ルーティング |
| `docforge-opendataloader-hybrid` | `5002`（コンテナ内部のみ） | OCR / 難しい PDF 用の任意 hybrid バックエンド |

実際のリクエスト経路:

- `PDF`: `client -> java-service -> python-service -> OpenDataLoader PDF`
- `PDF + hybrid`: `client -> java-service -> python-service -> opendataloader-hybrid`
- `DOCX/DOC`: `client -> java-service -> python-service -> Mammoth + python-docx`
- `PPTX/PPT`: `client -> java-service -> python-service -> python-pptx`
- `XLSX/XLS`: `client -> java-service -> python-service -> openpyxl`

旧 Office 形式（`.doc`、`.ppt`、`.xls`）は、まず Python サービス内で LibreOffice により新形式へ変換されます。

### 対応フォーマット

| 種別 | 拡張子 | 変換エンジン |
|------|--------|-------------|
| PDF（テキスト） | `.pdf` | OpenDataLoader PDF |
| PDF（スキャン/OCR） | `.pdf` | OpenDataLoader PDF + Hybrid Docling Backend |
| Word | `.docx` | Mammoth + python-docx |
| Word（旧形式） | `.doc` | LibreOffice で `.docx` に変換後 Mammoth + python-docx |
| Excel | `.xlsx` | Spreadsheet Converter（openpyxl） |
| Excel（旧形式） | `.xls` | LibreOffice で `.xlsx` に変換後 openpyxl |
| PowerPoint | `.pptx` | python-pptx |
| PowerPoint（旧形式） | `.ppt` | LibreOffice で `.pptx` に変換後 python-pptx |

### クイックスタート

前提: Docker / Docker Compose

```bash
git clone https://github.com/GPTtang/docforge.git
cd docforge
docker compose up -d --build

# ヘルスチェック
curl http://localhost:8080/api/convert/health
```

### デプロイ設定の推奨

デプロイ時は、次の 2 つの構成を基準にしてください。

| 構成 | CPU / メモリ | PDF Hybrid | `DOCFORGE_PYTHON_WORKERS` | 想定用途 |
|------|--------------|------------|---------------------------|----------|
| 最小構成 | 4 コア / 8 GB | `off` | `1` | Office 文書とテキスト PDF が中心、最小リソースで運用 |
| 推奨構成 | 8 コア以上 / 16 GB 以上 | `docling-fast` | `2` | Office/PDF 混在、スキャン PDF、OCR、複雑レイアウトを含む運用 |

パラメータ調整の目安:

- `DOCFORGE_PYTHON_WORKERS`: 最小構成は `1`、推奨構成は `2`
- `DOCFORGE_OPENDATALOADER_HYBRID`: 最小構成は `off`、推奨構成は `docling-fast`
- `DOCFORGE_OPENDATALOADER_HYBRID_SERVER_ARGS`: 通常は空のままにし、OCR が必要な場合のみ追加

起動例:

```bash
# 推奨構成
DOCFORGE_PYTHON_WORKERS=2 \
DOCFORGE_OPENDATALOADER_HYBRID=docling-fast \
docker compose up -d --build

# 推奨構成 + OCR フラグ
DOCFORGE_PYTHON_WORKERS=2 \
DOCFORGE_OPENDATALOADER_HYBRID=docling-fast \
DOCFORGE_OPENDATALOADER_HYBRID_SERVER_ARGS="--force-ocr --ocr-lang en" \
docker compose up -d --build

# 最小構成
DOCFORGE_PYTHON_WORKERS=1 \
DOCFORGE_OPENDATALOADER_HYBRID=off \
docker compose up -d --build docforge-java docling-service
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

#### 利用可能形式の確認
```bash
curl http://localhost:8080/api/convert/health
```

### Swagger UI

- `http://localhost:8080/`
- `http://localhost:8080/swagger-ui/index.html`
- `http://localhost:8080/v3/api-docs`

### 備考

- 初回起動時はモデル読み込みのため時間がかかる場合があります。
- `model-cache` ボリュームにモデルを保存するため、再起動時のダウンロードを削減できます。
- OCR や難しい PDF が不要な場合は `DOCFORGE_OPENDATALOADER_HYBRID=off` で hybrid を無効化できます。
- 大きなファイルを処理する場合は、メモリと CPU に余裕のある環境を推奨します。

---
## Acknowledgements / 致谢

This project is built upon the following outstanding open-source projects:

本项目基于以下优秀的开源项目构建：

| Project | Author | License | Description |
|---------|--------|---------|-------------|
| [Docling](https://github.com/DS4SD/docling) | IBM Research | MIT | Document parsing library for PDF, Word, Excel, PowerPoint |
| [OpenDataLoader PDF](https://github.com/opendataloader-project/opendataloader-pdf) | opendataloader-project | Apache-2.0 | PDF extraction engine with structured Markdown/JSON output and hybrid backend support |
| [Spring Boot](https://github.com/spring-projects/spring-boot) | VMware / Pivotal | Apache-2.0 | Java framework for building production-ready applications |
| [FastAPI](https://github.com/tiangolo/fastapi) | Sebastián Ramírez | MIT | Modern Python web framework for building APIs |
| [springdoc-openapi](https://github.com/springdoc/springdoc-openapi) | springdoc | Apache-2.0 | OpenAPI 3.0 documentation for Spring Boot |
