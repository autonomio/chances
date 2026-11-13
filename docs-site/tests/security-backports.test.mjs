import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import path from 'node:path';
import {realpathSync, readFileSync, cpSync, mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import test from 'node:test';
import {verifySecurityBackports} from '../scripts/verify-security-backports.mjs';

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(siteRoot, 'package.json'));
const braces = require('braces');
const CachePolicy = require('http-cache-semantics');
const deepmerge = require('deepmerge');

function request(headers = {}) {
  return {url: 'https://example.test/private', method: 'GET', headers: {host: 'example.test', ...headers}};
}

function policy(headers, shared = true) {
  const result = new CachePolicy(request(), {status: 200, headers}, {shared});
  result._responseTime -= 60000;
  return result;
}

test('reviewed backport hashes and identity match the installed source', () => {
  verifySecurityBackports();
});

test('modified source, identity and unreviewed files fail backport verification', (t) => {
  const root = realpathSync(mkdtempSync(path.join(tmpdir(), 'chances-backport-')));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  cpSync(path.join(siteRoot, 'vendor'), path.join(root, 'vendor'), {recursive: true});
  cpSync(path.join(siteRoot, 'package.json'), path.join(root, 'package.json'));
  cpSync(path.join(siteRoot, 'package-lock.json'), path.join(root, 'package-lock.json'));
  mkdirSync(path.join(root, 'node_modules'));
  for (const name of ['braces', 'http-cache-semantics', 'deepmerge']) {
    symlinkSync(path.join(root, 'vendor', name), path.join(root, 'node_modules', name), 'dir');
  }
  verifySecurityBackports(root);
  const source = path.join(root, 'vendor/braces/lib/parse.js');
  const original = readFileSync(source);
  writeFileSync(source, '// unreviewed source\n');
  assert.throws(() => verifySecurityBackports(root), /reviewed digest/);
  writeFileSync(source, original);
  const manifestPath = path.join(root, 'vendor/braces/package.json');
  const manifest = readFileSync(manifestPath);
  writeFileSync(manifestPath, JSON.stringify({...JSON.parse(manifest), version: '3.0.3'}));
  assert.throws(() => verifySecurityBackports(root), /identity differs/);
  writeFileSync(manifestPath, manifest);
  writeFileSync(path.join(root, 'vendor/braces/extra.js'), 'module.exports = {};\n');
  assert.throws(() => verifySecurityBackports(root), /file inventory/);
});

test('every installed consumer resolves the reviewed local backports', () => {
  const lock = JSON.parse(readFileSync(path.join(siteRoot, 'package-lock.json'), 'utf8'));
  for (const name of ['braces', 'http-cache-semantics', 'deepmerge']) {
    const expected = realpathSync(path.join(siteRoot, 'vendor', name, 'index.js'));
    assert.equal(realpathSync(require.resolve(name)), expected);
    let consumers = 0;
    for (const [location, pkg] of Object.entries(lock.packages)) {
      if (pkg.dependencies?.[name]) {
        const consumer = createRequire(path.join(siteRoot, location, 'package.json'));
        assert.equal(realpathSync(consumer.resolve(name)), expected, `${location} must use ${name} backport`);
        consumers++;
      }
    }
    assert.ok(consumers > 0);
  }
});

test('deep braces and parentheses fail explicitly before recursive walkers', () => {
  const library = require.resolve('braces');
  const code = `const assert = require('node:assert/strict'); const braces = require(${JSON.stringify(library)});
    for (const input of ['{'.repeat(4000) + 'a,b' + '}'.repeat(4000), '('.repeat(4000) + 'x' + ')'.repeat(4000)]) {
      for (const method of ['parse', 'compile', 'expand', 'stringify']) {
        assert.throws(() => braces[method](input), {name: 'SyntaxError', message: /maximum depth/});
      }
      assert.throws(() => braces(input), {name: 'SyntaxError', message: /maximum depth/});
    }`;
  const result = spawnSync(process.execPath, ['-e', code], {encoding: 'utf8', timeout: 5000});
  assert.equal(result.error, undefined);
  assert.equal(result.signal, null);
  assert.equal(result.status, 0, result.stderr);
});

