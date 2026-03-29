# DocForge

> One API for Office and PDF -> clean Markdown / JSON for LLM workflows

**[中文](#中文) | [English](#english) | [日本語](#日本語)**

---

## 中文

### DocForge 解决什么问题

做 AI 应用开发，最烦的往往不是模型调用，而是数据预处理。

- `PDF`、`Word`、`Excel`、`PowerPoint` 格式各不相同，要接不同解析库
- 表格容易错位，段落顺序容易乱，扫描 PDF 没有可直接提取的文字
- 想给 LLM、RAG、Agent 喂“干净文本”，结果先被文档解析工程拖住

DocForge 专门解决这个问题：

- 输入任意常见 Office 文档或 PDF
- 统一走一个 API 网关
- 返回适合下游 LLM 使用的 `Markdown` 或 `JSON`

目标不是做“文档预览器”，而是做“面向 AI 应用的数据入口层”。

### 它能做什么

支持的输入格式：

- `PDF`
- `DOCX` / `DOC`
- `XLSX` / `XLS`
- `PPTX` / `PPT`

支持的输出格式：

- `Markdown`
- `JSON`

当前引擎分流：

| 输入类型 | 当前实现 |
|---|---|
| `PDF` | `OpenDataLoader PDF` |
| `PDF` 扫描件 / OCR / 复杂页面 | `OpenDataLoader PDF + optional hybrid Docling backend` |
| `DOCX / DOC` | `Mammoth + python-docx` |
| `PPTX / PPT` | `python-pptx` |
| `XLSX / XLS` | `openpyxl` |
| 旧 Office 格式 | 先走 `LibreOffice` 转新格式，再进入对应转换器 |

### 技术结构

DocForge 不是“单一解析库”，而是“网关 + 多引擎路由”架构：

```text
Client
  -> Java Spring Boot gateway
  -> Python FastAPI conversion service
  -> Best local engine by file type
  -> Markdown / JSON
```

运行时有 3 个服务：

| 服务 | 作用 | 端口 |
|---|---|---|
| `docforge-java` | 对外 API 网关、Swagger UI | `8080`，宿主机暴露 |
| `docforge-python` | 主转换服务、格式路由 | `8000`，仅容器内部 |
| `opendataloader-hybrid` | 可选 PDF hybrid backend | `5002`，仅容器内部 |

真实请求链路：

- `PDF`：`client -> java -> python -> OpenDataLoader PDF`
- `PDF + hybrid`：`client -> java -> python -> opendataloader-hybrid`
- `DOCX/DOC`：`client -> java -> python -> Mammoth + python-docx`
- `PPTX/PPT`：`client -> java -> python -> python-pptx`
- `XLSX/XLS`：`client -> java -> python -> openpyxl`

### 项目结构

```text
docforge/
├── README.md
├── AGENTS.md
├── docker-compose.yml
├── java-service/
│   ├── Dockerfile
│   ├── pom.xml
│   └── src/main/java/com/docforge/
│       ├── controller/
│       │   ├── DocForgeController.java
│       │   └── HomeController.java
│       ├── service/
│       │   └── DocConvertService.java
│       ├── model/
│       │   └── ConvertResponse.java
│       ├── util/
│       │   └── MultipartInputStreamFileResource.java
│       └── config/
│           ├── RestTemplateConfig.java
│           └── SwaggerConfig.java
├── python-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── converters/
│   │   ├── opendataloader_converter.py
│   │   ├── docx_converter.py
│   │   ├── pptx_converter.py
│   │   ├── spreadsheet_converter.py
│   │   └── office_converter.py
│   └── tests/
├── scripts/
│   ├── generate_test_documents.py
│   └── run_benchmark.py
└── test-documents/
```

### 如何部署

前置条件：

- Docker
- Docker Compose

直接启动完整栈：

```bash
git clone https://github.com/GPTtang/docforge.git
cd docforge
docker compose up -d --build
```

检查服务状态：

```bash
docker compose ps
curl http://localhost:8080/api/convert/health
```

如果一切正常，你会得到：

```json
{
  "java": "ok",
  "python": "ok"
}
```

### 部署建议

| 配置档位 | CPU / 内存 | `DOCFORGE_PYTHON_WORKERS` | `DOCFORGE_OPENDATALOADER_HYBRID` | 适用场景 |
|---|---|---:|---|---|
| 最低配置 | 4 核 / 8 GB | `1` | `off` | Office 文档、文字版 PDF |
| 建议配置 | 8 核以上 / 16 GB 以上 | `2` | `docling-fast` | 混合 PDF / Office、扫描件、OCR、复杂版面 |

启动示例：

```bash
# 建议配置
DOCFORGE_PYTHON_WORKERS=2 \
DOCFORGE_OPENDATALOADER_HYBRID=docling-fast \
docker compose up -d --build

# 最低配置
DOCFORGE_PYTHON_WORKERS=1 \
DOCFORGE_OPENDATALOADER_HYBRID=off \
docker compose up -d --build docforge-java docling-service
```

说明：

- `model-cache` Docker volume 会缓存 Docling / OCR 模型
- `8000` 和 `5002` 默认不对宿主机暴露，外部统一通过 `8080`
- 浏览器访问 `http://localhost:8080/` 会自动跳转到 Swagger UI

### 如何使用

Swagger UI：

- `http://localhost:8080/`
- `http://localhost:8080/swagger-ui/index.html`
- `http://localhost:8080/v3/api-docs`

#### 转 Markdown

```bash
curl -X POST http://localhost:8080/api/convert/markdown \
  -F "file=@test-documents/word/docx/unit_test_formatting.docx"
```

返回结构：

```json
{
  "filename": "unit_test_formatting.docx",
  "markdown": "# ...",
  "status": "success"
}
```

#### 转 JSON

```bash
curl -X POST http://localhost:8080/api/convert/json \
  -F "file=@test-documents/pdf/text/multi_page.pdf"
```

返回结构：

```json
{
  "filename": "multi_page.pdf",
  "data": { },
  "status": "success"
}
```

#### 健康检查

```bash
curl http://localhost:8080/api/convert/health
```

### 适合什么场景

- 给 `LLM` 喂干净 Markdown
- 给 `RAG` 构建结构化 JSON
- 做企业知识库文档预处理
- 做 PDF / Office 批量抽取
- 做 Agent 工作流的文档入口

### 本地开发

```bash
# Python service
cd python-service
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Java gateway
cd java-service
mvn spring-boot:run
```

本地开发时，`java-service/src/main/resources/application.yml` 中的：

```yaml
docforge:
  python:
    service-url: http://localhost:8000
```

只用于“本地单独启动 Java + Python”的场景，不是 Docker 部署地址。

### 测试

```bash
pytest -q python-service/tests
cd java-service && mvn test
```

---

## English

### What problem does DocForge solve?

The painful part of AI application development is often not model calling. It is document preprocessing.

- PDFs, Word files, Excel sheets, and PowerPoint slides all need different parsers
- Tables drift, reading order breaks, and scanned PDFs contain no usable text
- Teams want clean Markdown or JSON for LLMs, RAG, and agents, but end up building parser glue code instead

DocForge solves that problem:

- upload common Office files or PDFs
- call one API gateway
- receive clean `Markdown` or `JSON` for downstream AI workflows

### Current architecture

- `docforge-java`: public API gateway on `8080`
- `docforge-python`: internal conversion service on `8000`
- `opendataloader-hybrid`: optional internal PDF hybrid backend on `5002`

Routing by file type:

| Input | Engine |
|---|---|
| `PDF` | `OpenDataLoader PDF` |
| scanned / complex `PDF` | `OpenDataLoader PDF + optional hybrid Docling backend` |
| `DOCX / DOC` | `Mammoth + python-docx` |
| `PPTX / PPT` | `python-pptx` |
| `XLSX / XLS` | `openpyxl` |

### Project structure

Key directories:

- `java-service/`: Spring Boot gateway
- `python-service/`: FastAPI conversion pipelines
- `scripts/`: fixture generation and benchmark helpers
- `test-documents/`: regression fixtures
- `docker-compose.yml`: deployment entrypoint

### Deploy

```bash
git clone https://github.com/GPTtang/docforge.git
cd docforge
docker compose up -d --build
curl http://localhost:8080/api/convert/health
```

Gateway and docs:

- `http://localhost:8080/`
- `http://localhost:8080/swagger-ui/index.html`
- `http://localhost:8080/v3/api-docs`

### Use

Convert to Markdown:

```bash
curl -X POST http://localhost:8080/api/convert/markdown \
  -F "file=@document.pdf"
```

Convert to JSON:

```bash
curl -X POST http://localhost:8080/api/convert/json \
  -F "file=@document.docx"
```

Health check:

```bash
curl http://localhost:8080/api/convert/health
```

### Deployment profiles

| Profile | CPU / RAM | Workers | Hybrid |
|---|---|---:|---|
| Minimum | 4 cores / 8 GB | `1` | `off` |
| Recommended | 8+ cores / 16+ GB | `2` | `docling-fast` |

---

## 日本語

### DocForge が解決する課題

AI アプリ開発で本当に面倒なのは、モデル呼び出しよりも文書前処理です。

- PDF、Word、Excel、PowerPoint はそれぞれ別の処理系が必要
- 表が崩れる、段落順が乱れる、スキャン PDF には抽出できる文字がない
- LLM や RAG に渡したいのはきれいな Markdown / JSON なのに、実際は文書解析の実装に時間を取られる

DocForge はその問題を解決します。

- Office 文書や PDF をアップロード
- 1 つの API ゲートウェイを呼ぶ
- LLM 向けに使いやすい `Markdown` / `JSON` を返す

### 現在の構成

- `docforge-java`: 公開 API ゲートウェイ (`8080`)
- `docforge-python`: 内部変換サービス (`8000`)
- `opendataloader-hybrid`: 任意の PDF hybrid backend (`5002`)

形式ごとのエンジン:

| 入力 | エンジン |
|---|---|
| `PDF` | `OpenDataLoader PDF` |
| スキャン / 複雑 `PDF` | `OpenDataLoader PDF + optional hybrid Docling backend` |
| `DOCX / DOC` | `Mammoth + python-docx` |
| `PPTX / PPT` | `python-pptx` |
| `XLSX / XLS` | `openpyxl` |

### デプロイ

```bash
git clone https://github.com/GPTtang/docforge.git
cd docforge
docker compose up -d --build
curl http://localhost:8080/api/convert/health
```

利用入口:

- `http://localhost:8080/`
- `http://localhost:8080/swagger-ui/index.html`
- `http://localhost:8080/v3/api-docs`

### API 例

```bash
curl -X POST http://localhost:8080/api/convert/markdown \
  -F "file=@document.pdf"
```

```bash
curl -X POST http://localhost:8080/api/convert/json \
  -F "file=@document.docx"
```

---

## Acknowledgements

DocForge builds on these open-source projects:

| Project | License | Role in DocForge |
|---|---|---|
| [OpenDataLoader PDF](https://github.com/opendataloader-project/opendataloader-pdf) | Apache-2.0 | PDF extraction engine |
| [Docling](https://github.com/DS4SD/docling) | MIT | Optional PDF hybrid backend |
| [Spring Boot](https://github.com/spring-projects/spring-boot) | Apache-2.0 | Java API gateway |
| [FastAPI](https://github.com/tiangolo/fastapi) | MIT | Python conversion service |
| [Mammoth](https://github.com/mwilliamson/python-mammoth) | BSD-2-Clause | DOCX to Markdown/HTML conversion |
| [python-docx](https://python-docx.readthedocs.io/) | MIT | DOCX structure extraction |
| [python-pptx](https://python-pptx.readthedocs.io/) | MIT | PPTX structure extraction |
| [openpyxl](https://openpyxl.readthedocs.io/) | MIT | XLSX parsing |
