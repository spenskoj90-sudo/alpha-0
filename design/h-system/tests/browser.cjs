/* Run with PLAYWRIGHT_MODULE pointing to an installed playwright package.
   CHROMIUM_EXECUTABLE is optional when Playwright owns its browser. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {spawn}=require('node:child_process');
const {once}=require('node:events');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const root=path.resolve(__dirname,'..');const server=spawn('python',['serve.py','--port','4176'],{cwd:root});server.stderr.resume();await once(server.stdout,'data');
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE||undefined,args:['--no-sandbox','--disable-dev-shm-usage']});
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let routes=0,checks=0;const {publicPages,productPages}=await import('../content.mjs');
 const targets={site:publicPages,...productPages};const output=process.env.H_QA_OUTPUT||'/tmp/sentinel-h-qa';fs.mkdirSync(output,{recursive:true});
 try{
 for(const endpoint of ['/..%2f..%2fetc%2fpasswd','/missing.woff2'])assert.equal((await page.request.get('http://127.0.0.1:4176'+endpoint)).status(),404);checks++;
 await page.goto('http://127.0.0.1:4176/?surface='+encodeURIComponent('" data-injected="yes'));await page.locator('h1').waitFor();assert.equal(await page.locator('[data-injected]').count(),0);assert.equal(await page.locator('#surface').inputValue(),'site');checks++;
 await page.goto('http://127.0.0.1:4176/?surface=site&lang=en');await page.locator('h1').waitFor();await page.evaluate(()=>document.fonts.ready);await page.locator('#theme').click();
 assert.equal(await page.locator('body').evaluate(e=>getComputedStyle(e).color),'rgb(24, 36, 51)','light theme must resolve dark foreground');
 assert.equal(await page.locator('body').evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(244, 246, 249)','light theme must paint light canvas');await page.locator('#theme').click();checks++;
 for(const viewport of [{width:320,height:844},{width:390,height:844},{width:768,height:1000},{width:1024,height:1000},{width:1440,height:1000}]){
 await page.setViewportSize(viewport);
 for(const lang of ['ru','en'])for(const [surface,pages]of Object.entries(targets))for(const p of pages){
  await page.goto(`http://127.0.0.1:4176${p.path}?surface=${surface}&lang=${lang}`);await page.locator('h1').waitFor();await page.evaluate(()=>document.fonts.ready);
  assert.equal(await page.locator('h1').innerText(),p.title[lang==='ru'?0:1]);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,`${surface}${p.path} ${lang} ${viewport.width} overflow`);
  const broken=await page.locator('a[href]').evaluateAll(links=>links.filter(a=>!['http:','https:'].includes(new URL(a.href).protocol)).length);assert.equal(broken,0);const hrefs=await page.locator('a[href]').evaluateAll(es=>es.map(e=>e.href));for(const href of hrefs){const u=new URL(href);if(u.origin==='http://127.0.0.1:4176'){const destination=u.searchParams.get('surface')||surface;const routeSet=destination==='library'?['/brand','/icons','/components']:(targets[destination]||[]).map(r=>r.path);assert.ok(routeSet.includes(u.pathname),`broken link ${href} on ${surface}${p.path}`);}}routes++;
 }
 }
 await page.setViewportSize({width:390,height:844});
 // Permission, observation, revoke, recovery and persistent Stop.
 await page.goto('http://127.0.0.1:4176/capture?surface=android&lang=en');await page.locator('#consent').check();await page.locator('[data-event=permission-dialog]').click();await page.locator('dialog [data-event=grant]').click();await page.locator('[data-event=observe]').click();assert.match(await page.locator('#observation-status').innerText(),/Demo observation/);checks++;
 await page.locator('[data-event=revoke]').click();assert.match(await page.locator('#observation-status').innerText(),/Permission revoked/);assert.equal(await page.locator('[data-event=observe]').count(),0);checks++;
 await page.getByRole('link',{name:'Review permission',exact:true}).click();await page.locator('#consent').check();await page.locator('[data-event=permission-dialog]').click();await page.locator('dialog [data-event=grant]').click();await page.locator('[data-event=observe]').click();await page.locator('[data-event=stop]').click();assert.match(await page.locator('#observation-status').innerText(),/Stopped/);await page.locator('.bottom-nav a').first().click();assert.match(await page.locator('.sticky-stop').innerText(),/STOPPED/);checks++;
 // Stale -> explanation -> recover cannot silently resume.
 await page.goto('http://127.0.0.1:4176/games/wow/observation?surface=android&lang=en');await page.locator('[data-event=stale]').click();assert.match(await page.locator('main').innerText(),/Source stale/);await page.locator('[data-event=recover]').click();assert.doesNotMatch(await page.locator('main').innerText(),/Demo observation/);checks++;
 // MFA rejects bad code, Escape closes and returns focus; no real session.
 await page.goto('http://127.0.0.1:4176/sign-in?surface=control&lang=en');await page.locator('[name=email]').fill('demo@example.test');await page.locator('[name=password]').fill('fictional');await page.locator('#auth-form button[type=submit]').click();await page.locator('dialog [name=code]').fill('000000');await page.locator('#mfa-form button.primary').click();assert.match(await page.locator('#mfa-error').innerText(),/Incorrect/);await page.locator('dialog [name=code]').fill('123456');await page.locator('#mfa-form button.primary').click();await page.waitForURL('**/overview?**');checks++;
 // Admin never offers operations.
 await page.goto('http://127.0.0.1:4176/admin?surface=control&lang=en');assert.match(await page.locator('main').innerText(),/Access denied/);checks++;
 // Download failure / rollback; simulated progress never claims installation.
 await page.goto('http://127.0.0.1:4176/updates?surface=windows&lang=en');await page.locator('[data-event=update-start]').click();await page.locator('[data-event=update-fail]').click();assert.equal(await page.locator('#update-status').innerText(),'ERROR');await page.locator('[data-event=update-rollback]').click();assert.equal(await page.locator('#update-status').innerText(),'ROLLBACK-UNAVAILABLE');checks++;
 // Overlay density and unconditional Stop.
 await page.goto('http://127.0.0.1:4176/overlay?surface=windows&lang=en');await page.locator('[data-density=minimal]').click();assert.equal(await page.locator('.overlay [data-event=stop]').isVisible(),true);await page.locator('.overlay [data-event=stop]').click();assert.match(await page.locator('.overlay').innerText(),/STOPPED/);checks++;
 // Menu, history, anchor navigation and locale.
 await page.goto('http://127.0.0.1:4176/?surface=site&lang=en');await page.locator('#menu').click();assert.equal(await page.locator('#menu').getAttribute('aria-expanded'),'true');await page.locator('.public-header nav a').first().click();await page.goBack();assert.equal(new URL(page.url()).pathname,'/');await page.locator('#locale').click();assert.equal(await page.locator('html').getAttribute('lang'),'ru');checks++;
 await page.goto('http://127.0.0.1:4176/legal?surface=site&lang=en');await page.locator('.legal-layout aside a').nth(1).click();assert.equal(new URL(page.url()).hash,'#legal-1');checks++;
 // Real keyboard focus and native modal Escape.
 await page.goto('http://127.0.0.1:4176/security?surface=control&lang=en');await page.locator('[data-event=mfa-dialog]').focus();await page.keyboard.press('Enter');assert.equal(await page.locator('dialog').isVisible(),true);assert.ok(await page.locator('dialog').getAttribute('aria-labelledby'));await page.keyboard.press('Escape');assert.equal(await page.locator('dialog').isVisible(),false);assert.equal(await page.locator('[data-event=mfa-dialog]').evaluate(e=>e===document.activeElement),true);checks++;
 await page.goto('http://127.0.0.1:4176/account?surface=windows&lang=en');await page.locator('[data-event=sign-out]').click();assert.equal(new URL(page.url()).pathname,'/launcher');assert.equal(await page.locator('.sticky-stop .badge').innerText(),'STOPPED');checks++;
 await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await page.evaluate(()=>matchMedia('(prefers-reduced-motion:reduce)').matches),true);assert.equal(await page.locator('button').first().evaluate(e=>getComputedStyle(e).transitionDuration),'0s');checks++;
 for(const [name,p,s,lang,width]of [['home','/','site','ru',1440],['android','/capture','android','ru',390],['windows','/overview','windows','en',1440],['control','/security','control','en',1440],['brands','/brand','library','ru',1440],['icons','/icons','library','en',1440],['light','/','site','en',390]]){
 await page.setViewportSize({width,height:1000});await page.goto(`http://127.0.0.1:4176${p}?surface=${s}&lang=${lang}`);await page.locator('h1').waitFor();await page.evaluate(()=>document.fonts.ready);if(name==='light')await page.locator('#theme').click();await page.screenshot({path:path.join(output,`${name}.png`),fullPage:true});
 }
 assert.deepEqual(errors,[]);
 const evidence={directRouteLocaleViewportChecks:routes,journeyChecks:checks,pageErrors:errors,viewports:[320,390,768,1024,1440],locales:['ru','en'],note:'Browser prototype evidence only; no native, physical, owner or release acceptance.'};fs.writeFileSync(path.join(output,'browser-evidence.json'),JSON.stringify(evidence,null,2));console.log(JSON.stringify(evidence));
 }finally{await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1});
