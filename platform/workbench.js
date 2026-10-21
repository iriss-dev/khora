(() => {
  'use strict';
  const A=KhoraAcoustics, $=id=>document.getElementById(id);
  let renderer,material,texture,scene,camera,drive,focus,queued=false,trackExpiry;
  const cpuStart=()=>performance.now();
  const status=$('field-render-status');
  const bridge=new KhoraSerial.SerialBridge(updateLink,track=>{
    clearTimeout(trackExpiry);
    $('serial-tracking').textContent=`RX #${track.sequence} / confidence ${(track.confidence*100).toFixed(0)}% / device ${track.deviceTimeUs} us`;
    trackExpiry=setTimeout(()=>{$('serial-tracking').textContent='Tracking stale / no packet received for 100 ms';},100);
  });
  function updateLink(info){
    $('serial-status').textContent=info.message;
    $('serial-connect').disabled=!['disconnected','ready'].includes(info.state);
    $('serial-connect').textContent=info.state==='ready'?'Disconnect':'Connect device';
    $('serial-stage').disabled=info.state!=='ready'||$('field-taper').checked;
    const sorted=info.rtt.slice().sort((a,b)=>a-b);
    $('serial-rtt').textContent=sorted.length
      ? `ACK RTT p95 ${sorted[Math.ceil(sorted.length*.95)-1].toFixed(2)} ms / n=${sorted.length}`
      : 'ACK RTT — / no measurements';
  }
  $('serial-connect').addEventListener('click',async()=>{
    try{if(bridge.state==='ready')await bridge.disconnect();else await bridge.connect();}
    catch(error){showToast(error.message);}
  });
  $('serial-stage').addEventListener('click',async()=>{
    $('serial-stage').disabled=true;
    try{await bridge.stage(drive.phases);}catch(error){showToast(error.message);}
  });
  document.addEventListener('visibilitychange',()=>{
    if(document.hidden&&bridge.state!=='disconnected')void bridge.disconnect();
  });
  window.addEventListener('pagehide',()=>void bridge.disconnect());
  function currentConfig() {
    return {
      x: Number($('field-x').value), y: Number($('field-y').value), z: Number($('field-z').value),
      plane: Number($('field-plane').value), quantity: Number($('field-quantity').value),
      taper: Number($('field-taper').checked)
    };
  }
  function restoreConfig() {
    const config = KhoraFieldConfig.parse(location.hash);
    for (const key of ['x', 'y', 'z', 'plane', 'quantity']) $(`field-${key}`).value = config[key];
    $('field-taper').checked = Boolean(config.taper);
  }
  restoreConfig();
  window.addEventListener('hashchange', () => { restoreConfig(); schedule(); });
  $('field-share').addEventListener('click', async () => {
    const url = new URL(location.href);
    url.hash = KhoraFieldConfig.encode(currentConfig());
    try {
      await navigator.clipboard.writeText(url.href);
      showToast('Configuration link copied');
    } catch {
      history.replaceState(null, '', url);
      showToast('Copy the address in your browser to share this configuration');
    }
  });
  $('field-export').addEventListener('click', () => {
    const config = currentConfig();
    const snapshot = A.synthesize([config.x, config.y, config.z].map(value => value / 1000), Boolean(config.taper));
    const data = KhoraFieldConfig.phaseExport(config, snapshot);
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `khora-phase-map-${config.x}-${config.y}-${config.z}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  document.querySelectorAll('[data-focus]').forEach(button => button.addEventListener('click', () => {
    button.dataset.focus.split(',').forEach((value, index) => { $(`field-${['x', 'y', 'z'][index]}`).value = value; });
    schedule();
  }));
  function dragFocus(event) {
    const bounds = $('field-canvas').getBoundingClientRect();
    const u = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
    const v = Math.max(0, Math.min(1, 1 - (event.clientY - bounds.top) / bounds.height));
    const plane = Number($('field-plane').value);
    const lateralAxis = plane === 1 ? 'y' : 'x';
    $(`field-${lateralAxis}`).value = Math.round((u - .5) * 320);
    $(plane === 2 ? 'field-y' : 'field-z').value = Math.round(plane === 2 ? (v - .5) * 320 : 20 + v * 240);
    schedule();
  }
  $('field-canvas').addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    $('field-canvas').setPointerCapture(event.pointerId);
    dragFocus(event);
  });
  $('field-canvas').addEventListener('pointermove', event => {
    if ($('field-canvas').hasPointerCapture(event.pointerId)) dragFocus(event);
  });
  $('field-canvas').addEventListener('pointerup', event => {
    if ($('field-canvas').hasPointerCapture(event.pointerId)) $('field-canvas').releasePointerCapture(event.pointerId);
  });
  function values(){
    focus=['x','y','z'].map(axis=>Number($(`field-${axis}`).value)/1000);
    ['x','y','z'].forEach((axis,i)=>$(`field-${axis}-value`).textContent=`${(focus[i]*1000).toFixed(0)} mm`);
    drive=A.synthesize(focus,$('field-taper').checked);
    $('serial-stage').disabled=bridge.state!=='ready'||$('field-taper').checked;
    return Number($('field-plane').value);
  }
  function render(){
    queued=false;
    const started=cpuStart(), mode=values(), source=1;
    const url = new URL(location.href);
    url.hash = KhoraFieldConfig.encode(currentConfig());
    history.replaceState(null, '', url);
    const p=A.pressure(focus,drive,source);
    const force=A.patchForce(focus,drive,source);
    const left=[focus[0]-.0005,focus[1],focus[2]],right=[focus[0]+.0005,focus[1],focus[2]];
    const gradient=(A.patchForce(right,drive,source)-A.patchForce(left,drive,source)); // denominator = 1 mm
    $('field-pressure').textContent=`${p.rms.toFixed(1)} Pa`;
    $('field-force').textContent=`${force.toFixed(3)} mN`;
    $('field-gradient').textContent=`${(Math.abs(gradient)<.00005?0:gradient).toFixed(4)}`;
    $('field-wavelength').textContent=`${(A.C/40).toFixed(2)} mm`;
    $('field-probe').textContent=`Focus [${focus.map(v=>(v*1000).toFixed(0)).join(', ')}] mm`;
    const offset=mode===0?focus[1]:mode===1?focus[0]:focus[2];
    $('field-axis').textContent=mode===2?'Y: -160 to +160 mm':'Z: 20 to 260 mm';
    $('field-axis-x').textContent=mode===1?'Y: -160 to +160 mm':'X: -160 to +160 mm';
    const horizontal=mode===1?focus[1]:focus[0];
    const vertical=mode===2?(focus[1]+.16)/.32:(focus[2]-.02)/.24;
    $('field-crosshair').style.left=`${(horizontal/.32+.5)*100}%`;
    $('field-crosshair').style.top=`${(1-vertical)*100}%`;
    const quantity=Number($('field-quantity').value);
    const forceScale=Math.max(p.radiation*.001,1e-8);
    $('field-scale-low').textContent=quantity?'0 mN/mm²':'−40 dB';
    $('field-scale-high').textContent=quantity?`${forceScale.toFixed(4)} mN/mm²`:'0 dB / focal pressure';
    if(renderer){
      for(let i=0;i<256;i++){texture.image.data[i*4]=drive.phases[i];texture.image.data[i*4+1]=drive.weights[i];}
      texture.needsUpdate=true;
      Object.assign(material.uniforms.referencePressure,{value:p.rms});
      material.uniforms.sliceMode.value=mode;material.uniforms.sliceOffset.value=offset;
      material.uniforms.quantity.value=quantity;material.uniforms.forceScale.value=forceScale;
      renderer.render(scene,camera);
      status.textContent=`320 × 240 samples / CPU + submit ${(performance.now()-started).toFixed(1)} ms`;
    }else status.textContent='CPU estimates available / WebGL unavailable';
  }
  function schedule(){if(!queued){queued=true;requestAnimationFrame(render);}}
  for(const id of ['field-x','field-y','field-z','field-plane','field-taper','field-quantity'])
    $(id).addEventListener('input',schedule);
  $('field-reset').addEventListener('click',()=>{
    $('field-x').value=0;$('field-y').value=0;$('field-z').value=140;
    $('field-plane').value=0;$('field-taper').checked=false;$('field-quantity').value=0;schedule();
  });
  try{
    renderer=new THREE.WebGLRenderer({canvas:$('field-canvas'),antialias:false,alpha:false});
    renderer.setPixelRatio(1);renderer.setSize(320,240,false);
    texture=new THREE.DataTexture(new Uint8Array(256*4),16,16,THREE.RGBAFormat);
    texture.minFilter=texture.magFilter=THREE.NearestFilter;texture.generateMipmaps=false;
    material=new THREE.ShaderMaterial({vertexShader:A.vertexShader,fragmentShader:A.fragmentShader,
      uniforms:{driveMap:{value:texture},k:{value:A.K},source:{value:1},referencePressure:{value:1},
        sliceOffset:{value:0},sliceMode:{value:0},quantity:{value:0},forceScale:{value:1}},depthTest:false,depthWrite:false});
    scene=new THREE.Scene();camera=new THREE.Camera();scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2,2),material));
    $('field-canvas').addEventListener('webglcontextlost',event=>{
      event.preventDefault();$('field-error').hidden=false;$('field-error').textContent='Graphics context lost. Reload to restore the field.';
    });
  }catch(error){renderer=null;$('field-error').hidden=false;$('field-error').textContent='WebGL unavailable. Numerical field estimates remain available below.';}
  render();
  if(!navigator.serial||!globalThis.isSecureContext){
    $('serial-connect').disabled=true;
    $('serial-status').textContent='WebSerial unavailable / use Chrome or Edge on localhost or HTTPS';
  }
})();
