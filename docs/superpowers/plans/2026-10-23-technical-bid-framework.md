# 技术标生成系统框架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Windows 本地构建一个使用真实招标资料和真实 DeepSeek 模型的技术标编制闭环。

**Architecture:** FastAPI 通过 REST API 提供项目、资料、事实、目录、章节、检查与导出服务；Vue 3/TypeScript 提供中文工作台。SQLite 保存业务版本，项目文件保存在本地 `data/`；解析、模型调用和 DOCX 通过独立适配器实现。

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, SQLAlchemy, SQLite, httpx, python-docx, pypdf, pytest; Vue 3, TypeScript, Vite, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-23-technical-bid-framework-design.md`

## Global Constraints

- Windows 本地单用户工具；无用户认证、云部署或多租户。
- 产品不提供演示模式、虚构演示项目或固定文本生成；单元测试可以使用隔离测试夹具。
- DeepSeek OpenAI-compatible base URL 默认为 `https://api.deepseek.com`，请求模型名默认为 `deepseek-flash`。
- `DEEPSEEK_API_KEY` 只由后端读取；密钥不进入前端、日志、源码、错误详情或 Git。
- 用户文件按项目保存；DOCX 以段落/表格位置、PDF 以页码保留出处。
- 未确认项目事实不得作为确定事实写入生成内容；冲突必须保留，不能自动择一。
- 人工编辑和重新生成都创建章节新版本；相关事实变化使依赖章节待复核。
- 未核验规范显示“待核验”；未渲染验证的实际页数和目录页码显示未验证。
- OCR、向量检索、规范核验、语义审查、工程计算和页数渲染不伪装成已完成能力。

## Review Focus

- 超大、损坏、扫描型或不支持的上传文件：测试拒绝超限和不支持类型、保留已上传扫描件并标记待处理，不让服务崩溃。Task 3: `test_unsupported_file_rejected_and_empty_pdf_retained`。
- 相互冲突的工期、工程量或目标：测试保留来源和值的冲突，不自动确认。Task 4: `test_conflicting_fact_candidates_remain_unconfirmed`。
- 文件正文中含有要求模型忽略规则的指令：测试提示构造将其作为引用资料而非控制指令。Task 4: `test_source_text_is_marked_untrusted_in_model_context`。
- DeepSeek 密钥缺失、超时、限流或无效 JSON：测试返回可见失败且不创建伪正文或章节版本。Task 5: `test_generation_failure_keeps_chapter_version_unchanged`。
- 章节已经人工修改后项目事实或补遗发生变化：测试保留旧版本并标记待复核。Task 5: `test_fact_change_marks_dependent_chapter_stale_without_overwrite`。

---

### Task 1: Project Scaffold and Configuration

**Files:**
- Create: `.gitignore`, `.env.example`
- Create: `backend/pyproject.toml`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/main.py`
- Create: `backend/tests/test_health.py`
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/main.ts`, `frontend/src/App.vue`

**Interfaces:**
- Produces: `GET /api/health -> {status: "ok"}`; `get_settings() -> Settings`; Vite proxies `/api` to `http://127.0.0.1:8000`.

- [ ] Write `test_health_endpoint` asserting HTTP 200 and exact JSON `{"status":"ok"}`.
- [ ] Run `python -m pytest backend/tests/test_health.py -q`; expected: FAIL because the API app does not exist.
- [ ] Implement the FastAPI entry point, backend settings, Python/Vue dependency manifests, starter Vue shell, and ignores for `.env`, `data/`, `.venv/`, `node_modules/`, and build output.
- [ ] Run `python -m pytest backend/tests/test_health.py -q` and `npm --prefix frontend run build`; expected: both PASS.
- [ ] Commit as `chore: scaffold technical bid application`.

### Task 2: Project Persistence and API

**Files:**
- Create: `backend/app/db.py`, `backend/app/models/project.py`, `backend/app/schemas/project.py`, `backend/app/services/projects.py`, `backend/app/api/projects.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_projects.py`

