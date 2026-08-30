# Risk Register

| ID | Risk | Probability | Impact | Early trigger | Mitigation and fallback |
|---|---|---|---|---|---|
| R-001 | Structured-data license, coverage, or publication history is unsuitable | High | Critical | Source cannot provide period/currency/scope/license metadata | Run the G0 source spike; fall back to frozen reconciled fixtures |
| R-002 | YTD, discrete-quarter, restatement, or scope semantics produce wrong comparisons | High | Critical | Provider figures disagree with official filings | Preserve full period metadata; deterministic derivation only; reject unexplained rows |
| R-003 | Filing PDFs are scanned or parse poorly | Medium | High | Stable locators and text extraction fail on sample filings | Choose text-readable companies; no V1 OCR platform |
| R-004 | Five product modes consume effort before one mode works | High | High | Multiple incomplete endpoints or UI panels appear before L1 | Enforce the thin slice and one-work-in-progress rule |
| R-005 | LangGraph becomes business logic or a multi-agent abstraction | Medium | High | Formulas/prompts/adapters are embedded in nodes or graph count grows | Enforce `research-workflow.md`; nodes call plain services and persist artifact IDs |
| R-006 | Benchmark leakage invalidates improvement claims | Medium | Critical | Validation/Final Test labels are visible during patch generation | Freeze manifests and namespaces; audit access before G3 |
| R-007 | No genuine repeated failure supports Evolution | Medium | High | Failure support stays below the frozen threshold | Report the negative result; never synthesize support or alter the threshold post hoc |
| R-008 | Verifier is gamed without improving research quality | Medium | Critical | Coverage rises while human-grounded correctness falls | Pair deterministic checks with golden-case review and regression guardrails |
| R-009 | LLM cost, latency, or nondeterminism harms reproducibility | Medium | Medium | Repeated fixed-case runs vary materially or exceed recorded budgets | Pin configuration, cap budgets, cache immutable inputs, report distribution and failures |
| R-010 | Frontend polish hides missing core evidence | High | Medium | UI activity starts before schema-valid report and trace | Keep CLI/API demo as fallback; start React after L2 evidence |
| R-011 | Portfolio copy overclaims incomplete functionality | Medium | High | Resume or README metrics lack run IDs and denominators | Use `PORTFOLIO.md`; link every claim to verified artifacts |
| R-012 | Interruption makes the project expensive to resume | High | Medium | More than one active milestone or stale status files | Update both checkpoints each session and rehearse the resume playbook |

## Review Cadence

Review the register at the start of each gate. Add a risk only when it changes a decision, acceptance test, or fallback; do not turn this into a generic issue list.

