import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

import {canonicalSitemapUrl, siteRoute} from './site-urls.mjs';

const scriptPath = fileURLToPath(import.meta.url);
const siteRoot = path.resolve(path.dirname(scriptPath), '..');
const buildRoot = path.resolve(siteRoot, 'build');
const profile = JSON.parse(
  await fs.readFile(path.resolve(siteRoot, 'product-docs.json'), 'utf8')
);
const docsMap = JSON.parse(
  await fs.readFile(path.resolve(siteRoot, 'docs-map.json'), 'utf8')
);
const maxJavaScriptBytes = 1_500_000;
const maxCssBytes = 400_000;

export function routeFile(slug) {
  if (slug === '/') {
    return 'index.html';
  }
  return `${slug.replace(/^\//, '')}.html`;
}

export function expectedSitemapUrls(product, map) {
  return new Set([
    ...map.sections.map((section) => section.slug),
    ...map.documents.map((document) => document.slug),
    '/search',
  ].map((slug) => new URL(siteRoute(product.basePath, slug), product.siteUrl).href));
}

export function validateSitemap(xml, expected) {
  const urls = [...xml.matchAll(/<loc>([^<]*)<\/loc>/g)].map((match) =>
    match[1].trim().replaceAll('&amp;', '&'));
  const actual = new Set(urls);
  if (actual.size !== urls.length) {
    throw new Error('sitemap must not contain duplicate URLs');
  }
  const missing = [...expected].filter((url) => !actual.has(url));
  const unexpected = [...actual].filter((url) => !expected.has(url));
  if (missing.length || unexpected.length) {
    throw new Error(`sitemap URL set differs: missing=${JSON.stringify(missing)}, unexpected=${JSON.stringify(unexpected)}`);
  }
}

export function validateRobots(content, expected) {
  const entries = [...content.matchAll(/^Sitemap:\s*(\S+)\s*$/gm)].map((match) => match[1]);
  if (entries.length !== 1 || entries[0] !== expected) {
    throw new Error(`robots.txt must name exactly ${expected}`);
  }
}

async function main() {
  const expectedRoutes = new Set([
    ...docsMap.sections.map((section) => routeFile(section.slug)),
    ...docsMap.documents.map((document) => routeFile(document.slug)),
    'search.html',
  ]);
  for (const route of expectedRoutes) {
    await fs.access(path.resolve(buildRoot, route));
  }

  const sitemap = await fs.readFile(path.resolve(buildRoot, 'sitemap.xml'), 'utf8');
  validateSitemap(sitemap, expectedSitemapUrls(profile, docsMap));
  const robots = await fs.readFile(path.resolve(buildRoot, 'robots.txt'), 'utf8');
  const expectedSitemap = canonicalSitemapUrl(profile.siteUrl, profile.basePath);
  validateRobots(robots, expectedSitemap);
  const searchIndex = await fs.readFile(path.resolve(buildRoot, 'search-index.json'), 'utf8');
  const searchPayload = JSON.parse(searchIndex);
  const indexedDocuments = searchPayload[0]?.documents;
  if (!Array.isArray(indexedDocuments)) {
    throw new Error('search index does not contain a page-document collection');
  }
  const indexedRoutes = new Set(indexedDocuments.map((document) => document.u));
  for (const document of docsMap.documents) {
    const route = siteRoute(profile.basePath, document.slug);
    if (!indexedRoutes.has(route)) {
      throw new Error(`search index does not contain mapped route ${route}`);
    }
  }

  const assetRoot = path.resolve(buildRoot, 'assets');
  const assetPaths = [];
  async function collect(directory) {
    for (const entry of await fs.readdir(directory, {withFileTypes: true})) {
      const entryPath = path.resolve(directory, entry.name);
      if (entry.isDirectory()) {
        await collect(entryPath);
      } else {
        assetPaths.push(entryPath);
      }
    }
  }
  await collect(assetRoot);
  async function largestAsset(extension) {
    const matchingPaths = assetPaths.filter((file) => file.endsWith(extension));
    if (matchingPaths.length === 0) {
      throw new Error(`build contains no ${extension} assets`);
    }
    return Math.max(
      ...await Promise.all(
        matchingPaths.map(async (file) => (await fs.stat(file)).size)
      )
    );
  }
  const largestJavaScript = await largestAsset('.js');
  const largestCss = await largestAsset('.css');
  const assetSummary = (
    `js=${largestJavaScript}/${maxJavaScriptBytes}, `
    + `css=${largestCss}/${maxCssBytes}`
  );
  if (largestJavaScript > maxJavaScriptBytes || largestCss > maxCssBytes) {
    throw new Error(`asset budget exceeded: ${assetSummary}`);
  }
  process.stdout.write(
    `Build verified: ${expectedRoutes.size} routes, ${assetSummary}\n`
  );
}

if (process.argv[1] === scriptPath) {
  await main();
}
