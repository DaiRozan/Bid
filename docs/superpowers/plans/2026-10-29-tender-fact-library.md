# Tender Fact Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import real nested tender archives, read drawings/BOQ, publish immutable Markdown facts and constrain generation to those facts.

**Architecture:** Keep original SourceDocument and ParseBlock contracts. Add independent material-analysis and fact-snapshot records, focused file adapters, and a single snapshot input/validation path shared by generation and retries. CAD measurements remain review evidence; adopted project quantities come from explicit supplements and BOQ.

**Tech Stack:** Python 3.11+, FastAPI/SQLite, ZIP/Windows tar, LibreOffice, ODA, ezdxf, xlrd/openpyxl, Vue 3.

**Spec:** docs/superpowers/specs/2026-10-29-tender-fact-library-design.md

## Global Constraints

- Latest explicit supplements and BOQ supply adopted quantities; CAD calculations only review them.
- Published version files are immutable, checksum checked and project scoped.
- Keep all original sources; reimport/reparse never erases confirmed facts or snapshots.
- No invented units, thickness, heights or duplicate-view takeoff totals.
- User authorized autonomous execution and selecting/downloading DWG environment; execute inline in the supplied checkout on a feature branch so its existing runtime/data remain usable.

## Review Focus

- Archive names and links must not escape extraction roots, including Windows paths and RAR metadata.
- XLS header continuations and repeated unit projects must not merge different BOQ items or fill blank quantities with zero.
- CAD view duplication, nested transformed blocks and missing units must not produce adopted quantities.
- Supplement edits must retain target evidence, user adoption and complete override lineage.
- Snapshot tampering, cross-project references and retry routes must not bypass generation constraints.

### Task 1: Archive import and source parsing

**Files:** adapters/archives.py, adapters/legacy_doc.py, services/material_import.py, services/file_storage.py, services/parsing.py, api/documents.py, config.py, pyproject.toml; tests/test_material_import.py.
**Interfaces:** import_materials(session, project_id, document) returns member documents with archive provenance; parse_document supports all accepted standalone formats.
- [ ] Write tests: nested zip child PDF/DOCX persists, repeated import stable, traversal/symlink/depth/expanded size rejected, unsupported member is visible.
- [ ] Run `python -m pytest tests/test_material_import.py -q`; expected failures on missing import support.
- [ ] Implement bounded archive walk with full preflight and DOC adapter; add indexed source provenance records without altering legacy columns.
- [ ] Run test file and complete suite; expected all pass. Commit deliverable.

### Task 2: BOQ and CAD adapters

**Files:** adapters/boq.py, adapters/cad.py, adapters/cad_geometry.py, models/material.py, services/material_analysis.py; tests/test_boq.py, tests/test_cad.py.
**Interfaces:** analyze_boq(path) / analyze_cad(path) return JSON-serializable records, source locations, warnings and measurements. analyze_material(session, document) persists these records and stable ParseBlock evidence.
- [ ] Write real XLSX and DXF fixture tests, using literal hand-calculated expected 6 m2 area, transformed block counts and 12 m3 explicit-height volume; test missing units and ambiguous view warnings.
- [ ] Run named tests; expected fail until adapters exist.
- [ ] Implement source-driven parsing and install ODA from official source, verify installer signature/hash and a real DWG conversion.
- [ ] Verify real XLS 31 sheet/representative rows; run suite; commit deliverable.

### Task 3: Markdown draft, supplements and immutable snapshots

**Files:** models/fact_snapshot.py, services/fact_library.py, services/fact_adoption.py, api/fact_library.py, db.py, main.py; tests/test_fact_library.py.
**Interfaces:** build_draft(session, project) returns adopted candidates and review evidence; publish_snapshot(session, project) returns version/manifest; load_snapshot(session, project) verifies digests and returns authoritative adopted facts. Explicit overrides require source block IDs and existing target IDs.
- [ ] Test publication, reimport immutability, MD checksums, cross-project IDs, explicit source override and provenance, empty publication rejection.
- [ ] Run tests red, implement draft/override/publication/read and source-level Markdown views.
- [ ] Preserve confirmed facts and requirements during AI extraction; test repeating extraction cannot wipe them.
- [ ] Run suite, commit deliverable.

