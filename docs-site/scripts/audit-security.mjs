import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

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
  const failure = auditFailure(report);
  if (failure) {
    process.stderr.write(`${failure}\n`);
    process.exit(1);
  }
  process.stdout.write(auditSummary(report));
}

if (process.argv[1] === scriptPath) {
  main();
}
