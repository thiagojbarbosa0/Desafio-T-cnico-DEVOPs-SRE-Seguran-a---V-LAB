// Standalone TypeScript/TSX *syntax* validation (not an npm build or type check).
// Uses local TypeScript if installed, otherwise the globally installed package.
const fs = require('fs');
const path = require('path');
const cp = require('child_process');
const root = path.resolve(__dirname, '..');
let ts;
try {
  ts = require(require.resolve('typescript', { paths: [path.join(root, 'frontend')] }));
} catch {
  try {
    const globalRoot = cp.execFileSync('npm', ['root', '-g'], { encoding: 'utf8' }).trim();
    ts = require(path.join(globalRoot, 'typescript'));
  } catch {
    console.log('TypeScript parser unavailable: syntax validation skipped (not passed)');
    process.exit(2);
  }
}
const sources = [
  'frontend/src/api.ts',
  'frontend/src/interfaces.d.ts',
  'frontend/src/components/ChatInterface/ChatInterface.tsx',
  'frontend/src/firebaseClient.ts',
  'frontend/src/components/UserChats/UserChats.tsx',
];
let failed = false;
for (const rel of sources) {
  const source = fs.readFileSync(path.join(root, rel), 'utf8');
  const ast = ts.createSourceFile(rel, source, ts.ScriptTarget.Latest, true,
    rel.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  if (ast.parseDiagnostics.length) {
    failed = true;
    for (const diag of ast.parseDiagnostics) {
      console.error(`${rel}: ${ts.flattenDiagnosticMessageText(diag.messageText, '\n')}`);
    }
  } else console.log(`Syntax OK: ${rel}`);
}
if (failed) process.exit(1);
console.log('TypeScript/TSX syntax checks passed; full npm type-check remains unverified.');
