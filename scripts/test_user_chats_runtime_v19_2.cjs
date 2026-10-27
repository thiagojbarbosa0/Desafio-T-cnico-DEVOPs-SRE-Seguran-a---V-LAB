#!/usr/bin/env node
/** Run real compiled UserChats effect/auth callbacks with isolated module stubs.
 * No real user, network, Firebase project, or browser dependencies.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
// Resolve from frontend/node_modules on CI; also works with globally installed TS.
const ts = require(require.resolve('typescript', { paths: [path.join(root, 'frontend'), root] }));
function transpile(source, jsx = false) {
  const output = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020,
    jsx: jsx ? ts.JsxEmit.ReactJSX : ts.JsxEmit.None,
  }});
  return output.outputText;
}
function importStub(source, filename, modules) {
  const m = { exports: {} };
  vm.runInNewContext(transpile(source, filename.endsWith('.tsx')).replaceAll('import.meta.env.VITE_API_BASE_URL', '""'), {
    exports: m.exports, module: m, require: name => {
      if (!(name in modules)) throw new Error('Unexpected module: ' + name);
      return modules[name];
    }, console, AbortController, fetch: (...args) => globalThis.fetch(...args),
  }, { filename, timeout: 1000 });
  return m.exports;
}
const sessionSource = fs.readFileSync(path.join(root, 'frontend/src/sessionGate.ts'), 'utf8');
const { SessionGate } = importStub(sessionSource, 'sessionGate.ts', {});
const state = [];
let stateIndex = 0;
let subscriber;
let cleanup;
let fetchQueue = [];
let abortCount = 0;
let toastCount = 0;
const auth = { currentUser: null };
const jsx = { jsx() { return null; }, jsxs() { return null; }, Fragment: Symbol('fragment') };
const useState = initial => {
  const slot = stateIndex++;
  state[slot] = initial;
  return [initial, val => { state[slot] = typeof val === 'function' ? val(state[slot]) : val; }];
};
const modules = {
  react: {
    useState,
    useRef(value) { return { current: value }; },
    useEffect(fn) { cleanup = fn(); },
  },
  'react/jsx-runtime': jsx,
  '@mui/material': { List() {}, ListItem() {}, ListItemText() {}, Typography() {} },
  'firebase/auth': { onAuthStateChanged(_, cb) { subscriber = cb; return () => { subscriber = null; }; } },
  '../../firebaseClient': { auth },
  '../../sessionGate': { SessionGate },
  'react-toastify': { toast: { error() { toastCount++; } } },
};
const source = fs.readFileSync(path.join(root, 'frontend/src/components/UserChats/UserChats.tsx'), 'utf8');
const { default: UserChats } = importStub(source, 'UserChats.tsx', modules);
UserChats();
assert.equal(typeof subscriber, 'function');
const a = { uid: 'A', getIdToken: async () => 'synthetic-A' };
const b = { uid: 'B', getIdToken: async () => 'synthetic-B' };
const originalFetch = globalThis.fetch;
globalThis.fetch = (_url, options) => new Promise(resolve => {
  const request = { options, resolve };
  options.signal.addEventListener('abort', () => abortCount++);
  fetchQueue.push(request);
});
const tick = async () => { for(let i=0;i<4;i++) await Promise.resolve(); };
(async () => {
  try {
    auth.currentUser = a;
    const aJob = subscriber(a);
    await tick();
    assert.equal(fetchQueue.length, 1);
    auth.currentUser = b;
    const bJob = subscriber(b);
    await tick();
    assert.equal(fetchQueue.length, 2);
    assert.equal(abortCount, 1);
    assert.equal(state[0].length, 0);
    fetchQueue[0].resolve({ ok: true, json: async () => ({ chats: [{ title: 'PRIVATE A', timestamp: '' }] }) });
    await aJob;
    assert.equal(state[0].length, 0, 'late A response must not enter B session');
    fetchQueue[1].resolve({ ok: true, json: async () => ({ chats: [{ title: 'B CHAT', timestamp: '' }] }) });
    await bJob;
    assert.equal(state[0][0].title, 'B CHAT');
    auth.currentUser = null;
    await subscriber(null);
    assert.equal(state[0].length, 0, 'logout must clear visible chats immediately');
    assert.equal(state[2], false);
    assert.equal(toastCount, 0, 'aborted A request must not show spurious error');
    cleanup();
    console.log('UserChats async integration: A->B stale response rejected, B displayed, logout wiped data, abort was quiet');
  } finally { globalThis.fetch = originalFetch; }
})().catch(e => { console.error(e); process.exitCode = 1; });
