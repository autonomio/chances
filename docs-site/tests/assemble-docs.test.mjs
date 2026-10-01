import assert from 'node:assert/strict';
import {mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';

import {
  normalizeForMdx,
  rewriteOutsideCode,
  validateDocuments,
  validateDocumentSources,
  validateRouteInventory,
  validateProfile,
  validateSections,
} from '../scripts/assemble-docs.mjs';
import {
  assertPublicUrl,
  extractExternalLinks,
  isPublicAddress,
} from '../scripts/check-external-links.mjs';
import {
  lintExitCode,
  markdownSources,
} from '../scripts/lint-markdown.mjs';
import {
  isPathInside,
  resolveRepositoryPath,
} from '../scripts/repository-paths.mjs';
import {canonicalSitemapUrl, siteRoute} from '../scripts/site-urls.mjs';

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const product = JSON.parse(readFileSync(path.join(siteRoot, 'product-docs.json'), 'utf8'));
const docsMap = JSON.parse(readFileSync(path.join(siteRoot, 'docs-map.json'), 'utf8'));
const standardSections = () => ['Overview', 'Guides', 'Reference', 'Developer', 'Packages']
  .map((label, index) => ({
    dir: label.toLowerCase(), label, position: index + 1,
    slug: `/${label.toLowerCase()}`, description: `${label} description.`,
  }));

const mark = (value) => value.replaceAll('{TOKEN}', 'REWRITTEN');


test('rewrites prose but preserves fenced and inline code', () => {
  const source = [
    'before {TOKEN}',
    '```text',
    'inside {TOKEN}',
    '```',
    '~~~text',
    'inside tilde {TOKEN}',
    '~~~',
    'after `{TOKEN}` and {TOKEN}',
  ].join('\n');

  assert.equal(
    rewriteOutsideCode(source, mark),
    [
      'before REWRITTEN',
      '```text',
      'inside {TOKEN}',
      '```',
      '~~~text',
      'inside tilde {TOKEN}',
      '~~~',
      'after `{TOKEN}` and REWRITTEN',
    ].join('\n')
  );
});

test('preserves the tail of an unclosed fence', () => {
  const source = 'before {TOKEN}\n```text\ninside {TOKEN}';

  assert.equal(
    rewriteOutsideCode(source, mark),
    'before REWRITTEN\n```text\ninside {TOKEN}'
  );
});

test('preserves the tail of unmatched inline code', () => {
  const source = 'before {TOKEN} and `{TOKEN}';

  assert.equal(
    rewriteOutsideCode(source, mark),
    'before REWRITTEN and `{TOKEN}'
  );
});

test('preserves multi-backtick inline code while transforming surrounding prose', () => {
  const source = 'before {TOKEN}, ``inside $& $$ ` {TOKEN}``, after {TOKEN}';

  assert.equal(
    rewriteOutsideCode(source, mark),
    'before REWRITTEN, ``inside $& $$ ` {TOKEN}``, after REWRITTEN'
  );
});

test('extracts unique Markdown and HTML external links', () => {
  const source = [
    '[Repository](https://github.com/Autonomio/example)',
    '<a href="https://docs.autonomio.fi/example/">Docs</a>',
    '<img src="https://docs.autonomio.fi/example/logo.png" alt="Logo" />',
    '[Duplicate](https://github.com/Autonomio/example)',
    '`[Inline example](http://127.0.0.1/private)`',
    '~~~markdown',
    '[Fenced example](http://169.254.169.254/latest/meta-data)',
    '~~~',
  ].join('\n');

  assert.deepEqual(
    [...extractExternalLinks(source)].sort(),
    [
      'https://docs.autonomio.fi/example/',
      'https://docs.autonomio.fi/example/logo.png',
      'https://github.com/Autonomio/example',
    ]
  );
});

test('rewrites prose links without mutating code examples', () => {
  const source = [
    '[Docs](docs/README.md)',
    '[``Docs with `ticks` ``](docs/README.md)',
    '<a href="docs/README.md">Docs</a>',
    '```markdown',
    '[Docs](docs/README.md)',
    '```',
    '`[Docs](docs/README.md)`',
    '``[Docs](docs/README.md) with `ticks` ``',
  ].join('\n');

  const normalized = normalizeForMdx(source, 'README.md');
  const home = docsMap.documents.find((document) => document.source === 'README.md');
  const hub = docsMap.documents.find((document) => document.source === 'docs/README.md');
  assert.ok(home && hub, 'home and docs hub must be mapped');
  const relative = path.posix.relative(path.posix.dirname(home.dest), hub.dest);
  const lines = normalized.split('\n');
  assert.ok(lines.includes(`[Docs](${relative})`));
  assert.ok(lines.includes(`[\`\`Docs with \`ticks\` \`\`](${relative})`));
  assert.ok(lines.includes(`<a href="${siteRoute(product.basePath, hub.slug)}">Docs</a>`));
  assert.match(normalized, /^`\[Docs\]\(docs\/README\.md\)`$/m);
  assert.match(normalized, /^``\[Docs\]\(docs\/README\.md\) with `ticks` ``$/m);
  assert.match(
    normalized,
    /```markdown\n\[Docs\]\(docs\/README\.md\)\n```/
  );
});

test('keeps repository link resolution inside the repository root', () => {
  assert.equal(isPathInside('/repo', '/repo'), true);
  assert.equal(isPathInside('/repo', '/repo/docs/README.md'), true);
  assert.equal(isPathInside('/repo', '/repo-neighbor/README.md'), false);
  assert.equal(isPathInside('/repo', '/outside/README.md'), false);
  assert.throws(
    () => resolveRepositoryPath('/repo', '../outside/README.md'),
    /documentation source is outside the repository/
  );
});

test('builds canonical sitemap URLs for root and nested docs paths', () => {
  assert.equal(
    canonicalSitemapUrl('https://docs.example.com', '/'),
    'https://docs.example.com/sitemap.xml'
  );
  assert.equal(
    canonicalSitemapUrl('https://docs.example.com/', '/product/'),
    'https://docs.example.com/product/sitemap.xml'
  );
  assert.equal(siteRoute('/', '/guide'), '/guide');
  assert.equal(siteRoute('/', '/'), '/');
  assert.equal(siteRoute('/product/', '/guide'), '/product/guide');
  assert.equal(siteRoute('/product/', '/'), '/product/');
});

test('derives Markdown lint sources from the route map', () => {
  const map = {
    documents: [
      {source: 'README.md'},
      {source: 'docs/README.md'},
      {source: 'README.md'},
    ],
  };

  assert.deepEqual(
    markdownSources(map),
    ['CHANGELOG.md', 'README.md', 'docs/README.md']
  );
});

test('fails markdown lint when the subprocess exits by signal', () => {
  assert.equal(lintExitCode(null), 1);
  assert.equal(lintExitCode(2), 2);
});

test('validates every category field before generation', () => {
  const sections = standardSections();

  assert.doesNotThrow(() => validateSections(sections));
  assert.throws(
    () => validateSections([{...sections[0], label: ''}, ...sections.slice(1)]),
    /section.label must be a non-empty string/
  );
  assert.throws(
    () => validateSections([{...sections[0], position: 0}, ...sections.slice(1)]),
    /section.position must be a positive integer/
  );
  assert.throws(
    () => validateSections([{...sections[0], slug: '/section/'}, ...sections.slice(1)]),
    /section.slug must be \/ or a canonical leading-slash route/
  );
});

test('validates canonical document routes before generation', () => {
  const documents = [
    {source: 'README.md', dest: 'index.md', slug: '/'},
    {source: 'docs/README.md', dest: 'overview.md', slug: '/overview'},
  ];

  assert.doesNotThrow(() => validateDocuments(documents));
  assert.throws(
    () => validateDocuments([{...documents[0], slug: 'overview'}]),
    /document.slug must be \/ or a canonical leading-slash route/
  );
  assert.throws(
    () => validateDocuments([{...documents[0], slug: '/overview/'}]),
    /document.slug must be \/ or a canonical leading-slash route/
  );
});

test('validates documentation deployment coordinates before generation', () => {
  const profile = {
    productId: 'product',
    productName: 'Product',
    tagline: 'Product documentation.',
    siteUrl: 'https://docs.example.com',
    basePath: '/product/',
    sourceRepoUrl: 'https://github.com/Autonomio/product',
    sourceBranch: 'master',
  };

  assert.doesNotThrow(() => validateProfile(profile));
  assert.doesNotThrow(() => validateProfile({...profile, basePath: '/'}));
  assert.throws(
    () => validateProfile({...profile, siteUrl: 'https://docs.example.com/'}),
    /siteUrl must be an HTTP\(S\) origin without a trailing slash/
  );
  assert.throws(
    () => validateProfile({...profile, basePath: 'product/'}),
    /basePath must be \/ or have leading and trailing slashes/
  );
});

test('rejects external-link destinations that can reach private networks', async () => {
  assert.equal(isPublicAddress('8.8.8.8'), true);
  assert.equal(isPublicAddress('127.0.0.1'), false);
  assert.equal(isPublicAddress('169.254.169.254'), false);
  assert.equal(isPublicAddress('10.20.30.40'), false);
  assert.equal(isPublicAddress('192.0.2.1'), false);
  assert.equal(isPublicAddress('::1'), false);
  assert.equal(isPublicAddress('fe80::1'), false);

  await assert.rejects(
    assertPublicUrl('http://localhost/private'),
    /non-public destination/
  );
  await assert.rejects(
    assertPublicUrl('http://169.254.169.254/latest/meta-data'),
    /non-public destination/
  );
  await assert.rejects(
    assertPublicUrl('https://user:secret@example.com/'),
    /must not contain credentials/
  );
});


test('uses declared source branch and rejects ambiguous repository coordinates', () => {
  const profile = {
    productId: 'product', productName: 'Product', tagline: 'Product documentation.',
    siteUrl: 'https://docs.example.com', basePath: '/product/',
    sourceRepoUrl: 'https://github.com/autonomio/product', sourceBranch: 'master',
  };
  assert.doesNotThrow(() => validateProfile({...profile, sourceBranch: 'release/docs'}));
  assert.throws(() => validateProfile({...profile, sourceBranch: '../master'}), /branch name/);
  assert.throws(() => validateProfile({...profile, sourceRepoUrl: 'https://example.com/org/repo'}), /canonical GitHub/);
  const normalized = normalizeForMdx('[Profile](docs-site/product-docs.json)', 'README.md');
  assert.equal(normalized, `[Profile](${product.sourceRepoUrl}/blob/${product.sourceBranch}/docs-site/product-docs.json)`);
});


test('rejects section renaming, reordering, and destination traversal', () => {
  const sections = standardSections();
  for (const change of [{dir: '../overview'}, {dir: './overview'}, {label: 'Introduction'},
    {position: 2}, {slug: '/different'}]) {
    assert.throws(() => validateSections([{...sections[0], ...change}, ...sections.slice(1)]));
  }
  assert.throws(() => validateSections([...sections].reverse()), /five standard section names/);
});

test('rejects aliases and traversal in maintained source and destination paths', () => {
  const home = {source: 'README.md', dest: 'index.md', slug: '/'};
  for (const key of ['source', 'dest']) {
    for (const value of ['./README.md', 'docs/../README.md', '/README.md', 'docs//README.md',
      'docs/./README.md', 'docs\\README.md', 'C:/README.md', 'docs/README.md/', 'bad\u0000.md']) {
      assert.throws(() => validateDocuments([{...home, [key]: value}]), /canonical relative path/);
    }
    assert.throws(() => validateDocuments([{...home, [key]: 'image.png'}]), /Markdown paths/);
  }
});

test('rejects URL aliases in route slugs and deployment base paths', () => {
  const home = {source: 'README.md', dest: 'index.md', slug: '/'};
  for (const slug of ['/docs/../guide', '/docs/./guide', '/docs//guide', '/docs%2fguide',
    '/docs?preview', '/docs#fragment', '/docs\\guide', '/docs guide']) {
    assert.throws(() => validateDocuments([{...home, slug}]), /canonical leading-slash route/);
  }
  for (const basePath of ['/docs/../', '/docs/./', '/docs%2fguide/', '/docs?preview/',
    '/docs#fragment/', '/docs\\guide/', '/docs guide/']) {
    assert.throws(() => validateProfile({...product, basePath}), /leading and trailing slashes/);
  }
});

test('rejects section, document, and search route collisions and requires a home', () => {
  const sections = standardSections();
  const home = {source: 'README.md', dest: 'index.md', slug: '/'};
  assert.doesNotThrow(() => validateRouteInventory(sections, [home]));
  for (const slug of ['/overview', '/search']) {
    assert.throws(() => validateRouteInventory(sections, [home,
      {source: 'docs/README.md', dest: 'overview/hub.md', slug}]), /route values must be unique/);
  }
  assert.throws(() => validateRouteInventory(sections, []), /product home at \/$/);
});

test('rejects physical source aliases and symlinks outside the repository', () => {
  const root = mkdtempSync(path.join(tmpdir(), 'docs-sources-'));
  const outside = mkdtempSync(path.join(tmpdir(), 'docs-outside-'));
  try {
    writeFileSync(path.join(root, 'README.md'), '# Home\n');
    writeFileSync(path.join(outside, 'private.md'), '# Private\n');
    symlinkSync('README.md', path.join(root, 'alias.md'));
    symlinkSync(path.join(outside, 'private.md'), path.join(root, 'outside.md'));
    assert.doesNotThrow(() => validateDocumentSources(root, [{source: 'README.md'}]));
    assert.throws(() => validateDocumentSources(root, [{source: 'README.md'}, {source: 'alias.md'}]),
      /resolved document source values must be unique/);
    assert.throws(() => validateDocumentSources(root, [{source: 'outside.md'}]), /resolves outside/);
  } finally {
    rmSync(root, {recursive: true, force: true});
    rmSync(outside, {recursive: true, force: true});
  }
});