**Interfaces:**
- Consumes: `get_settings()` and FastAPI app from Task 1.
- Produces: SQLAlchemy `Project`; `POST /api/projects`; `GET /api/projects`; `GET /api/projects/{project_id}`. Project fields: `id`, `code`, `name`, `engineering_type` (`building` or `municipal`), `status`, `target_pages` (default 50, configurable), `facts_version`, `updated_at`.

- [ ] Write `test_project_create_and_list_persist_across_sessions`; assert created fields and that a fresh DB session returns the same project.
- [ ] Run `python -m pytest backend/tests/test_projects.py -q`; expected: FAIL because project persistence is absent.
- [ ] Implement SQLite session management, model creation, request validation, and project CRUD service/routes; use an injectable DB URL so tests use a temporary SQLite file.
- [ ] Run `python -m pytest backend/tests/test_projects.py -q`; expected: PASS, including invalid `engineering_type` rejection.
- [ ] Commit as `feat: add persistent project management`.

### Task 3: Upload Storage and Document Parsing

**Files:**
- Create: `backend/app/models/document.py`, `backend/app/models/parse_block.py`, `backend/app/schemas/document.py`, `backend/app/services/file_storage.py`, `backend/app/services/parsing.py`, `backend/app/adapters/docx_parser.py`, `backend/app/adapters/pdf_parser.py`, `backend/app/api/documents.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_documents.py`, `backend/tests/fixtures/document_factory.py`

**Interfaces:**
- Consumes: `Project`, DB session, configured `DATA_DIR` from Tasks 1-2.
- Produces: `SourceDocument` and ordered `ParseBlock` records; `POST /api/projects/{project_id}/documents`; `GET /api/projects/{project_id}/documents`; `POST /api/documents/{document_id}/parse`.
- Document states: `uploaded`, `parsing`, `parsed`, `needs_review`, `failed`; block locations use DOCX paragraph/table indexes or PDF page number.

- [ ] Write `test_docx_preserves_paragraph_table_order_and_locations` and assert each extracted block points to its DOCX paragraph/table index.
- [ ] Write `test_pdf_blocks_keep_page_number` and assert every extracted text block identifies its source page.
- [ ] Write `test_unsupported_extension_is_rejected` and `test_file_over_configured_limit_is_rejected` with the exact configured maximum of `104857600` bytes.
- [ ] Write `test_scanned_pdf_keeps_source_and_needs_review` and assert the empty-text PDF remains stored with status `needs_review`.
- [ ] Run `python -m pytest backend/tests/test_documents.py -q`; expected: FAIL because upload and parser adapters are absent.
- [ ] Implement extension/size validation using configurable `MAX_UPLOAD_BYTES=104857600`, generated storage names under `data/projects/{project_id}/uploads/`, SHA-256 metadata, DOCX paragraph/table order and PDF page extraction, and explicit partial/failed states.
- [ ] Run `python -m pytest backend/tests/test_documents.py -q`; expected: PASS; test fixtures are generated under pytest temporary directories and are not installed as demo files.
- [ ] Commit as `feat: upload and parse tender documents`.

### Task 4: DeepSeek Adapter, Facts, Requirements, and Knowledge Metadata

**Files:**
- Create: `backend/app/adapters/deepseek.py`, `backend/app/models/fact.py`, `backend/app/models/requirement.py`, `backend/app/models/knowledge_item.py`, `backend/app/models/job.py`, `backend/app/schemas/extraction.py`, `backend/app/services/extraction.py`, `backend/app/services/knowledge.py`, `backend/app/services/jobs.py`, `backend/app/api/extraction.py`, `backend/app/api/facts.py`, `backend/app/api/requirements.py`, `backend/app/api/knowledge.py`, `backend/app/api/jobs.py`
- Modify: `backend/app/main.py`, `backend/app/config.py`
- Test: `backend/tests/test_deepseek.py`, `backend/tests/test_extraction.py`, `backend/tests/test_knowledge.py`

