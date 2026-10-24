import test from 'node:test';
import assert from 'node:assert/strict';
import {transition, initialState, resolveRoute} from '../model.mjs';
test('permission revocation stops observation and drops displayed data',()=>{
 let s=transition(initialState,'grant'); s=transition(s,'observe');
 assert.equal(s.observing,true); s=transition(s,'revoke');
 assert.equal(s.observing,false); assert.equal(s.permission,'revoked'); assert.equal(s.telemetry,null);
});
test('Stop is unconditional and never enables gameplay',()=>{
 for(const event of ['grant','observe','offline','recover','confirm','stop']) {
  const s=transition(transition(initialState,event),'stop');
  assert.equal(s.observing,false); assert.equal(s.executionEnabled,false); assert.equal(s.status,'stopped');
 }
});
test('stale recovery does not fabricate captured data or auto-resume',()=>{
 const s=transition(transition(transition(initialState,'grant'),'stale'),'recover');
 assert.equal(s.telemetry,null); assert.equal(s.observing,false); assert.equal(s.executionEnabled,false);
});
test('direct public routes resolve distinctly and reject absent routes',()=>{
 for(const p of ['/','/features','/games/world-of-warcraft','/platforms/android','/legal']) assert.equal(resolveRoute(p).path,p);
 assert.equal(resolveRoute('/absent').found,false);
});
test('surface identifiers from URLs cannot become HTML attributes', async()=>{
 const {parseSurface}=await import('../model.mjs');
 assert.equal(parseSurface('" onmouseover="alert(1)'), 'site');
 for(const surface of ['site','android','windows','control','library'])assert.equal(parseSurface(surface),surface);
});
