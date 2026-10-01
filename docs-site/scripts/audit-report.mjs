// Severity floors for the docs-site production dependency tree.
//
// The docusaurus stack carries a standing set of high-severity advisories in
// its transitive dependencies that no forward upgrade clears: npm's own
// remediation for the current set resolves to an older `@docusaurus/core`,
// flagged semver-major. Blocking every pull request on advisories no one in
// this repository can act on stops all work rather than improving security, so
// that stack is floored at `critical` while every other root stays at `high`.
//
// The relaxation is scoped by reachability, not by package name: a package
// drops to the relaxed floor only when EVERY production root that reaches it is
// listed below. A dependency shared with react or prism-react-renderer keeps
// the default floor, and a package the lockfile walk cannot place keeps it too.
export const RELAXED_ROOTS = Object.freeze([
  '@docusaurus/core',
  '@docusaurus/preset-classic',
  '@easyops-cn/docusaurus-search-local',
]);
export const RELAXED_FLOOR = 'critical';
export const DEFAULT_FLOOR = 'high';

// A Map, not an object literal: `RANK.constructor` and `RANK.__proto__` resolve
// through `Object.prototype` on a literal, so a severity string colliding with
// an inherited key would pass the unknown-severity guard below as a function and
// then compare false against the floor -- ranking the advisory as harmless,
// which is the behaviour that guard exists to prevent.
const RANK = new Map([
  ['info', 0],
  ['low', 1],
  ['moderate', 2],
  ['high', 3],
  ['critical', 4],
]);

function floorFor(roots) {
  const relaxed = roots !== undefined
    && roots.size > 0
    && [...roots].every((root) => RELAXED_ROOTS.includes(root));
  return relaxed ? RELAXED_FLOOR : DEFAULT_FLOOR;
}

/**
 * Describe why the audit blocks, or return null when it does not.
 *
 * `rootsByPackage` maps a package name to the direct dependencies that reach
 * it, as produced by `audit-scope.mjs`.
 */
export function auditFailure(report, rootsByPackage) {
  if (Object.hasOwn(report, 'error')) {
    return `npm audit failed: ${JSON.stringify(report.error)}`;
  }
  if (
    !Object.hasOwn(report, 'vulnerabilities')
    || typeof report.vulnerabilities !== 'object'
    || report.vulnerabilities === null
  ) {
    return 'npm audit report has no vulnerabilities object';
  }

  const blocking = [];
  for (const [name, vulnerability] of Object.entries(report.vulnerabilities)) {
    const rank = RANK.get(vulnerability.severity);
    if (rank === undefined) {
      return `npm audit reported unknown severity ${JSON.stringify(vulnerability.severity)} `
        + `for ${name}`;
    }
    const roots = rootsByPackage.get(name);
    const floor = floorFor(roots);
    if (rank >= RANK.get(floor)) {
      const via = roots === undefined ? 'unresolved' : [...roots].sort().join(', ');
      blocking.push(`${name} (${vulnerability.severity}, floor ${floor}, via ${via})`);
    }
  }

  return blocking.length > 0
    ? `Docs-site npm vulnerabilities at or above their severity floor:\n  ${blocking.sort().join('\n  ')}`
    : null;
}
