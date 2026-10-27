#!/usr/bin/env node
/** Execute compiled real API profile auth callback under controlled fake Firebase.
 * Tests stale A response rejection, B state, logout cleanup and cancellation.
 */
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const vm = require('node:vm');
const root = path.resolve(__dirname,'..');
const ts = require(require.resolve('typescript',{paths:[path.join(root,'frontend'),root]}));
function loadTS(file,modules) {
  let src=fs.readFileSync(path.join(root,'frontend/src',file),'utf8');
  const js=ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText
   .replaceAll('import.meta.env.VITE_API_BASE_URL','""');
  const m={exports:{}};
  vm.runInNewContext(js,{exports:m.exports,module:m,require:name=>{
    if (!(name in modules)) throw new Error('Unexpected import: '+name);
    return modules[name];
  },fetch:(...args)=>globalThis.fetch(...args), AbortController, alert(){ throw new Error('unexpected alert'); },console},
  {filename:file,timeout:1000});
  return m.exports;
}
const gate=loadTS('sessionGate.ts',{});
const auth={currentUser:null};
let cb,active=true,alerts=0,aborted=0;const queue=[];
const modules={
  'firebase/auth':{
    onAuthStateChanged(_,handler){cb=handler;return()=>{active=false;};},
    createUserWithEmailAndPassword(){throw new Error('unused');},
    signInWithEmailAndPassword(){throw new Error('unused');},
  },
  './firebaseClient':{auth},
  './sessionGate':gate,
  'react-toastify':{toast:{error(){alerts++;},success(){throw new Error('unexpected success');}}},
};
const api=loadTS('api.ts',modules);
const profile={majors:['old'],minors:['old'],year:'old',college:'old',courses:['old'],about:'old'};
const setters=['majors','minors','year','college','courses','about'].map(key=>value=>{profile[key]=value;});
const stop=api.setProfileInfoIfLoggedIn(...setters);
assert.equal(typeof cb,'function');
const oldFetch=globalThis.fetch;
globalThis.fetch=(url,opts)=>new Promise(resolve=>{
  opts.signal.addEventListener('abort',()=>{aborted++;});
  queue.push({url,opts,resolve});
});
const tick=async()=>{for(let i=0;i<5;i++) await Promise.resolve();};
const a={uid:'A',getIdToken:async()=> 'synthetic-A'};
const b={uid:'B',getIdToken:async()=> 'synthetic-B'};
(async()=>{
 try {
  auth.currentUser=a;
  const jobA=cb(a);await tick();
  assert.equal(queue.length,1);
  assert.equal(profile.year,'');
  auth.currentUser=b;
  const jobB=cb(b);await tick();
  assert.equal(queue.length,2);
  assert.equal(aborted,1);
  queue[0].resolve({ok:true,json:async()=>({year:'YEAR A',about:'SECRET A',majors:['A']})});
  await jobA;
  assert.notEqual(profile.about,'SECRET A');
  queue[1].resolve({ok:true,json:async()=>({year:'YEAR B',about:'PROFILE B',majors:['B'],minors:['minor'],courses:['course'],college:'college'})});
  await jobB;
  assert.equal(profile.about,'PROFILE B');
  assert.equal(profile.year,'YEAR B');
  assert.equal(profile.majors[0],'B');
  auth.currentUser=null;await cb(null);
  assert.equal(profile.about,'');
  assert.equal(profile.year,'');
  assert.equal(profile.majors.length,0);
  assert.equal(alerts,0);
  stop();assert.equal(active,false);
  console.log('Profile auth runtime: stale A discarded, B loaded, logout wiped all fields, abort quiet');
 }finally {globalThis.fetch=oldFetch;}
})().catch(e=>{console.error(e);process.exitCode=1;});