**Interfaces:**
- Consumes: `ParseBlock`, project/document services, and `Settings` from Tasks 1-3.
- Produces: async `DeepSeekClient.complete_json(system: str, payload: dict, response_model: type[BaseModel]) -> BaseModel`; `POST /api/projects/{project_id}/extract` returning a persisted `Job`; `GET /api/jobs/{job_id}`; fact/requirement extraction output with source block IDs; `GET/PUT /api/projects/{project_id}/facts`; `POST /api/projects/{project_id}/facts/confirm`; `GET/PUT /api/projects/{project_id}/requirements`; knowledge-file upload and item import/update/list/search routes under `data/knowledge/`.
- DeepSeek defaults: base URL `https://api.deepseek.com`, model `deepseek-flash`; key from `DEEPSEEK_API_KEY` only.

- [ ] Write `test_missing_key_returns_configuration_error`, `test_http_timeout_is_reported`, and `test_invalid_model_json_fails_without_fallback`.
- [ ] Write `test_unknown_source_block_id_is_rejected`, `test_conflicting_fact_candidates_remain_unconfirmed`, and `test_source_text_is_marked_untrusted_in_model_context`.
- [ ] Write `test_absent_fact_stays_empty`, `test_extraction_job_persists_status`, `test_cross_project_knowledge_is_not_returned_as_project_facts`, and `test_imported_standard_defaults_to_pending_verification`.
- [ ] Run `python -m pytest backend/tests/test_deepseek.py backend/tests/test_extraction.py backend/tests/test_knowledge.py -q`; expected: FAIL because the adapter and records do not exist.
- [ ] Implement bounded HTTP timeout/retry, Pydantic output validation, source-reference validation, missing/conflicting facts without auto-confirmation, user confirmation/version increment, knowledge metadata including `verification_status="待核验"`, and keyword search. Do not include any fixed extraction response in runtime code.
- [ ] Run the three test modules; expected: PASS, with model calls replaced only at the HTTP transport boundary in tests.
- [ ] Commit as `feat: extract sourced facts and requirements with DeepSeek`.

### Task 5: Templates, Outline, Chapter Versions, and Generation Jobs

**Files:**
- Create: `backend/app/models/template.py`, `backend/app/models/chapter.py`, `backend/app/schemas/chapter.py`, `backend/app/services/outlines.py`, `backend/app/services/chapters.py`, `backend/app/services/generation.py`, `backend/app/api/outlines.py`, `backend/app/api/chapters.py`
- Modify: `backend/app/models/job.py`, `backend/app/services/jobs.py`, `backend/app/api/jobs.py`
- Modify: `backend/app/main.py`, `backend/app/models/fact.py`, `backend/app/services/extraction.py`
- Test: `backend/tests/test_chapters.py`, `backend/tests/test_generation.py`, `backend/tests/test_jobs.py`

**Interfaces:**
- Consumes: `DeepSeekClient`, confirmed facts, requirements, knowledge search, and project models from Tasks 1-4.
- Produces: `GET/PUT /api/projects/{project_id}/outline`; `GET/PUT /api/projects/{project_id}/chapters`; `POST /api/chapters/{chapter_id}/generate`; `GET /api/jobs/{job_id}`; `POST /api/jobs/{job_id}/retry`.
- Chapter content is ordered JSON blocks: `{type:"paragraph", text, heading_level?}` or `{type:"table", rows:string[][]}`. Every save or successful generation appends a `ChapterVersion` with source, fact version, citations, and open issues.
- Job state is `queued|running|succeeded|failed|interrupted`; retry reuses the job/chapter association and never duplicates the chapter.

