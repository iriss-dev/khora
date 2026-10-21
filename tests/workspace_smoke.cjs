const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const root=path.resolve(__dirname,'..');
const server=http.createServer((req,res)=>{
  let file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
  if(!file.startsWith(root+path.sep))return res.writeHead(403).end();
  if(fs.existsSync(file)&&fs.statSync(file).isDirectory())file=path.join(file,'index.html');
  const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.png':'image/png'};
  fs.readFile(file,(error,data)=>{if(error)return res.writeHead(404).end();res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');res.end(data);});
});
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try{
    browser=await chromium.launch({channel:process.env.KHORA_BROWSER_CHANNEL||'msedge',headless:true,args:['--enable-unsafe-swiftshader']});
    const page=await browser.newPage({viewport:{width:1536,height:1100}}),errors=[],external=[];
    page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
    await page.route('**/*',route=>{
      const url=new URL(route.request().url());
      if(url.hostname!=='127.0.0.1'&&!['data:','blob:'].includes(url.protocol)){external.push(url.href);return route.abort();}
      return route.continue();
    });
    const base=`http://127.0.0.1:${server.address().port}/platform/`;
    fs.mkdirSync(path.join(root,'build'),{recursive:true});
    await page.goto(base+'robot.html');
    await page.locator('#robot-plan').click();
    await page.waitForFunction(()=>!document.getElementById('robot-run').disabled);
    assert.match(await page.locator('#robot-error').textContent(),/0\.00/);
    const downloadReady=page.waitForEvent('download');await page.locator('#robot-export').click();
    const downloaded=await downloadReady,exported=JSON.parse(fs.readFileSync(await downloaded.path(),'utf8'));
    assert.equal(exported.samples.length,101);
    await page.locator('#robot-run').click();
    await page.waitForFunction(()=>document.getElementById('robot-progress').textContent==='100%',null,{timeout:10000});
    await page.locator('#robot-import').setInputFiles({name:'plan.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(exported))});
    await page.waitForFunction(()=>!document.getElementById('robot-run').disabled);
    await page.locator('#robot-run').click();await page.locator('#robot-stop').click();
    assert.equal(await page.locator('#robot-state').getAttribute('data-state'),'stopped');
    await page.locator('#robot-tool').fill('{"name":"khora_robot_plan_move","arguments":{"target_m":[99,0,0.5]}}');
    await page.locator('#robot-tool-apply').click();assert.ok((await page.locator('#robot-message').textContent()).length>0);
    await page.locator('#robot-tool').fill('{"name":"khora_robot_plan_move","arguments":{"target_m":[0.3,0.1,0.6]}}');
    await page.locator('#robot-tool-apply').click();assert.equal(await page.locator('#robot-message').textContent(),'');
    await page.screenshot({path:path.join(root,'build/robot-desktop.png'),fullPage:true});
    await page.goto(base+'hardware.html');
    await page.locator('#pico-simulate').click();await page.locator('#pico-stage').click();
    assert.match(await page.locator('#pico-info').textContent(),/true/);
    await page.locator('#pico-interlock').check();assert.equal(await page.locator('#pico-arm').isDisabled(),true);
    const before=await page.locator('.phase-cell strong').first().textContent();
    await page.locator('#pico-x').fill('20');assert.notEqual(await page.locator('.phase-cell strong').first().textContent(),before);
    await page.locator('#pico-stop').click();assert.match(await page.locator('#pico-state').textContent(),/DESCONECTADO/);
    await page.screenshot({path:path.join(root,'build/pico-desktop.png'),fullPage:true});
    await page.goto(base+'community.html');
    assert.equal(await page.locator('a[href="https://github.com/iriss-dev/khora/discussions"]').count(),2);
    await page.getByRole('link',{name:'Abrir los ejemplos del BBS original'}).click();
    await page.waitForFunction(()=>document.querySelector('.notebook-details')?.open===true);
    for(const file of ['robot.html','hardware.html','community.html']){
      await page.goto(base+file);await page.setViewportSize({width:390,height:844});
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),file);
      await page.screenshot({path:path.join(root,`build/${file.replace('.html','')}-mobile.png`),fullPage:true});
    }
    const camera=await browser.newPage();
    await camera.addInitScript(()=>{
      navigator.mediaDevices.getUserMedia=async()=>{
        const canvas=document.createElement('canvas');canvas.width=320;canvas.height=240;
        canvas.getContext('2d').fillRect(0,0,320,240);
        window.testCamera=canvas.captureStream(15);return window.testCamera;
      };
    });
    await camera.route('https://cdn.jsdelivr.net/**',route=>route.fulfill({contentType:'text/javascript',headers:{'Access-Control-Allow-Origin':'*'},body:'export const FilesetResolver={forVisionTasks:async()=>({})};export const HandLandmarker={createFromOptions:async()=>({detectForVideo:()=>({landmarks:[Array.from({length:9},()=>({x:0.3,y:0.6,z:0}))]}),close(){}})};'}));
    await camera.goto(base+'robot.html');await camera.locator('#camera-start').click();
    await camera.waitForFunction(()=>document.getElementById('robot-x').value==='325');
    await camera.locator('#camera-start').click();assert.ok(await camera.evaluate(()=>window.testCamera.getTracks().every(track=>track.readyState==='ended')));
    assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
    console.log(JSON.stringify({result:'passed',robotPlanReplay:true,picoSimulation:true,forumAndArchive:true,cameraWiring:'mocked detector and video',externalRequests:external.length,browserErrors:errors.length},null,2));
  }finally{await browser?.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