test('direct AST inputs cannot bypass depth or cycle limits', () => {
  let ast = {type: 'text', value: 'x'};
  for (let depth = 0; depth < 101; depth++) ast = {type: 'root', nodes: [ast]};
  const cyclic = {type: 'root', nodes: []};
  cyclic.nodes.push(cyclic);
  for (const method of ['compile', 'expand', 'stringify']) {
    assert.throws(() => braces[method](ast), /maximum depth/);
    assert.throws(() => braces[method](cyclic), /repeated nodes/);
  }
});

test('ordinary brace compilation, expansion and matching remain compatible', () => {
  assert.deepEqual(braces.expand('docs/{Guides,Reference}/{a,b}.md'), [
    'docs/Guides/a.md', 'docs/Guides/b.md', 'docs/Reference/a.md', 'docs/Reference/b.md',
  ]);
  assert.equal(braces.compile('docs/{a,b}.md'), 'docs/(a|b).md');
  assert.deepEqual(require('micromatch')(['docs/a.md', 'docs/b.txt'], ['docs/*.{md,mdx}']), ['docs/a.md']);
});

test('max-stale and stale-while-revalidate cannot expose security-blocked responses', () => {
  const responses = [
    {'set-cookie': 'session=other-user', 'cache-control': 'max-age=600'},
    {'set-cookie': 'session=other-user', 'cache-control': 'immutable, max-age=600'},
    {'cache-control': 'proxy-revalidate, max-age=600'},
    {'cache-control': 'no-cache, max-age=600'},
    {'cache-control': 'no-store, max-age=600'},
    {'cache-control': 'private, max-age=600'},
    {vary: '*', 'cache-control': 'max-age=600'},
  ];
  for (const headers of responses) {
    for (const directive of ['max-stale', 'max-stale=999999999']) {
      const entry = policy({...headers, 'cache-control': `${headers['cache-control']}, stale-while-revalidate=999999999`});
      const restored = CachePolicy.fromObject(entry.toObject());
      for (const candidate of [entry, restored]) {
        const req = request({'cache-control': directive});
        assert.equal(candidate.satisfiesWithoutRevalidation(req), false, JSON.stringify(headers));
        assert.equal(candidate.evaluateRequest(req).response, undefined);
        assert.equal(candidate.evaluateRequest(req).revalidation.synchronous, true);
      }
    }
  }
});

test('ordinary expired public and private-cache responses can still honor max-stale', () => {
  const req = request({'cache-control': 'max-stale=120'});
  assert.equal(policy({'cache-control': 'public, max-age=1'}).satisfiesWithoutRevalidation(req), true);
  assert.equal(policy({'cache-control': 'max-age=1', 'set-cookie': 'own-session'}, false).satisfiesWithoutRevalidation(req), true);
  assert.equal(policy({'cache-control': 'public, max-age=600'}).satisfiesWithoutRevalidation(request()), true);
});

test('self and external parent cycles fail before expansion can loop', () => {
  const library = require.resolve('braces');
  const code = `const assert = require('node:assert/strict'); const braces = require(${JSON.stringify(library)});
    for (const external of [false, true]) {
      const paren = {type: 'paren', nodes: []};
      const parent = external ? {type: 'paren'} : paren;
      parent.parent = parent; paren.parent = parent;
      const ast = {type: 'root', nodes: [paren]};
      for (const method of ['compile', 'expand', 'stringify']) {
        assert.throws(() => braces[method](ast), /cyclic parents/);
      }
    }`;
  const result = spawnSync(process.execPath, ['-e', code], {encoding: 'utf8', timeout: 5000});
  assert.equal(result.error, undefined);
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(braces.expand('(a{b,c})'), ['(ab)', '(ac)']);
  assert.equal(braces.stringify('a{b'), 'a{b');
});

test('compiling an invalid closing node writes no diagnostic output', () => {
  const library = require.resolve('braces');
  const code = `const assert = require('node:assert/strict'); const braces = require(${JSON.stringify(library)});
    assert.equal(braces.compile({type: 'close', isClose: true, value: '}'}), '}');`;
  const result = spawnSync(process.execPath, ['-e', code], {encoding: 'utf8', timeout: 5000});
  assert.equal(result.error, undefined);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, '');
  assert.equal(result.stderr, '');
});

