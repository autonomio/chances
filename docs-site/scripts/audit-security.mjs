import {spawnSync} from 'node:child_process';
import {mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

import {acceptedPackages, auditExecutionFailure, reviewedExceptions, verifyInstalledExceptions} from './audit-exceptions.mjs';
import {auditFailure} from './audit-report.mjs';

const scriptPath = fileURLToPath(import.meta.url);
const siteRoot = path.resolve(path.dirname(scriptPath), '..');
export function auditSummary(report) {
  const findings = Object.entries(report.vulnerabilities).sort(([left], [right]) => left.localeCompare(right));
  const counts = new Map();
  for (const [, vulnerability] of findings) {
    counts.set(vulnerability.severity, (counts.get(vulnerability.severity) || 0) + 1);
  }
  const severities = [...counts].map(([severity, count]) => `${severity}=${count}`).join(', ');
  const lines = [
    'Docs-site npm audit completed.',
    `Reported vulnerable packages: ${findings.length}${severities ? ` (${severities})` : ''}.`,
  ];
  if (findings.length) {
    lines.push('Findings:', ...findings.map(([name, vulnerability]) => `  ${name} (${vulnerability.severity})`));
  }
  return `${lines.join('\n')}\n`;
}

function main() {
  const result = spawnSync('npm', ['audit', '--include=dev', '--json'], {
    cwd: siteRoot,
    encoding: 'utf8',
    timeout: 120000,
  });
  if (result.error || result.signal || ![0, 1].includes(result.status)) {
    const reason = result.error?.message || result.signal || `status ${result.status}`;
    process.stderr.write(`npm audit did not complete normally: ${reason}\n`);
    process.exit(1);
  }
  if (!result.stdout) {
    process.stderr.write(result.stderr || 'npm audit produced no JSON output\n');
    process.exit(result.status || 1);
  }
  const report = JSON.parse(result.stdout);
  // Retain original findings, including accepted advisories, in CI evidence.
  const evidence = path.join(siteRoot, 'audit-evidence', 'npm-audit.json');
  mkdirSync(path.dirname(evidence), {recursive: true});
  writeFileSync(evidence, result.stdout);
  if (typeof report !== 'object' || report === null || Array.isArray(report)
      || typeof report.vulnerabilities !== 'object' || report.vulnerabilities === null
      || Array.isArray(report.vulnerabilities) || Object.hasOwn(report, 'error')) {
    process.stderr.write(`${auditFailure(report)}\n`);
    process.exit(1);
  }
  const entries = JSON.parse(readFileSync(path.join(siteRoot, 'security-exceptions.json'), 'utf8'));
  const reviewed = reviewedExceptions(entries);
  const packages = JSON.parse(readFileSync(path.join(siteRoot, 'package-lock.json'), 'utf8')).packages;
  verifyInstalledExceptions(siteRoot, packages, reviewed);
  const accepted = acceptedPackages(report, packages, reviewed);
  const failure = auditExecutionFailure(result, report, auditFailure(report, accepted));
  if (failure) {
    process.stderr.write(`${failure}\n`);
    process.exit(1);
  }
  process.stdout.write(auditSummary(report));
  for (const entry of reviewed.values()) {
    if (accepted.has(entry.package)) {
      process.stdout.write(`Accepted known finding until ${entry.expires} 00:00 UTC: ${entry.id}, ${entry.package}@${entry.version}; owner ${entry.approved_by}\n`);
    }
  }
  process.stdout.write(`No unaccepted findings; ${accepted.size} reported package findings accepted. Raw audit: ${evidence}\n`);
}

if (process.argv[1] === scriptPath) {
  main();
}
