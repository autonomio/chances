import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {chmodSync, copyFileSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync, writeFileSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';

import {auditFailure} from '../scripts/audit-report.mjs';
import {auditSummary} from '../scripts/audit-security.mjs';

test('reports advisory counts without classifying findings as allowed', () => {
  const report = {vulnerabilities: {
    zeta: {severity: 'high'}, alpha: {severity: 'moderate'}, beta: {severity: 'moderate'},
  }};
  assert.match(auditFailure(report), /known vulnerabilities/);
  const summary = auditSummary(report);
  assert.match(summary, /Reported vulnerable packages: 3 \(moderate=2, high=1\)/);
  assert.match(summary, /Findings:\n  alpha \(moderate\)\n  beta \(moderate\)\n  zeta \(high\)/);
  assert.doesNotMatch(summary, /allowed|no known|zero vulnerabilities|0 vulnerabilities/i);
});

test('reports an empty audit explicitly without listing fictional findings', () => {
  assert.equal(auditSummary({vulnerabilities: {}}),
    'Docs-site npm audit completed.\nReported vulnerable packages: 0.\n');
});

const sourceRoot = fileURLToPath(new URL('..', import.meta.url));
for (const outcome of [0, 1, 2, 'accepted', 'signal', 'missing', 'array-report', 'null-finding', 'development-advisory']) {
  test(`the audit command handles complete fixture JSON with process outcome ${outcome}`, () => {
    const directory = realpathSync(mkdtempSync(path.join(os.tmpdir(), 'chances-audit-process-')));
    try {
      const scriptDirectory = path.join(directory, 'scripts');
      mkdirSync(scriptDirectory);
      for (const script of ['audit-security.mjs', 'audit-report.mjs', 'audit-exceptions.mjs']) {
        copyFileSync(path.join(sourceRoot, 'scripts', script), path.join(scriptDirectory, script));
      }
      const entries = JSON.parse(readFileSync(path.join(sourceRoot, 'tests', 'fixtures', 'reviewed-exceptions.json'), 'utf8'));
      writeFileSync(path.join(directory, 'security-exceptions.json'), JSON.stringify(entries));
      const packages = {};
      for (const entry of entries) {
        const location = `node_modules/${entry.package}`;
        mkdirSync(path.join(directory, location), {recursive: true});
        writeFileSync(path.join(directory, location, 'package.json'), JSON.stringify({name: entry.package, version: entry.version}));
        packages[location] = {version: entry.version};
      }
      writeFileSync(path.join(directory, 'package-lock.json'), JSON.stringify({packages}));
      const accepted = {vulnerabilities: Object.fromEntries(entries.map((entry) => [entry.package, {
        name: entry.package, severity: entry.severity, nodes: [`node_modules/${entry.package}`],
        via: [{name: entry.package, dependency: entry.package, severity: entry.severity,
          url: `https://github.com/advisories/${entry.id}`}],
      }]))};
      const payload = outcome === 'array-report' ? {vulnerabilities: []}
        : outcome === 'development-advisory' ? {vulnerabilities: {tool: {severity: 'low'}}}
          : outcome === 'null-finding' ? {vulnerabilities: {tool: null}}
            : outcome === 'accepted' ? accepted : {vulnerabilities: {}};
      if (outcome !== 'missing') {
        const finish = outcome === 'signal'
          ? "process.kill(process.pid, 'SIGTERM')"
          : `process.exit(${outcome === 'accepted' ? 1 : typeof outcome === 'number' ? outcome : 0})`;
        const executable = path.join(directory, 'npm');
        writeFileSync(executable,
          `#!${process.execPath}\nif (process.argv.includes('--omit=dev') || !process.argv.includes('--include=dev')) process.exit(3);\nprocess.stdout.write(${JSON.stringify(JSON.stringify(payload))}, () => { ${finish}; });\n`);
        chmodSync(executable, 0o755);
      }
      const result = spawnSync(process.execPath, [path.join(scriptDirectory, 'audit-security.mjs')], {
        encoding: 'utf8', env: {...process.env, PATH: directory},
      });
      assert.equal(result.error, undefined);
      if (outcome === 0 || outcome === 'accepted') {
        assert.equal(result.status, 0, result.stderr);
        assert.match(result.stdout, /npm audit completed/);
        if (outcome === 'accepted') {
          for (const entry of entries) assert.ok(result.stdout.includes(`Accepted known finding until ${entry.expires} 00:00 UTC: ${entry.id}`));
          assert.match(result.stdout, /2 reported package findings accepted/);
          assert.doesNotMatch(result.stdout, /zero vulnerabilities|0 vulnerabilities/i);
        }
      } else if (outcome === 'development-advisory') {
        assert.equal(result.status, 1);
        assert.match(result.stderr, /tool \(low\)/);
      } else if (outcome === 'null-finding') {
        assert.equal(result.status, 1);
        assert.match(result.stderr, /invalid vulnerability/);
      } else if (outcome === 'array-report') {
        assert.equal(result.status, 1);
        assert.match(result.stderr, /no vulnerabilities object/);
      } else if (outcome === 1) {
        assert.equal(result.status, 1);
        assert.match(result.stderr, /without accounted advisory findings/);
      } else {
        assert.equal(result.status, 1);
        assert.match(result.stderr, /npm audit did not complete normally/);
      }
      if ([0, 1, 'accepted', 'array-report', 'null-finding', 'development-advisory'].includes(outcome)) {
        const retained = readFileSync(path.join(directory, 'audit-evidence', 'npm-audit.json'), 'utf8');
        assert.equal(retained, JSON.stringify(payload));
      }
      if (![0, 'accepted'].includes(outcome)) assert.doesNotMatch(result.stdout, /npm audit completed/);
    } finally {
      rmSync(directory, {recursive: true, force: true});
    }
  });
}
