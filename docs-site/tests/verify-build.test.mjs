import assert from 'node:assert/strict';
import test from 'node:test';

import {
  expectedSitemapUrls,
  routeFile,
  validateRobots,
  validateSitemap,
} from '../scripts/verify-build.mjs';

const product = {siteUrl: 'https://docs.example.com', basePath: '/product/'};
const map = {sections: [{slug: '/overview'}], documents: [{slug: '/'}, {slug: '/overview/start'}]};
const canonicalUrls = [
  'https://docs.example.com/product/overview',
  'https://docs.example.com/product/',
  'https://docs.example.com/product/overview/start',
  'https://docs.example.com/product/search',
];
const sitemap = (urls) => `<urlset>${urls.map((url) => `<url><loc>${url}</loc></url>`).join('')}</urlset>`;

test('derives every canonical page, section, and search URL from the profile and map', () => {
  assert.deepEqual([...expectedSitemapUrls(product, map)], canonicalUrls);
  assert.deepEqual([...expectedSitemapUrls({...product, basePath: '/'}, map)], [
    'https://docs.example.com/overview', 'https://docs.example.com/',
    'https://docs.example.com/overview/start', 'https://docs.example.com/search',
  ]);
  assert.equal(routeFile('/'), 'index.html');
  assert.equal(routeFile('/overview/start'), 'overview/start.html');
});

test('validates sitemap URLs independently of their order', () => {
  assert.doesNotThrow(() => validateSitemap(sitemap([...canonicalUrls].reverse()), new Set(canonicalUrls)));
});

test('rejects same-count sitemap replacements, wrong origins, and trailing-slash aliases', () => {
  for (const replacement of ['https://wrong.example.com/product/search',
    'https://docs.example.com/product/undeclared', 'https://docs.example.com/product/search/']) {
    assert.throws(() => validateSitemap(sitemap([...canonicalUrls.slice(0, -1), replacement]),
      new Set(canonicalUrls)), /sitemap URL set differs/);
  }
});

test('rejects missing, unexpected, and duplicate sitemap entries', () => {
  assert.throws(() => validateSitemap(sitemap(canonicalUrls.slice(1)), new Set(canonicalUrls)),
    /sitemap URL set differs/);
  assert.throws(() => validateSitemap(sitemap([...canonicalUrls, 'https://docs.example.com/product/extra']),
    new Set(canonicalUrls)), /sitemap URL set differs/);
  assert.throws(() => validateSitemap(sitemap([...canonicalUrls, canonicalUrls[0]]), new Set(canonicalUrls)),
    /duplicate URLs/);
});

test('robots names exactly one canonical sitemap', () => {
  const url = 'https://docs.example.com/product/sitemap.xml';
  assert.doesNotThrow(() => validateRobots(`User-agent: *\nAllow: /\nSitemap: ${url}\n`, url));
  for (const content of [`Sitemap: https://wrong.example.com/product/sitemap.xml\n`,
    `Sitemap: ${url}/\n`, `Sitemap: ${url}\nSitemap: ${url}\n`,
    `# Sitemap: ${url}\n`, `Sitemap: ${url}\nSitemap: https://wrong.example.com/sitemap.xml\n`]) {
    assert.throws(() => validateRobots(content, url), /must name exactly/);
  }
});
