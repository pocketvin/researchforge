# ResearchForge Data Notice

ResearchForge source code is licensed under the MIT License. That license does not grant rights to third-party filings, announcements, market data, or other source materials.

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
- private Benchmark or Final Test answers before the applicable evaluation is irrevocably closed;
- API keys, cookies, credentials, or personal data.

When a real excerpt cannot safely be redistributed, public fixtures use synthetic evidence with explicit labels. The corresponding real experiment may publish only its hash, metrics, official source locator, and method. A source link is attribution, not proof of permission to redistribute its contents.

## V1.5 real-data slice

`data/product/packages/catl-2024h1/` contains one derived product package for the official CATL
2024 half-year report. It includes six reviewed normalized facts, eight minimal evidence chunks,
the official URL, publication/retrieval times, page locators, parser identity and hashes. The
1,684,794-byte source PDF is not committed. Factual table cells and two short limitation snippets
are included to make claim-level provenance demonstrable; no substantial portion of the filing is
reproduced.

This package is separate from `data/fixtures/` and frozen Benchmark packages. Product execution
rejects namespace mismatch rather than silently falling back to either one.

## Intended use

ResearchForge is a local, single-user research engineering demonstration. It does not provide investment advice, trade execution, real-time prices, or a warranty that source data is complete or correct. Users remain responsible for source terms, factual verification, and investment decisions.
