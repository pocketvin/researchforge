# ResearchForge Data Notice

ResearchForge source code is licensed under the MIT License. That license does not grant rights to third-party filings, announcements, market data, or other source materials.

## Active V2 runtime data

New product research uses one runtime data boundary under `artifacts/v2/`:

- original filing bytes stored by hash;
- reusable official filing/document cache;
- V2 Run manifests and artifact pointers;
- durable public trace events;
- resumable public LangGraph checkpoints;
- project/run provider-budget ledgers.

A V2 product Run acquires or reuses the official filing through this V2 cache. It does **not** fall back to `data/product`, `data/fixtures`, `data/archive`, benchmark packages, historical PostgreSQL state, or old V1 Run artifacts.

## Historical data retained for auditability

The repository still contains frozen V1-era material such as:

- `data/product/` reviewed filing packages;
- `data/fixtures/` synthetic/public-safe fixtures and frozen benchmark packages;
- `data/archive/` preserved source/evidence metadata;
- historical `artifacts/`, schemas, benchmark/evolution evidence and screenshots.

These files are useful for reproducing and auditing earlier milestones, hashes and contract evidence. They are **history, not active product data**. Runtime Docker images no longer copy or mount them.

## Public-repository boundary

The public package may contain:

- normalized factual values that were manually checked;
- minimal evidence excerpts only when redistribution is permitted;
- factual tables whose reuse is permitted, or synthetic equivalents;
- official source URLs, publication timestamps, page or section locators, content hashes, and data-method notes;
- aggregate experiment metrics that do not expose a closed Benchmark answer key.

It must not contain:

- complete third-party announcement or annual-report PDFs;
- licensed or access-controlled datasets;
- material excerpts whose redistribution basis has not been confirmed;
- private Benchmark/held-out answers or questions before the applicable evaluation boundary permits disclosure;
- API keys, cookies, credentials, or personal data.

When a real excerpt cannot safely be redistributed, historical public fixtures use synthetic evidence with explicit labels. A source link is attribution, not proof of permission to redistribute its contents.

## Historical V1.5 example

`data/product/packages/catl-2024h1/` is a preserved V1.5 reviewed package. It contains derived facts/evidence metadata from the official CATL 2024 half-year report; the source PDF is not committed. It remains only as historical release evidence and is not consulted by V2 product execution.

## Intended use

ResearchForge is a local, single-user research engineering project. It does not provide investment advice, trade execution, real-time prices, or a warranty that source data is complete or correct. Users remain responsible for source terms and factual verification.
