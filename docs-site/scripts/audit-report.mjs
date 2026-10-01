// Every advisory blocks, including development and documentation tooling.
const SEVERITIES = new Set(['info', 'low', 'moderate', 'high', 'critical']);

/** Return the blocking findings, or null for a complete audit with none. */
export function auditFailure(report) {
  if (typeof report !== 'object' || report === null || Array.isArray(report)) {
    return 'npm audit report must be an object';
  }
  if (Object.hasOwn(report, 'error')) {
    return `npm audit failed: ${JSON.stringify(report.error)}`;
  }
  if (
    !Object.hasOwn(report, 'vulnerabilities')
    || typeof report.vulnerabilities !== 'object'
    || report.vulnerabilities === null
    || Array.isArray(report.vulnerabilities)
  ) {
    return 'npm audit report has no vulnerabilities object';
  }

  const blocking = [];
  for (const [name, vulnerability] of Object.entries(report.vulnerabilities)) {
    if (!SEVERITIES.has(vulnerability.severity)) {
      return `npm audit reported unknown severity ${JSON.stringify(vulnerability.severity)} `
        + `for ${name}`;
    }
    blocking.push(`${name} (${vulnerability.severity})`);
  }

  return blocking.length > 0
    ? `Docs-site npm audit found known vulnerabilities:\n  ${blocking.sort().join('\n  ')}`
    : null;
}
