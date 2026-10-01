# Documentation adoption

This page records the documentation migration and its acceptance boundary.
The shared scaffold is adapted from `new-repository-template` at commit
`fa7bf92caab5bb8d7f73120d4dc3526fd86c0348`. Product prose and profiles describe
Chances; all organization identity is Autonomio. The operator authorized
licensing the adopted files under Autonomio; [the scaffold license](../../docs-site/LICENSE)
records that identity. The installed manual includes the same license notice.

## Prerequisites and baseline

Use the [developer setup](README.md) and locked Node toolchain. Before adoption,
Chances had a repository README and installed Markdown, JSON catalogs, and an
executable research example. It had no repository-owned rendered site, route map,
search, or visual baseline. Historical installed manual paths remain available as generated aliases.
The specifications and migration prose are now canonical under repository
Reference and Guides; package copies are generated with portable local links.
[The baseline manifest](../../docs-site/adoption-baseline.json) records prior
source hashes, template commit, lockfile, style fingerprint, and target coordinates.

## Expected differences

| Surface | Adopted behavior | Authority |
| --- | --- | --- |
| Information architecture | Overview, Guides, Reference, Developer, Packages | [System contract](Documentation-System.md) |
| Identity | Chances under Autonomio; matching metadata and style identifiers | `product-docs.json` |
| Source links | Explicit `sourceBranch=master`, matching this repository's default branch | Git repository and profile |
| Navigation and search | Stable routes, collapsed categories, local index | `docs-map.json` and browser checks |
| Appearance | Shared light/dark geometry, self-hosted Plex fonts, accessible code colors | `docs-site/src/css/custom.css` |
| Installed documentation | Generated mirrors retain usable links outside the checkout | Catalog generator and package tests |

Expanded browser coverage exposed inherited inline syntax colors that failed
light-theme contrast and a scrollable table without keyboard access. The renderer
now applies contrast-safe string/constant/comment tokens over Prism inline styles
and gives tables keyboard focus with a visible outline. These are explicit defect
corrections, preserving shared geometry and brand tokens.

The branch field removes the upstream assumption that every default branch is
`main`. It changes source-link coordinates, not the public API. The maintained
source map is the route authority; generated mirrors and build output are derived.

## Proof and failure conditions

Run the security audit and full site check from
[the documentation toolchain](../../docs-site/README.md), then Python tests,
catalog freshness, the research example, and installed artifact checks.
The browser matrix covers the product home, category index, guide, reference,
developer page, and package page in desktop/mobile and light/dark contexts.
Each context checks navigation, overflow, and accessibility; shared tests also
check search, source edit links, typography, and mobile interaction.

The inherited dependency audit blocks high-severity findings for ordinary
production roots and critical findings for the Docusaurus/search-only subtree.
That is a severity policy, not a claim that the dependency tree has no advisories.
The audit prints its findings and fails on unknown severities or malformed data.

## Deployment and rollout boundary

`https://autonomio.github.io/chances/` is the configured target coordinate for
canonical metadata, sitemap, and robots generation. Adoption builds and validates
the site locally and in CI; it does not publish or claim that URL is live. TLS,
redirects, security headers, and production error responses need a deployment
adapter and HTTP evidence before a hosted release can claim the full standard.

The full governance package is locally adopted; [governance adoption](Governance-Adoption.md) records its activation boundary. Its laws,
issue workflow, branch protection, and release automation are not enforced merely
by adopting documentation.

## Read next

Use [the documentation system contract](Documentation-System.md) for page
changes and [the contributor workflow](README.md) for verification.