### Task 4: Generation from published facts

**Files:** services/generation.py, services/generation_guard.py, api/chapters.py, api/jobs.py, adapters/deepseek.py, tests/test_generation.py, tests/test_deepseek.py, tests/test_jobs.py, tests/test_workflow.py.
**Interfaces:** run_generation(session, project, chapter) and validate_generated(snapshot, generated, permitted_ids) shared across generate/retry; project values referenced as typed fact parts, resolved from snapshot only. Generic method parts use an approved vocabulary.
- [ ] Test missing snapshot rejection, stale draft ignored, unknown/cross-project fact rejection, raw unsupported number rejection, typed body validation, retry same gate, JSON-only response prompt/schema.
- [ ] Run tests red. Implement guards and schema guidance; adapt old tests by publishing controlled facts.
- [ ] Run full suite and isolated real model short chapter check. Commit deliverable.

### Task 5: Material/fact-library UI and real acceptance

**Files:** frontend/src/api/documents.ts, api/factLibrary.ts, components/DocumentUpload.vue, components/FactLibraryPanel.vue, pages/ProjectWorkspaceView.vue, README.md, scripts/verify_tender.py.
- [ ] Test UI/API view transformations where behavior matters. Implement file tree/status, analysis, Markdown preview, adoption and publication, current snapshot status and generation prerequisites.
- [ ] Run `npm run test -- --run` and `npm run build`; expected pass.
- [ ] Import the real archive through application API into a marked acceptance project; retain report and complete material/MD outputs; list CAD calculations and any unresolved interpretation honestly.
- [ ] Verify backend health/proxy/browser, run full tests, commit. Dispatch independent final code reviewer per requesting-code-review skill; fix important findings with RED/GREEN tests and record results.

## Execution ledger