- [ ] Write `test_building_and_municipal_starter_templates_are_distinct` and `test_outline_edits_persist`; starter templates contain editable headings only, with no fabricated body text.
- [ ] Write `test_human_edit_appends_chapter_version`.
- [ ] Write `test_generation_uses_only_confirmed_facts_and_cited_knowledge` and `test_generation_failure_keeps_chapter_version_unchanged`.
- [ ] Write `test_retry_does_not_duplicate_chapter_or_export` and `test_fact_change_marks_dependent_chapter_stale_without_overwrite`.
- [ ] Run `python -m pytest backend/tests/test_chapters.py backend/tests/test_generation.py backend/tests/test_jobs.py -q`; expected: FAIL because chapter/job services do not exist.
- [ ] Implement distinct building and municipal starter templates with editable heading skeletons and no body text, outline persistence, JSON block validation, chapter versioning, durable job status and startup interruption recovery, generation input packs, and DeepSeek calls through the Task 4 adapter. Missing required facts become open issues; they are not fabricated.
- [ ] Run the three test modules; expected: PASS; model failure must leave current chapter version unchanged.
- [ ] Commit as `feat: generate versioned chapters with durable jobs`.

### Task 6: Deterministic Checks and Editable DOCX Export

**Files:**
- Create: `backend/app/models/review_issue.py`, `backend/app/models/export.py`, `backend/app/services/checks.py`, `backend/app/adapters/docx_export.py`, `backend/app/api/checks.py`, `backend/app/api/exports.py`
- Modify: `backend/app/main.py`, `backend/app/models/chapter.py`
- Test: `backend/tests/test_checks.py`, `backend/tests/test_exports.py`

**Interfaces:**
- Consumes: project facts, requirements, template/outline, chapter versions, knowledge status, and source citations from Tasks 1-5.
- Produces: `POST /api/projects/{project_id}/checks/run`; `GET /api/projects/{project_id}/issues`; `POST /api/projects/{project_id}/exports`; `GET /api/exports/{export_id}/download`.
- Check result states: `passed`, `issues_found`, `not_checked`, `needs_human_judgment`; export status defaults to `审核稿` and page count to `未验证`.

- [ ] Write `test_project_name_and_duration_mismatch_is_reported` and `test_requirement_mapping_does_not_mark_response_complete`.
- [ ] Write `test_missing_required_chapter_and_placeholder_are_reported`, `test_missing_citation_and_unverified_standard_are_issues`, and `test_stale_chapter_version_is_reported`.
- [ ] Write `test_docx_contains_editable_paragraph_and_table_blocks` and `test_export_is_audit_draft_with_unverified_pages`; assert exported DOCX reopens and records the exact chapter version IDs.
- [ ] Run `python -m pytest backend/tests/test_checks.py backend/tests/test_exports.py -q`; expected: FAIL because checks and export are absent.
- [ ] Implement deterministic checks and python-docx rendering of editable blocks; add a TOC field with update-on-open and record pagination as unverified.
- [ ] Run the two test modules; expected: PASS, including loading each export with `python-docx` and checking its chapter version IDs.
- [ ] Commit as `feat: review projects and export editable docx drafts`.

### Task 7: Vue Project Workflow

**Files:**
- Create: `frontend/src/api/client.ts`, `frontend/src/api/projects.ts`, `frontend/src/api/documents.ts`, `frontend/src/api/extraction.ts`, `frontend/src/api/facts.ts`, `frontend/src/api/requirements.ts`, `frontend/src/api/outline.ts`, `frontend/src/api/chapters.ts`, `frontend/src/api/jobs.ts`, `frontend/src/api/knowledge.ts`, `frontend/src/api/reviews.ts`, `frontend/src/api/exports.ts`, `frontend/src/pages/ProjectListView.vue`, `frontend/src/pages/ProjectWorkspaceView.vue`, `frontend/src/components/ProjectForm.vue`, `frontend/src/components/DocumentUpload.vue`, `frontend/src/components/FactTable.vue`, `frontend/src/components/RequirementTable.vue`, `frontend/src/components/OutlineEditor.vue`, `frontend/src/components/ChapterEditor.vue`, `frontend/src/components/IssueList.vue`, `frontend/src/components/KnowledgePanel.vue`
- Modify: `frontend/src/App.vue`, `frontend/src/main.ts`, `frontend/package.json`
- Test: `frontend/src/api/client.test.ts`, `frontend/src/components/ChapterEditor.test.ts`

