const {chromium}=require(process.env.CREATOR_FLOW_PLAYWRIGHT||'playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os');
const assert=require('node:assert/strict'),readline=require('node:readline');
(async()=>{
 const repo=path.resolve(__dirname,'..'),temp=await fs.mkdtemp(path.join(os.tmpdir(),'creator-studio-test-'));
 const python=process.env.CREATOR_FLOW_PYTHON||path.join(repo,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
 const child=spawn(python,['-X','utf8',path.join(__dirname,'studio_browser_fixture.py'),temp],{cwd:repo,windowsHide:true,stdio:['ignore','pipe','pipe']});
 let browser;try{
  const config=await new Promise((resolve,reject)=>{const t=setTimeout(()=>reject(Error('Fixture timeout')),15000);readline.createInterface({input:child.stdout}).once('line',line=>{clearTimeout(t);resolve(JSON.parse(line))});child.once('error',reject);child.stderr.on('data',x=>process.stderr.write(x));});
  const request=async body=>{const r=await fetch(config.url+'/v1/studio',{method:'POST',headers:{Authorization:'Bearer '+config.token,'Content-Type':'application/json'},body:JSON.stringify(body)});return {status:r.status,body:await r.json()}};
  const unauth=await fetch(config.url+'/v1/studio');assert.equal(unauth.status,401);
  const cross=await fetch(config.url+'/v1/studio',{headers:{Authorization:'Bearer '+config.token,Origin:'https://evil.example'}});assert.equal(cross.status,403);
  const embed=await fetch(config.url+'/studio/',{headers:{'Sec-Fetch-Site':'cross-site','Sec-Fetch-Mode':'cors'}});assert.equal(embed.status,403);
  browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:1550,height:1150}}),errors=[];page.on('pageerror',x=>errors.push(x.message));page.on('dialog',d=>d.accept());
  await page.goto(config.url+'/studio/');await page.getByRole('button',{name:'+ ახალი პროექტი',exact:true}).waitFor();
  await page.locator('#language').click();await page.getByRole('button',{name:'+ New project',exact:true}).click();
  await page.locator('#project-name').fill('Synthetic creator workspace');await page.locator('#project-folder').fill(temp);await page.locator('#create-project').click();
  await page.getByRole('heading',{name:'New task',exact:true}).waitFor();
  await page.locator('[data-tab="memory"]').click();await page.getByLabel('Memory',{exact:true}).fill('Audience: Georgian creators. Correct name: გიორგი.');await page.getByRole('button',{name:'Save memory',exact:true}).click();await page.locator('#notice').filter({hasText:'Memory updated'}).waitFor();
  await page.locator('[data-tab="connectors"]').click();const boxes=page.locator('#content .grid > .card');await boxes.nth(0).getByLabel('Enabled',{exact:true}).check();await boxes.nth(0).getByLabel('Connection method',{exact:true}).selectOption('handoff');await page.getByRole('button',{name:'Save connectors and roles',exact:true}).click();await page.locator('#notice').filter({hasText:'Saved.'}).waitFor();
  await page.locator('[data-tab="overview"]').click();await page.getByLabel('What should be done?',{exact:true}).fill('Give one accurate title.');await page.getByRole('button',{name:'Start task',exact:true}).click();await page.locator('.job .badge').filter({hasText:'handoff'}).waitFor();
  await page.getByLabel('Returned text',{exact:true}).fill('<img src=x onerror=alert(1)> Safe fictional result');await page.getByRole('button',{name:'Import result into project',exact:true}).click();await page.getByRole('button',{name:'Accept result into shared memory',exact:true}).click();await page.locator('#notice').filter({hasText:'Accepted.'}).waitFor();assert.equal(await page.locator('img[src=x]').count(),0);
  await page.locator('[data-tab="memory"]').click();await page.locator('details summary').click();assert.ok((await page.locator('details pre').innerText()).includes('Safe fictional result'));
  await page.reload();await page.locator('[data-tab="memory"]').click();assert.ok((await page.getByLabel('Memory',{exact:true}).inputValue()).includes('გიორგი'));
  const snapshot=await (await fetch(config.url+'/v1/studio',{headers:{Authorization:'Bearer '+config.token}})).json();const p=Object.values(snapshot.projects)[0];
  const stale=await request({action:'memory',project:p.id,revision:0,memory:'overwrite'});assert.equal(stale.status,400);
  const forbidden=await request({action:'local_job',project:p.id,revision:p.revision,operation:'shell',requestId:crypto.randomUUID()});assert.equal(forbidden.status,400);
  await page.locator('[data-tab="video"]').click();await page.getByLabel('review.json',{exact:true}).fill(config.review);await page.getByRole('button',{name:'Attach review',exact:true}).click();await page.getByRole('button',{name:'Edit transcript and clips',exact:true}).click();
  const editor=page.locator('#review-editor');await editor.locator('table textarea').first().fill('Corrected synthetic transcript');await editor.getByRole('button',{name:'Save corrections',exact:true}).click();await page.locator('#notice').filter({hasText:'Saved. The current version needs approval.'}).waitFor();
  await editor.getByLabel('I reviewed the full transcript and approve these cuts, hooks and caption choices',{exact:true}).check();await editor.getByLabel('Playback check: start / middle / end',{exact:true}).fill('Synthetic test: matching generated 6-second source.');await editor.getByRole('button',{name:'Approve saved version',exact:true}).click();await page.locator('#notice').filter({hasText:'Saved version approved.'}).waitFor();
  await editor.getByRole('button',{name:'Render approved Reels',exact:true}).click();await page.locator('.job').filter({hasText:'clips_render'}).locator('.badge').filter({hasText:'completed'}).waitFor({timeout:45000});
  const reviewData=JSON.parse(await fs.readFile(config.review,'utf8'));assert.equal(reviewData.cues[0].text,'Corrected synthetic transcript');assert.ok(reviewData.approval);
  await page.locator('#language').click();await page.locator('[data-tab="connectors"]').click();await page.getByRole('button',{name:'Continue with ChatGPT',exact:true}).waitFor();
  if(process.env.CREATOR_FLOW_STUDIO_SCREENSHOT)await page.screenshot({path:process.env.CREATOR_FLOW_STUDIO_SCREENSHOT,fullPage:true});
  assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,checks:['local auth and origin checks','cross-site bootstrap blocked','project creation','memory persistence','single-provider routing','chat handoff','explicit result acceptance','escaped text','stale-memory rejection','operation allowlist','full transcript editing','review approval','real local synthetic clip render','KA/EN UI'],liveProviderCalls:0}));
 }finally{if(browser)await browser.close();child.kill();}
})().catch(e=>{console.error(e);process.exitCode=1});
