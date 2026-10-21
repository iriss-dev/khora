/* Run with Playwright resolvable through NODE_PATH or local node_modules. */
const {chromium}=require('playwright');
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const server=http.createServer((req,res)=>{
  const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=path.resolve(root,'.'+pathname);
  if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'};
  fs.readFile(file,(err,data)=>{if(err){res.writeHead(404).end();return;}
    res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');res.end(data);});
});
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try{
    browser=await chromium.launch({channel:process.env.KHORA_BROWSER_CHANNEL||'msedge',headless:true,args:['--enable-unsafe-swiftshader']});
    const page=await browser.newPage({viewport:{width:1536,height:1100}});
    const errors=[],external=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    await page.route('**/*',route=>{
      const url=new URL(route.request().url());
      if(url.hostname!=='127.0.0.1'&&!['data:','blob:'].includes(url.protocol)){external.push(url.href);return route.abort();}
      return route.continue();
    });
    await page.goto(`http://127.0.0.1:${server.address().port}/platform/lab.html`);
    await page.locator('#field-pressure').filter({hasText:/Pa/}).waitFor();
    const before=await page.locator('#field-force').textContent();
    await page.locator('#field-x').fill('35');
    await page.waitForFunction(()=>document.getElementById('field-x-value').textContent==='35 mm');
    assert.notEqual(await page.locator('#field-force').textContent(),before);
    await page.selectOption('#field-plane','2');
    await page.locator('#field-taper').check();
    await page.selectOption('#field-quantity','1');
    await page.waitForFunction(()=>document.getElementById('field-scale-low').textContent.includes('mN'));
    await page.locator('#field-reset').click();
    await page.waitForFunction(()=>document.getElementById('field-x-value').textContent==='0 mm');
    await page.locator('[data-focus="45,0,140"]').click();
    await page.waitForFunction(()=>location.hash.includes('x=45'));
    await page.reload();
    await page.waitForFunction(()=>document.getElementById('field-x-value').textContent==='45 mm');
    const downloadReady=page.waitForEvent('download');
    await page.locator('#field-export').click();
    const download=await downloadReady;
    const exported=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
    assert.deepEqual(exported.focus_m,[.045,0,.14]);
    assert.equal(exported.phase_u8.length,256);
    const plot=await page.locator('#field-canvas').boundingBox();
    await page.mouse.click(plot.x+plot.width*.6,plot.y+plot.height*.5);
    await page.waitForFunction(()=>document.getElementById('field-x').value==='32');
    await page.locator('#field-reset').click();
    await page.waitForFunction(()=>document.getElementById('field-x-value').textContent==='0 mm');
    // GPU phasor calculation compared with the CPU at center pixel of each slice.
    const parity=await page.evaluate(()=>{
      const A=KhoraAcoustics,drive=A.synthesize([.013,-.009,.14]);
      const data=new Uint8Array(1024);for(let i=0;i<256;i++){data[4*i]=drive.phases[i];data[4*i+1]=drive.weights[i];}
      const texture=new THREE.DataTexture(data,16,16,THREE.RGBAFormat);texture.needsUpdate=true;
      const renderer=new THREE.WebGLRenderer({antialias:false});renderer.setSize(1,1);
      const output=new THREE.WebGLRenderTarget(1,1),scene=new THREE.Scene(),camera=new THREE.Camera();
      // Encode RMS into RGB with 1e-3 Pa resolution for readback (up to 16.7 kPa).
      const shader=A.fragmentShader.replace('gl_FragColor=vec4(color,1.0);',
        'float v=floor(rms*1000.0); gl_FragColor=vec4(mod(v,256.0),mod(floor(v/256.0),256.0),floor(v/65536.0),255.0)/255.0;');
      const material=new THREE.ShaderMaterial({vertexShader:A.vertexShader,fragmentShader:shader,
        uniforms:{driveMap:{value:texture},k:{value:A.K},source:{value:1},referencePressure:{value:1000},
          sliceOffset:{value:0},sliceMode:{value:0},quantity:{value:0},forceScale:{value:1}},depthTest:false});
      scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2,2),material));
      const results=[];
      for(let mode=0;mode<3;mode++){
        const offset=mode===2?.14:.01;
        material.uniforms.sliceMode.value=mode;material.uniforms.sliceOffset.value=offset;
        renderer.setRenderTarget(output);renderer.render(scene,camera);
        const bytes=new Uint8Array(4);renderer.readRenderTargetPixels(output,0,0,1,1,bytes);
        const gpu=(bytes[0]+bytes[1]*256+bytes[2]*65536)/1000;
        const point=mode===0?[0,offset,.14]:mode===1?[offset,0,.14]:[0,0,offset];
        const cpu=A.pressure(point,drive).rms;results.push({mode,cpu,gpu,relativeError:Math.abs(gpu-cpu)/cpu});
      }
      renderer.dispose();texture.dispose();material.dispose();output.dispose();return results;
    });
    assert.ok(parity.every(x=>x.relativeError<.002),JSON.stringify(parity));
    fs.mkdirSync(path.join(root,'build'),{recursive:true});
    await page.screenshot({path:path.join(root,'build/workbench-desktop.png'),fullPage:false});
    await page.locator('.assembly-details>summary').first().click();
    await page.locator('#smode-stage3d').click();
    await page.locator('#smode-combined').click();
    // User-authored HTML must display literally, including replies and citation controls.
    await page.evaluate(()=>{
      document.getElementById('nt-title').value="<img src=x onerror=alert(1)> ' quote";
      document.getElementById('nt-body').value='<svg onload=alert(1)>body</svg>';
      publishThread();
    });
    assert.equal(await page.locator('.bbs-post-title img').count(),0);
    assert.equal(await page.locator('.post-lead svg').count(),0);
    await page.setViewportSize({width:390,height:844});
    await page.locator('.assembly-details>summary').first().click();
    await page.screenshot({path:path.join(root,'build/workbench-mobile.png'),fullPage:true});
    const overflow=await page.evaluate(()=>({width:innerWidth,body:document.documentElement.scrollWidth}));
    assert.ok(overflow.body<=overflow.width,JSON.stringify(overflow));
    assert.deepEqual(external,[]);assert.deepEqual(errors,[]);
    console.log(JSON.stringify({result:'passed',parity,externalRequests:external.length,browserErrors:errors.length,overflow},null,2));
  }finally{await browser?.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
