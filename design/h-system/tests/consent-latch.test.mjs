import test from 'node:test';
import assert from 'node:assert/strict';
import {initialState,transition} from '../model.mjs';

test('Stop requires fresh simulated consent before observing again',()=>{
 let s=transition(initialState,'grant');
 s=transition(s,'observe');assert.equal(s.observing,true);
 s=transition(s,'stop');assert.equal(s.status,'stopped');assert.equal(s.consentRequired,true);
 s=transition(s,'observe');assert.equal(s.observing,false);
 s=transition(s,'recover');assert.equal(s.status,'stopped');
 s=transition(s,'observe');assert.equal(s.observing,false);
 s=transition(s,'grant');assert.equal(s.consentRequired,false);
 s=transition(s,'observe');assert.equal(s.observing,true);
});

test('Source invalidation always disarms demo observer before recovery',()=>{
 for(const event of ['offline','stale','timeout','revoke','deny']) {
  let s=transition(transition(initialState,'grant'),'observe');
  s=transition(s,event);assert.equal(s.observing,false,event);
  assert.equal(s.consentRequired,true,event);
  s=transition(s,'recover');s=transition(s,'observe');
  assert.equal(s.observing,false,event);
  s=transition(s,'grant');s=transition(s,'observe');
  assert.equal(s.observing,true,event);
 }
});

test('Stopped status never restarts without a fresh ready state',()=>{
 const stopped={...initialState,permission:'granted',status:'stopped',consentRequired:false};
 assert.equal(transition(stopped,'observe').observing,false);
});
