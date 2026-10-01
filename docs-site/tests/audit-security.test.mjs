import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {chmodSync, mkdtempSync, rmSync, writeFileSync} from 'node:fs';
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

const auditScript = fileURLToPath(new URL('../scripts/audit-security.mjs', import.meta.url));
for (const outcome of [0, 1, 2, 'signal', 'missing', 'array-report', 'development-advisory']) {
  test(`the audit command handles complete fixture JSON with process outcome ${outcome}`, () => {
    const directory = mkdtempSync(path.join(os.tmpdir(), 'chances-audit-process-'));
    try {
      if (outcome !== 'missing') {
        const finish = outcome === 'signal'
          ? "process.kill(process.pid, 'SIGTERM')"
          : `process.exit(${['array-report', 'development-advisory'].includes(outcome) ? 0 : outcome})`;
        const executable = path.join(directory, 'npm');
        const payload = outcome === 'array-report' ? {vulnerabilities: []}
          : outcome === 'development-advisory'
            ? {vulnerabilities: {tool: {severity: 'low'}}} : {vulnerabilities: {}};
        writeFileSync(executable,
          `#!${process.execPath}\nif (process.argv.includes('--omit=dev') || !process.argv.includes('--include=dev')) process.exit(3);\nprocess.stdout.write(${JSON.stringify(JSON.stringify(payload))}, () => { ${finish}; });\n`);
        chmodSync(executable, 0o755);
      }
      const result = spawnSync(process.execPath, [auditScript], {
        encoding: 'utf8', env: {...process.env, PATH: directory},
      });
      assert.equal(result.error, undefined);
      if (outcome === 0 || outcome === 1) {
        assert.equal(result.status, 0, result.stderr);
        assert.match(result.stdout, /npm audit completed/);
      } else if (outcome === 'development-advisory') {
        assert.equal(result.status, 1);
        assert.match(result.stderr, /tool \(low\)/);
        assert.doesNotMatch(result.stdout, /npm audit completed/);
      } else if (outcome === 'array-report') {
        assert.equal(result.status, 1);
        assert.match(result.stderr, /no vulnerabilities object/);
        assert.doesNotMatch(result.stdout, /npm audit completed/);
      } else {
        assert.equal(result.status, 1);
        assert.match(result.stderr, /npm audit did not complete normally/);
        assert.doesNotMatch(result.stdout, /npm audit completed/);
      }
    } finally {
      rmSync(directory, {recursive: true, force: true});
    }
  });
}