test('origin errors cannot restore forbidden responses through stale-if-error', () => {
  const responses = [
    {'set-cookie': 'other-user', 'cache-control': 'max-age=600'},
    {'cache-control': 'no-cache, max-age=600'},
    {'cache-control': 'proxy-revalidate, max-age=600'},
    {'cache-control': 'must-revalidate, max-age=600'},
    {'cache-control': 'no-store, max-age=600'},
    {'cache-control': 'private, max-age=600'},
    {vary: '*', 'cache-control': 'max-age=600'},
  ];
  for (const headers of responses) {
    const entry = policy({...headers, 'cache-control': `${headers['cache-control']}, stale-if-error=999999999`});
    entry._responseTime -= 600000;
    for (const candidate of [entry, CachePolicy.fromObject(entry.toObject())]) {
      assert.equal(candidate.useStaleWhileRevalidate(), false);
      for (const status of [500, 502, 503, 504]) {
        const result = candidate.revalidatedPolicy(request(), {status, headers: {}});
        assert.equal(result.modified, true, JSON.stringify(headers));
        assert.equal(result.matches, false);
        assert.notEqual(result.policy, candidate);
      }
      assert.throws(() => candidate.revalidatedPolicy(request(), undefined), /Response headers missing/);
    }
  }
  const publicEntry = policy({'cache-control': 'public, max-age=1, stale-if-error=120'});
  const result = publicEntry.revalidatedPolicy(request(), {status: 503, headers: {}});
  assert.equal(result.modified, false);
  assert.equal(result.policy, publicEntry);
  const mismatch = publicEntry.revalidatedPolicy({...request(), url: 'https://example.test/other'}, {status: 503, headers: {}});
  assert.equal(mismatch.modified, true);
  assert.notEqual(mismatch.policy, publicEntry);
});


test('prototype keys in merge operands cannot poison returned objects', () => {
  const target = JSON.parse('{"__proto__": {"a": 1}, "keep": {"x": 1}}');
  const source = JSON.parse('{"__proto__": {"polluted": true}, "keep": {"y": 2}}');
  for (const result of [deepmerge(target, source), deepmerge.all([target, source])]) {
    assert.equal(Object.getPrototypeOf(result), Object.prototype);
    assert.equal(result.polluted, undefined);
    assert.equal({}.polluted, undefined);
    assert.deepEqual(result.keep, {x: 1, y: 2});
  }
  const nested = deepmerge({a: JSON.parse('{"__proto__": {"polluted": true}}')}, {b: 1});
  assert.equal(Object.getPrototypeOf(nested.a), Object.prototype);
  assert.equal(nested.a.polluted, undefined);
  assert.equal(deepmerge({}, JSON.parse('{"__proto__": {"polluted": true}}')).polluted, undefined);
});

test('ordinary deep merges, arrays and clones remain compatible', () => {
  assert.deepEqual(deepmerge({a: {b: 1}}, {a: {c: 2}, d: [1]}), {a: {b: 1, c: 2}, d: [1]});
  assert.deepEqual(deepmerge({list: [1, 2]}, {list: [3]}), {list: [1, 2, 3]});
  assert.deepEqual(deepmerge.all([{a: 1}, {b: 2}, {c: 3}]), {a: 1, b: 2, c: 3});
  const source = {nested: {value: 1}};
  const cloned = deepmerge({}, source);
  assert.deepEqual(cloned, source);
  assert.notEqual(cloned.nested, source.nested);
  assert.deepEqual(deepmerge({list: [1]}, {list: [2]}, {arrayMerge: (target, source) => [...target, ...source, 'custom']}), {list: [1, 2, 'custom']});
});

test('must-revalidate permits fresh hits but forbids stale reuse through every path', () => {
  const entry = policy({'cache-control': 'max-age=600, must-revalidate, stale-if-error=999999999, stale-while-revalidate=999999999'});
  assert.equal(entry.satisfiesWithoutRevalidation(request()), true);
  assert.ok(entry.evaluateRequest(request()).response);
  entry._responseTime -= 600000;
  assert.equal(entry.satisfiesWithoutRevalidation(request({'cache-control': 'max-stale'})), false);
  assert.equal(entry.evaluateRequest(request()).response, undefined);
  assert.equal(entry.useStaleWhileRevalidate(), false);
  const result = entry.revalidatedPolicy(request(), {status: 503, headers: {}});
  assert.equal(result.modified, true);
  assert.notEqual(result.policy, entry);
});