- 2026-10-29: User approved design and explicitly authorized choosing/installing DWG tools and autonomous execution. No further routine approval gates; source sample remains untouched.
- Task 1: complete, fd88e59; backend suite 33 passed. Original archive members use generated storage names, with separate intact archive paths.
- Task 2: complete, 272e230; backend suite 39 passed. Official ODA package SHA256 0E3FAC3B3C2486CC40BF1D13545EB422786AA5623C90F0B72FCF081085212AAB, Authenticode Valid / OPEN DESIGN ALLIANCE. System installation lacked administrator rights; official administrative extraction to the user's LocalAppData succeeded; real DWG conversion verified.
- Task 3: complete, 8e00505; backend suite 44 passed, including chronological explicit supplement override and retained source chain.
- Task 4: complete, e8ad0fd; backend suite 49 passed. Real model generated HTTP 200 in 9.62 seconds from immutable facts; unknown references and unreferenced project digits rejected in tests.
- Ruling: Keep development in the supplied checkout on codex/tender-fact-library, following the user's autonomous execution instruction and preserving its usable installed dependencies/data. Cost if wrong: changes are visible in this checkout rather than isolated in another directory; commits preserve review/revert history.
- Ruling: Store full CAD analysis in checksummed compressed JSON outside SQLite, with bounded previews and all original text retained. The real archive initially produced about 900 MB of redundant JSON in SQLite. Cost if wrong: backup/move must include data/projects, not only the database; the snapshot manifest includes copies and checksums.
- Task 5: UI and reusable real acceptance script implemented; initial frontend 3 tests and Vite build passed, backend 49 tests passed. Real archive: 17 source documents, 8 DWG, 31 BOQ sheets, 1096 independently counted BOQ items (including 29 ZB-prefixed items), 51 Markdown files.
- 2026-11-03 Final review: one independent reviewer completed the whole branch. Eight Important findings entered one fix pass; no second reviewer dispatched.
- Final: fixed supplement negation/questions/undated changes and partial numeric parsing — test_supplement_only_adopts_complete_affirmative_dated_quantities RED→GREEN (5 cases).
- Final: fixed invented nonnumeric project properties — test_legacy_free_text_cannot_smuggle_unfounded_project_properties RED→GREEN; model output now uses typed references plus a closed vocabulary of generic methods. test_valid_typed_project_reference_is_rendered_from_snapshot RED→GREEN.
- Final: fixed BOQ scope changes, reordered/repeated headers and feature continuation rows — test_boq_scope_changes_and_feature_continuations_retain_all_rows RED→GREEN.
- Final: fixed byte-identical workbook duplication and retained all archive occurrences — test_duplicate_archive_workbooks_have_one_fact_and_all_occurrences RED→GREEN.
- Final: fixed manual adoption's original evidence lineage and contradictory structured quantities — test_manual_override_preserves_original_evidence_and_consistent_adopted_quantity RED→GREEN.
- Final: fixed MINSERT array undercounts and per-cell provenance — test_multi_insert_array_expands_counts_geometry_and_cell_provenance RED→GREEN; followed ezdxf's official Insert.multi_insert documentation.
- Final: fixed unbounded extraction and unintended CAD/BOQ model input — test_text_extraction_batches_without_sending_cad_or_boq RED→GREEN; bounded text-document batches and batch-local source validation.
- Final: fixed omitted/mutable writing requirements — test_generation_receives_only_published_requirements RED→GREEN.
- Final fix-pass suite: backend 66/66 passed; frontend 3/3 passed; Vite build passed on 2026-11-03. Additional scope test_boq_field_reference_keeps_quantity_unit_and_unit_project_scope and short manual quantity adoption RED→GREEN; generated BOQ field fragments retain scope/units. Existing Starlette/httpx deprecation warning remains; no test failures.
- Final: Ruling: Allow AI-generated prose only as frozen fact references and selected approved generic sentences — arbitrary natural-language semantic truth cannot be enforced reliably by number/keyword regexes. Cost if wrong: prose variety is intentionally limited; users can still manually edit exported/editor content and must review those edits.
- Final: minor (deferred): The pre-existing project-list status label remains “资料待上传” after processing; the fact-library tab shows the actual parsing/version status.
- Final: Ruling: Professional interpretation of CAD proxies, duplicate views and construction measurement scope stays explicit review evidence — geometric fixtures verify arithmetic, not all-discipline professional takeoff. Cost if wrong: a qualified reviewer must identify adopted component scope; the software must not claim complete arbitrary-DWG takeoff.
- Final: Ruling: Archive validation covers member paths/link metadata, bounds and tested traversal cases; a hostile RAR binary fuzz corpus is outside this acceptance — preserve original inputs and rely on maintained archive tools. Cost if wrong: malformed binary cases may still fail or need additional hardening.
- Final: Ruling: ODA environment/performance is judged by signed official download and successful real conversions, followed by fresh real-material reanalysis — no independent installer audit is claimed. Cost if wrong: another machine may need a different supported converter setup.
- Final: Ruling: Browser behavior is verified directly by the parent after review — the reviewer did not control the browser. Cost if wrong: unexercised UI combinations may still need follow-up.
- Final: Ruling: Existing immutable snapshots protect past publications; future parser ordinal changes and hostile concurrent filesystem/database mutation are not certified — current app is a local single-user workflow. Cost if wrong: adopted draft evidence may need rechecking after parser changes; concurrent writers need a separate design.
- 2026-11-03 real acceptance: reanalyzed all 8 DWG and 3 XLS using final adapters; 17 documents, 0 failed/unprocessed, 1096 facts and independent BOQ count 1096. Published new v3 (v1/v2 preserved), real model HTTP 200 with typed references and v3 citation. Runtime 297.73 seconds. Detailed report: data/acceptance/验收报告.md.
- Task 5: complete. Browser confirmed v3 / 1096 facts / 38280 review entries / 19 issues, ZB search returned 29 actual entries, published Markdown preview rendered. Backend health ok; frontend reachable. Snapshot has 51 Markdown files; all 60 manifest file hashes valid.
- Final: Ruling: Keep the local feature branch and working services for review, following the user's explicit autonomous execution instruction — no shared branch push or merge is necessary to run this local project. Cost if wrong: Git integration remains a later local decision; the feature is already present in the user's checkout.
