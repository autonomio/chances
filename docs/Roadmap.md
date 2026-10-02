# Roadmap

This page records intended work from October 2, 2026 through October 31, 2027.
It guides priorities; it does not promise delivery dates or describe unshipped
features as available. Current behavior belongs in the [operation catalog](Reference/Operation-Catalog.md).

## Researcher outcomes

| Period | Intended work | Acceptance evidence |
| --- | --- | --- |
| October–December 2026 | Publish the reviewed 2.0 package with verifiable build provenance; complete documented maintenance continuity and the Silver assessment | Approved release artifacts, consumer verification, and source-linked assessment evidence |
| January–June 2027 | Expand distributions and experimental designs when a documented research workflow needs them; strengthen agent-readable inspection and failure contracts | Reviewed scientific definition, explicit parameters and support, meaningful tests, executable examples, and regenerated catalogs |
| July–October 2027 | Improve throughput and memory use on measured researcher workloads; strengthen repeatability evidence across supported dependency upgrades | Retained benchmark protocol and environment, before/after measurements, unchanged declared output contracts or an explicit compatibility migration |
| Throughout the period | Maintain dependencies, security fixes, release verification, accessible documentation, and the supported runtime matrix | Required CI, vulnerability audits, release notes, and artifact installation checks |

## Scope decisions

Chances intends to make declared randomness easier to execute, verify, retain,
and replay. New families need an actual scientific use case and an explicit
contract; a larger catalog alone is not the acceptance criterion. Agents must
have the same inspectable protocol, deterministic stream ownership, and
structured failures as human callers.

The project does not plan to become a cryptographic key or nonce service,
a source of certified physical entropy, or an inference engine that chooses a
researcher's statistical method. It will not promise exact replay across
arbitrary environments, hide invalid inputs behind another method, or weaken
review and evidence requirements to expand the catalog.

## Review and changes

Maintainers review this roadmap at least quarterly and before its horizon
expires. Record changed priorities through public issues or reviewed PRs;
update this page when intentions change. Evaluate proposed work against the
[product boundary](README.md#product-boundary), scientific tests, and
[release policy](Developer/Release-Policy.md).

## Read next

Use the [current catalog](Reference/Operation-Catalog.md) for available methods,
or [contribute a scoped proposal](../CONTRIBUTING.md).
