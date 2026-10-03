<!-- Generated from docs-site/README.md; edit the canonical repository source. -->

# Documentation toolchain

`docs-site/` assembles the maintained Chances Markdown into a static site.
[The documentation system contract](../docs/Developer/Documentation-System.md)
owns acceptance; [adoption evidence](../docs/Developer/Documentation-Adoption.md)
owns this repository's migration and deployment boundary.

## Prerequisites

Use Node.js 20 or later and npm. The committed lockfile owns dependency versions.
Install the Chromium browser used by Playwright before running the full check.

## Install and check

From the repository root:

```bash
npm --prefix docs-site ci
npm --prefix docs-site exec -- playwright install chromium
npm --prefix docs-site run security:audit
npm --prefix docs-site run check
```

The check lints maintained Markdown, runs scaffold unit tests, checks external
links, assembles sources, builds the site, verifies route/search/sitemap/robots
invariants and asset budgets, and exercises browser behavior and accessibility.
Failures block this CI job. The full-tree audit retains raw findings and displays
exact, expiring maintainer exceptions under [the adoption policy](../docs/Developer/Documentation-Adoption.md).
No deployment occurs.

## Preview

```bash
npm --prefix docs-site start
```

Open the local address printed by Docusaurus. For a completed production build:

```bash
npm --prefix docs-site run serve
```

## Configuration and ownership

`product-docs.json` declares Chances identity, canonical target coordinates,
repository URL, and source branch. `docs-map.json` declares the complete maintained
source inventory and stable routes. Product prose stays in mapped source pages;
the renderer contains no product-specific scientific claims.

Generated `.generated`, `.docusaurus`, `build`, browser reports, and dependency
folders stay ignored. Do not edit derived output. An omitted source, duplicate
route, broken link, stale source mirror, overflow, or failed accessibility check
needs correction in its authoritative file.

## Read next

Use [the system contract](../docs/Developer/Documentation-System.md) when
changing composition, routes, or shared rendering behavior.
