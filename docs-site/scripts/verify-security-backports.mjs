import {createHash} from 'node:crypto';
import {readFileSync, readdirSync, realpathSync} from 'node:fs';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export function verifySecurityBackports(root = siteRoot) {
  const require = createRequire(path.join(root, 'package.json'));
  const records = JSON.parse(readFileSync(path.join(root, 'vendor/provenance.json'), 'utf8'));
  const lock = JSON.parse(readFileSync(path.join(root, 'package-lock.json'), 'utf8'));
  for (const [name, record] of Object.entries(records)) {
    const directory = path.join(root, 'vendor', name);
    const expected = realpathSync(path.join(directory, 'index.js'));
    const actual = realpathSync(require.resolve(name));
    if (actual !== expected) throw new Error(`${name} does not resolve to its reviewed backport`);
    const manifest = JSON.parse(readFileSync(path.join(directory, 'package.json'), 'utf8'));
    if (manifest.name !== name || manifest.version !== record.local_version) {
      throw new Error(`${name} backport identity differs from provenance`);
    }
    const files = [];
    function collectFiles(relative = '') {
      for (const entry of readdirSync(path.join(directory, relative), {withFileTypes: true})) {
        const file = path.posix.join(relative, entry.name);
        if (entry.isDirectory()) collectFiles(file);
        else if (entry.isFile()) files.push(file);
      }
    }
    collectFiles();
    files.sort();
    if (JSON.stringify(files) !== JSON.stringify(Object.keys(record.patched_sha256).sort())) {
      throw new Error(`${name} backport file inventory differs from provenance`);
    }
    for (const [file, digest] of Object.entries(record.patched_sha256)) {
      const actualDigest = createHash('sha256').update(readFileSync(path.join(directory, file))).digest('hex');
      if (actualDigest !== digest) throw new Error(`${name}/${file} differs from its reviewed digest`);
    }
    for (const [location, pkg] of Object.entries(lock.packages)) {
      if (pkg.dependencies?.[name]) {
        const consumer = createRequire(path.join(root, location, 'package.json'));
        if (realpathSync(consumer.resolve(name)) !== expected) {
          throw new Error(`${location} bypasses the reviewed ${name} backport`);
        }
      }
    }
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  verifySecurityBackports();
  process.stdout.write('Documentation security backport identities, files and consumers verified.\n');
}
