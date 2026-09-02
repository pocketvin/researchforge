# Product Research Run Contract

## Input

The ordinary user supplies exactly the product-level intent:

```text
Company + Period + Research Question
```

Company and period resolution happen before a run is created. Ambiguous or unsupported values
return a structured refusal; they do not silently select a nearby filing.

## Responsibilities

- The LLM interprets the question and performs bounded reasoning over supplied evidence.
- Deterministic Python owns formulas, period conversion, numeric comparison and policy gates.
- The Evidence System owns document identity, locators and Claim—Fact—Evidence linkage.
- The Verifier owns consistency, evidence coverage and counter-evidence checks.
- One bounded LangGraph owns lifecycle and orchestration.

## Isolation

A request with `data_namespace: product` MUST resolve only a ready product package. Fixture and
benchmark runs remain available for tests and the read-only Quality Lab through explicit roots,
but cannot satisfy or impersonate a product request.

## Output order

1. Executive Conclusion
2. Key Findings
3. Financial Facts
4. Calculations
5. Supporting Evidence
6. Counter Evidence
7. Risks & Limitations
8. Monitoring Plan
9. Research Trace

Facts, calculations, evidence and trace use progressive disclosure. Every material numeric claim
must resolve to a deterministic Calculation Record or a normalized Financial Fact. An absence of
credible counter evidence is reported as bounded `not_found`, never as proof that none exists.

## Degradation

Unsupported company/period, unavailable official source, hash mismatch, parsing failure,
insufficient verified facts or unresolved citation results in abstention, `insufficient_data` or
a structured terminal failure. Fluent unsupported prose is not an acceptable fallback.
