# Changelog

All notable contract and planning changes are recorded here. Product-scope changes require a separate decision and change note.

## [Contract Package 1.3.0] — 2026-08-30

### Added

- Active V1.3 product/research scope and explicit V1.2→V1.3 change note.
- Eleven current V1.3 schemas while preserving V1.2 schemas as history.
- Dedicated `workflow-trace` contract/example for sanitized LangGraph execution evidence.
- Explicit Run Manifest workflow configuration: engine, graph version, and checkpoint schema version.
- Honest `insufficient_data` terminal lifecycle state.
- Three supporting persistence records: source documents, evidence chunks, and run artifacts.

### Changed

- V1.2 is no longer the active frozen scope; V1.3 is a versioned baseline changed through explicit decisions and change notes.
- Product/portfolio completion is separated from the result of the Evolution research hypothesis.
- LangGraph remains required for the single Research Agent workflow but is prohibited from owning finance, retrieval, verifier, persistence, or Evolution semantics.
- pgvector is conditional on retrieval evidence instead of being an unconditional implementation blocker.
- Active contracts, status, guidance, examples, and validator target V1.3.
- `insufficient_data` persists a structured failure and Workflow Trace but never a Research Result artifact.

### Preserved

- Five product task modes, one Agent, one skill, and the earnings-quality Evolution target.
- Benchmark leakage protections and Base/Seed/Candidate comparability.
- V1.2 scope document, schemas, and example as immutable historical evidence.

## [Contract Package 1.2.1] — 2026-08-30

### Added

- Solo-success plan with Portfolio MVP and honest stopping levels.
- Portfolio/interview evidence guide.
- Data-source acceptance contract and spike protocol.
- Product-success metrics distinct from Evolution metrics.
- Implementation blueprint and complexity budget.
- Feasibility/career/usefulness/completeness/resumability scorecard.
- Risk register with triggers and fallbacks.
- Project status, decision log, and resume playbook.
- Machine-readable project-checkpoint schema and live `project-status.json`.
- Bounded LangGraph workflow contract and explicit framework/domain boundary.

### Changed

- README now exposes current gate, next action, success ladder, and strategy documents.
- AGENTS.md now requires one active milestone, status handoff, evidence-backed career claims, and complexity justification.
- Contract catalog and validator include the new contracts and project checkpoint.

### Scope

No V1.2 product capability was added or removed. These changes improve execution probability, proof quality, and project recoverability.

## [Contract Package 1.2.0] — 2026-08-29

### Added

- Initial V1.2 scope-preserving project scaffold.
- Nine core JSON Schemas.
- Financial methodology, task, Benchmark, Evolution, lifecycle, and development-gate contracts.
- Dependency-free contract validator and Benchmark Case example.
