# Repository Guidelines

## Project Structure & Module Organization
DocForge is a gateway + local-engine document conversion platform. `java-service/` hosts the Spring Boot gateway that exposes `/api/convert/*`, `/api/convert/health`, and redirects `/` to Swagger UI. `python-service/` contains the FastAPI backend and the actual conversion pipelines orchestrated by `main.py`. Converter modules are split by format under `python-service/converters/`:
- `opendataloader_converter.py` for PDF
- `docx_converter.py` for DOCX
- `pptx_converter.py` for PPTX
- `spreadsheet_converter.py` for XLSX
- `office_converter.py` for legacy Office pre-conversion via LibreOffice

Shared automation lives in `scripts/`, especially `generate_test_documents.py` and `run_benchmark.py`. Regression fixtures live under `test-documents/`. Docker orchestration is defined in `docker-compose.yml`.

## Runtime Architecture
The deployed stack has three services:
- `docforge-java`: public gateway on host port `8080`
- `docling-service`: internal Python conversion service on container port `8000`
- `opendataloader-hybrid`: optional internal PDF hybrid backend on container port `5002`

Current conversion routing:
- `PDF` -> `OpenDataLoader PDF`
- `PDF` with hybrid enabled -> `OpenDataLoader PDF + opendataloader-hybrid`
- `DOCX/DOC` -> `Mammoth + python-docx`
- `PPTX/PPT` -> `python-pptx`
- `XLSX/XLS` -> `openpyxl`
- Legacy `.doc/.ppt/.xls` first convert through LibreOffice, then route to the modern-format converter

Do not reintroduce `marker` or `docling` as the default Office pipeline without an explicit change request. `Docling` is only the optional PDF hybrid backend in the current architecture.

## Build, Test, and Development Commands
- `docker compose up -d --build`: build and start the full stack
- `docker compose ps`: inspect service health/status
- `curl http://localhost:8080/api/convert/health`: gateway health check
- `cd python-service && pip install -r requirements.txt && uvicorn main:app --reload --host 0.0.0.0 --port 8000`: run the Python service locally
- `cd java-service && mvn spring-boot:run`: run the Java gateway locally
- `cd java-service && mvn test`: run JVM tests
- `pytest -q python-service/tests`: run Python tests
- `python scripts/run_benchmark.py --samples ... --output benchmark-results.json`: run in-process conversion benchmarks

When validating end-to-end behavior, prefer testing through the Java gateway on `http://localhost:8080` rather than calling the Python service directly.

## Coding Style & Naming Conventions
Python code follows PEP 8 with 4-space indents, type hints, and stateless converter modules where practical. Prefer explicit helper functions over embedding routing logic in endpoint handlers. Keep converter filenames in `lower_snake_case`.

Java code follows standard Spring conventions:
- PascalCase class names
- camelCase methods
- REST controllers under `controller/`
- service orchestration under `service/`

YAML and Markdown should stay compact and explicit. In README/API docs, document only behavior that actually exists in the codebase.

## Testing Guidelines
Python changes should include pytest coverage in `python-service/tests/`. Cover:
- converter behavior
- unsupported extension handling
- gateway error mapping
- health and format endpoints
- real fixture-based cases when practical

Java changes should include JUnit tests in `java-service/src/test/java/`, especially for:
- controller response shape
- downstream error handling
- root path / Swagger behavior

Use `test-documents/` fixtures for regression coverage. If you replace binary fixtures, prefer regeneratable fixtures plus a generator script rather than opaque hand-edited binaries.

## Documentation Guidelines
Keep `README.md` aligned with the actual running system:
- root path `/` redirects to Swagger UI
- only `8080` is host-exposed in Docker by default
- `8000` and `5002` are internal-only container ports
- API examples must match actual response fields

If runtime behavior changes, update README in the same change set.

## Commit & Pull Request Guidelines
Follow Conventional Commits such as `feat:`, `fix:`, `docs:`, and `chore:`. Keep commits focused. When changes span both services, the commit message should still describe one coherent user-facing outcome.

Pull requests should include:
- concise summary of what changed
- verification commands
- affected document types or pipelines
- any deployment or migration notes

If the worktree contains unrelated local files, do not stage them implicitly. Stage explicit paths.