**Interfaces:**
- Consumes: REST API routes from Tasks 2-6.
- Produces: a Chinese project list and workspace that call the real backend for create/upload/parse/extract/edit/confirm/outline/save/generate/check/export/download; displays provenance, source locations, failures, stale state, manual versions, unverified capabilities, and the configured DeepSeek model/material scope before generation.

- [ ] Write `client.test.ts` cases proving API error details are visible without exposing secrets, and extraction polls the returned job.
- [ ] Write `ChapterEditor.test.ts` proving paragraph/table edits preserve block data when saved.
- [ ] Run `npm --prefix frontend test -- --run`; expected: FAIL because API clients and views are absent.
- [ ] Implement project list and workspace screens with working upload, confirmed fact editing, requirements/outline editing, chapter block editor, knowledge file import and metadata, check status, task progress and DOCX download.
- [ ] Run `npm --prefix frontend test -- --run` and `npm --prefix frontend run build`; expected: PASS.
- [ ] Commit as `feat: build Chinese tender preparation workspace`.

### Task 8: Windows Startup, Documentation, and Acceptance

**Files:**
- Create: `run.ps1`, `README.md`, `backend/tests/test_workflow.py`
- Modify: `.env.example`, `backend/app/config.py`, `frontend/vite.config.ts`

**Interfaces:**
- Consumes: completed backend/frontend workflow and `.env.example` from Tasks 1-7.
- Produces: one-command local startup at `http://127.0.0.1:5173` in development; README steps for setup, DeepSeek configuration, test path, and capability limits; API integration test covering project through DOCX download.

- [ ] Write `test_real_workflow_project_to_docx` using temporary DB/files and mocked DeepSeek HTTP transport; assert project, upload, parsed source location, confirmed fact, edited outline, generated chapter version, issue result, and downloadable DOCX reopened by `python-docx`.
- [ ] Run `python -m pytest backend/tests/test_workflow.py -q`; expected: FAIL because the cross-module workflow test is absent.
- [ ] Implement PowerShell startup/cleanup, health wait, Vite API proxy, Chinese README, `.env` exclusion, and the integration test. Select port 5173 or the next free local port. Do not add user-facing demo files.
- [ ] Run `python -m pytest backend/tests -q`, `npm --prefix frontend test -- --run`, and `npm --prefix frontend run build`; expected: all PASS.
- [ ] Run one live DeepSeek smoke request with `max_tokens=64` using the local environment key; verify the configured `deepseek-flash` endpoint and confirm the secret is absent from logs and Git status.
- [ ] Commit as `docs: document local startup and verify end-to-end workflow`.

## Self-Review Record

- Spec coverage: Tasks 1-8 cover the Windows/local architecture, project CRUD, file upload and provenance, facts/requirements, knowledge metadata, templates/outline, chapter generation/versioning, durable jobs, deterministic checks, editable DOCX, Chinese UI, startup, documentation, and acceptance path. Deferred OCR, vector retrieval, standards verification, semantic review, engineering calculations, and real pagination remain explicitly outside the implementation.
- Step scan: Each task uses a failing test, implementation, passing verification, and commit. Commands include expected outcomes; interfaces are named before later tasks consume them.
- Type consistency: Project IDs, source block IDs, `ChapterVersion` IDs, job IDs, chapter JSON blocks, check states, and export IDs are shared across API/service boundaries as declared.
- Review Focus tests are assigned to Tasks 3, 4, and 5. Cross-module document-to-DOCX behavior is additionally exercised in Task 8. A second pass added the extraction job route, separated file rejection from retained scan states, fixed a configurable 100 MiB upload default, included knowledge-file import and project name/duration checks, and clarified starter templates as structural headings only.
- Proportion: The plan keeps implementation choices and checks concise while retaining exact paths, route names, settings, and test commands needed by a new implementer.
