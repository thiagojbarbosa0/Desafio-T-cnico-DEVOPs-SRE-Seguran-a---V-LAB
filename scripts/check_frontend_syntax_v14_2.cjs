// Parse every TypeScript and TSX source, even when npm dependencies are absent.
// This is a syntax-only guard, NEVER a substitute for `npm run build`.
const fs = require('node:fs');
const path = require('node:path');
const cp = require('node:child_process');
const root = path.resolve(__dirname, '..');
let ts;
try {
  ts = require(require.resolve('typescript', { paths: [path.join(root, 'frontend')] }));
} catch {
  try {
    const npmRoot = cp.execFileSync('npm', ['root', '-g'], { encoding: 'utf8' }).trim();
    ts = require(path.join(npmRoot, 'typescript'));
  } catch {
    process.stderr.write('TypeScript parser indisponível; não é possível afirmar que a sintaxe passou.\n');
    process.exit(2);
  }
}
const files=[];
function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(abs);
    else if (/\.tsx?$/.test(entry.name)) files.push(abs);
  }
}
walk(path.join(root, 'frontend/src'));
let failures=0;
for (const abs of files) {
  const rel = path.relative(root, abs);
  const kind=abs.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const parsed=ts.createSourceFile(rel, fs.readFileSync(abs,'utf8'), ts.ScriptTarget.Latest, true, kind);
  for (const error of parsed.parseDiagnostics) {
    failures++;
    const loc=parsed.getLineAndCharacterOfPosition(error.start || 0);
    console.error(`${rel}:${loc.line+1}:${loc.character+1}: ${ts.flattenDiagnosticMessageText(error.messageText, '\n')}`);
  }
}
console.log(`TypeScript/TSX: ${files.length} arquivos analisados, ${failures} erros de sintaxe.`);
if (failures) process.exit(1);
console.log('Sintaxe OK; tipagem completa, resolução de módulos e bundle Vite dependem do build npm.');
