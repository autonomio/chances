import assert from 'node:assert/strict';
import test from 'node:test';

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
