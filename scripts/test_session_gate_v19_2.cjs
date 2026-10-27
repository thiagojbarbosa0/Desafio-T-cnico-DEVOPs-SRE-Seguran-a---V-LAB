#!/usr/bin/env node
/** Real execution of the compiled TypeScript session generation guard.
 * Static wiring assertions below complement, but do not replace, browser tests.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
// Resolve from frontend/node_modules on CI; also works with globally installed TS.
const ts = require(require.resolve('typescript', { paths: [path.join(root, 'frontend'), root] }));
const source = fs.readFileSync(path.join(root, 'frontend/src/sessionGate.ts'), 'utf8');
const result = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  reportDiagnostics: true,
});
const errors = (result.diagnostics || []).filter(x => x.category === ts.DiagnosticCategory.Error);
assert.equal(errors.length, 0, 'sessionGate.ts must transpile without errors');
const m = { exports: {} };
vm.runInNewContext(result.outputText, { module: m, exports: m.exports }, { timeout: 1000 });
const { SessionGate } = m.exports;
assert.equal(typeof SessionGate, 'function');
const gate = new SessionGate();
const a1 = gate.begin('alice');
assert.equal(gate.isCurrent('alice', a1), true);
assert.equal(gate.isCurrent('bob', a1), false);
const b = gate.begin('bob');
assert.equal(gate.isCurrent('alice', a1), false, 'A data must be invalidated when B logs in');
assert.equal(gate.isCurrent('bob', b), true);
const a2 = gate.begin('alice');
assert.equal(gate.isCurrent('alice', a1), false, 'A->B->A must not resurrect old A work');
assert.equal(gate.isCurrent('alice', a2), true);
const out = gate.begin(null);
assert.equal(gate.isCurrent('alice', a2), false);
assert.equal(gate.isCurrent(null, out), true);
const a3 = gate.begin('alice');
const a4 = gate.begin('alice');
assert.equal(gate.isCurrent('alice', a3), false, 'new generation of same user invalidates old fetch');
assert.equal(gate.isCurrent('alice', a4), true);

// Verify the UI actually consumes the guard and resets sensitive state.
function src(file) { return fs.readFileSync(path.join(root, 'frontend/src', file), 'utf8'); }
const chats = src('components/UserChats/UserChats.tsx');
const dashboard = src('api.ts');
const chatUi = src('components/ChatInterface/ChatInterface.tsx');
const nav = src('components/nav/Nav.tsx');
for (const code of [chats, dashboard, chatUi]) {
  assert.match(code, /new SessionGate\(\)/);
  assert.match(code, /\.isCurrent\(/);
}
assert.match(chats, /setChats\(\[\]\)/);
assert.match(chats, /pending\?\.abort\(\)/);
assert.match(dashboard, /clearProfile\(\)/);
assert.match(dashboard, /sameUser\(user\.uid\)/);
assert.match(chatUi, /setLines\(\[\]\)/);
assert.match(chatUi, /expectedUid|saveCourseSphereChat\(chatId\.current, \[userMessage, botMessage\], uid\)/);
assert.match(nav, /await auth\.signOut\(\)/);
console.log('Session guard: 11 runtime assertions + source wiring/cleanup checks passed');
