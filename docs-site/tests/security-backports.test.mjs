import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import path from 'node:path';
import {realpathSync, readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import test from 'node:test';

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(siteRoot, 'package.json'));
const braces = require('braces');
const CachePolicy = require('http-cache-semantics');

function request(headers = {}) {
  return {url: 'https://example.test/private', method: 'GET', headers: {host: 'example.test', ...headers}};
}

function policy(headers, shared = true) {
  const result = new CachePolicy(request(), {status: 200, headers}, {shared});
  result._responseTime -= 60000;
  return result;
}

test('every installed consumer resolves the reviewed local backports', () => {
  const lock = JSON.parse(readFileSync(path.join(siteRoot, 'package-lock.json'), 'utf8'));
  for (const name of ['braces', 'http-cache-semantics']) {
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
