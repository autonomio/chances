import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {chmodSync, mkdtempSync, rmSync, writeFileSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';

import {auditFailure} from '../scripts/audit-report.mjs';
import {auditSummary} from '../scripts/audit-security.mjs';

test('reports permitted advisories without claiming zero vulnerabilities', () => {
  const report = {vulnerabilities: {
    zeta: {severity: 'high'}, alpha: {severity: 'moderate'}, beta: {severity: 'moderate'},
  }};
  const roots = new Map([
    ['zeta', new Set(['@docusaurus/core'])],
    ['alpha', new Set(['react'])], ['beta', new Set(['react'])],
  ]);
  assert.equal(auditFailure(report, roots), null);
  const summary = auditSummary(report);
  assert.match(summary, /meets the configured severity floors/);
  assert.match(summary, /Reported vulnerable packages: 3 \(moderate=2, high=1\)/);
  assert.match(summary, /Allowed findings:\n  alpha \(moderate\)\n  beta \(moderate\)\n  zeta \(high\)/);
  assert.doesNotMatch(summary, /no known|zero vulnerabilities|0 vulnerabilities/i);
});

test('reports an empty audit explicitly without listing fictional findings', () => {
  assert.equal(auditSummary({vulnerabilities: {}}),
    'Docs-site npm audit meets the configured severity floors.\nReported vulnerable packages: 0.\n');
});

test('the reporting change preserves the strict and relaxed severity policy', () => {
  const report = {vulnerabilities: {victim: {severity: 'high'}}};
  assert.match(auditFailure(report, new Map([['victim', new Set(['react'])]])), /floor high/);
  assert.equal(auditFailure(report, new Map([['victim', new Set(['@docusaurus/core'])]])), null);
  assert.match(auditFailure({vulnerabilities: {victim: {severity: 'critical'}}},
    new Map([['victim', new Set(['@docusaurus/core'])]])), /floor critical/);
});

const auditScript = fileURLToPath(new URL('../scripts/audit-security.mjs', import.meta.url));
for (const outcome of [0, 1, 2, 'signal', 'missing']) {
  test(`the audit command handles complete fixture JSON with process outcome ${outcome}`, () => {
    const directory = mkdtempSync(path.join(os.tmpdir(), 'chances-audit-process-'));
    try {
      if (outcome !== 'missing') {
        const finish = outcome === 'signal'
          ? "process.kill(process.pid, 'SIGTERM')"
          : `process.exit(${outcome})`;
        const executable = path.join(directory, 'npm');
        writeFileSync(executable,
          `#!${process.execPath}\nprocess.stdout.write(JSON.stringify({vulnerabilities: {}}), () => { ${finish}; });\n`);
        chmodSync(executable, 0o755);
      }
      const result = spawnSync(process.execPath, [auditScript], {
        encoding: 'utf8', env: {...process.env, PATH: directory},
      });
      assert.equal(result.error, undefined);
      if (outcome === 0 || outcome === 1) {
        assert.equal(result.status, 0, result.stderr);
        assert.match(result.stdout, /meets the configured severity floors/);
      } else {
        assert.equal(result.status, 1);
        assert.match(result.stderr, /npm audit did not complete normally/);
        assert.doesNotMatch(result.stdout, /meets the configured severity floors/);
      }
    } finally {
      rmSync(directory, {recursive: true, force: true});
    }
  });
}
