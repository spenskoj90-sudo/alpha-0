import test from 'node:test';
import assert from 'node:assert/strict';
import {createWorkspace,reduceWorkspace,selectRows} from '../workspace-model.mjs';
test('fictional data is opt-in and cannot enable game execution',()=>{
 let s=createWorkspace();assert.equal(s.sample,false);assert.equal(s.executionEnabled,false);
 s=reduceWorkspace(s,{type:'sample',value:true});assert.equal(s.sample,true);assert.equal(s.executionEnabled,false);
});
test('build comparison is bounded and keeps independent workspace choices',()=>{
 let s=reduceWorkspace(createWorkspace(),{type:'sample',value:true});for(const id of ['balanced','reserve','mobility'])s=reduceWorkspace(s,{type:'compare',id});
 assert.deepEqual(s.compare,['balanced','reserve']);
 s=reduceWorkspace(s,{type:'quest',id:'survey'});assert.deepEqual(s.compare,['balanced','reserve']);assert.deepEqual(s.quests,['survey']);
});
test('talent points and recipe quantities reject out-of-range and nonnumeric input',()=>{
 let s=reduceWorkspace(createWorkspace(),{type:'sample',value:true});for(let i=0;i<20;i++)s=reduceWorkspace(s,{type:'talent',id:'focus',delta:1});
 assert.equal(s.talents.focus,3);s=reduceWorkspace(s,{type:'quantity',value:'invalid'});assert.equal(s.quantity,1);
 s=reduceWorkspace(s,{type:'quantity',value:10000});assert.equal(s.quantity,99);
 s=reduceWorkspace(s,{type:'reset'});assert.equal(s.sample,false);assert.deepEqual(s.talents,{});
});
test('table search, sorting and page bounds do not invent rows',()=>{
 const rows=[{id:'a',name:['Образец A','Sample A'],price:12},{id:'b',name:['Образец B','Sample B'],price:4}];
 assert.deepEqual(selectRows(rows,{query:'Sample B',sort:'price',page:99,pageSize:1},'en').rows.map(r=>r.id),['b']);
 assert.equal(selectRows(rows,{query:'absent',sort:'price',page:0,pageSize:5},'en').total,0);
});

test('fixture opt-out clears drafts and model disallows hidden sample mutations',()=>{
 let s=reduceWorkspace(createWorkspace(),{type:'sample',value:true});
 for(const action of [{type:'compare',id:'balanced'},{type:'talent',id:'focus',delta:1},{type:'quantity',value:4},{type:'quest',id:'survey'},{type:'item',id:'ore'},{type:'arena',id:'reserve'}])s=reduceWorkspace(s,action);
 assert.deepEqual(reduceWorkspace(s,{type:'sample',value:false}),createWorkspace());
 s=createWorkspace();for(const action of [{type:'compare',id:'balanced'},{type:'quantity',value:7},{type:'item',id:'ore'},{type:'arena',id:'reserve'},{type:'talent',id:'focus',delta:1}])s=reduceWorkspace(s,action);
 assert.deepEqual(s,createWorkspace());
});
