/** Deterministic before/after real TypeScript callbacks; mocked auth/fetch, no browser. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const ts=require(require.resolve('typescript',{paths:[root+'/frontend']}));
const before='audit/baseline/profile_api_original.ts.txt',after='frontend/src/api.ts';
async function scenario(file){
 const auth={currentUser:null};let callback,release;const state={about:''};
 const modules={'jquery':()=>({val(){}}),'./firebaseConfig':{},'firebase/app':{initializeApp:()=>({})},'firebase/database':{getDatabase:()=>({})},'./firebaseClient':{auth},'firebase/auth':{getAuth:()=>auth,onAuthStateChanged:(_,cb)=>{callback=cb;return()=>{};}},'react-toastify':{toast:{error(){throw Error('unexpected toast');}}}};
 function load(name){
  const js=ts.transpileModule(fs.readFileSync(root+'/'+name,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020,esModuleInterop:true}}).outputText.replaceAll('import.meta.env.VITE_API_BASE_URL','""');
  const m={exports:{}};
  vm.runInNewContext(js,{module:m,exports:m.exports,require:n=>{assert.ok(n in modules,n);return modules[n];},AbortController,console,alert(){throw Error('unexpected alert');},fetch:()=>auth.currentUser.uid==='A'?new Promise(r=>{release=r;}):Promise.resolve({ok:true,json:async()=>({about:'BOB_PROFILE'})})},{timeout:1000});return m.exports;
 }
 modules['./sessionGate']=load('frontend/src/sessionGate.ts');
 const api=load(file);await api.setProfileInfoIfLoggedIn(()=>{},()=>{},()=>{},()=>{},()=>{},v=>{state.about=v;});
 const user=uid=>({uid,getIdToken:async()=> 'SYNTHETIC_'+uid});
 auth.currentUser=user('A');const a=callback(auth.currentUser);for(let i=0;i<8;i++)await Promise.resolve();assert.equal(typeof release,'function');
 auth.currentUser=user('B');await callback(auth.currentUser);assert.equal(state.about,'BOB_PROFILE');
 release({ok:true,json:async()=>({about:'ALICE_PRIVATE_PROFILE'})});await a;
 return state.about;
}
(async()=>{
 const baseline=await scenario(before),corrected=await scenario(after);
 assert.equal(baseline,'ALICE_PRIVATE_PROFILE');assert.equal(corrected,'BOB_PROFILE');
 const report={validated:true,scope:'Exact upstream TypeScript and corrected API callbacks; mocked Firebase/fetch, no browser or unauthorized server read',precondition:'Two authenticated users successively use the same client while a profile request remains pending',before:'Delayed A profile overwrites B state',after:'Delayed A response discarded; B profile preserved',source_sha256:{}};
 for(const f of [before,after,'frontend/src/sessionGate.ts','scripts/prove_profile_race_work.cjs'])report.source_sha256[f]=crypto.createHash('sha256').update(fs.readFileSync(root+'/'+f)).digest('hex');
 fs.writeFileSync(root+'/evidence/generated/PROFILE_RACE_WORK.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
