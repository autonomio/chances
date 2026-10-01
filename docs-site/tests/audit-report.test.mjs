import assert from 'node:assert/strict';
import test from 'node:test';

import {auditFailure} from '../scripts/audit-report.mjs';

const report = (severity) => ({vulnerabilities: {victim: {severity}}});

test('fails closed on npm audit errors and incomplete reports', () => {
  assert.match(auditFailure({error: {code: 'ENOAUDIT'}}), /npm audit failed.*ENOAUDIT/);
  assert.equal(auditFailure({metadata: {}}), 'npm audit report has no vulnerabilities object');
  assert.equal(auditFailure({vulnerabilities: {}}), null);
});

for (const severity of ['info', 'low', 'moderate', 'high', 'critical']) {
  test(`every known advisory blocks at ${severity} severity`, () => {
    assert.ok(auditFailure(report(severity)).includes(`victim (${severity})`));
  });
}

for (const severity of ['catastrophic', 'constructor', 'toString', '__proto__', 'valueOf']) {
  test(`unknown severity fails closed: ${severity}`, () => {
    assert.match(auditFailure(report(severity)), /unknown severity/);
  });
}

for (const vulnerabilities of [[], [{severity: 'critical'}]]) {
  test(`array vulnerability reports fail closed (${vulnerabilities.length} entries)`, () => {
    assert.equal(auditFailure({vulnerabilities}), 'npm audit report has no vulnerabilities object');
  });
}

for (const invalid of [null, [], false, 'report']) {
  test(`non-object audit reports fail closed (${JSON.stringify(invalid)})`, () => {
    assert.equal(auditFailure(invalid), 'npm audit report must be an object');
  });
}
