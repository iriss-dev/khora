(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const translated = [...document.querySelectorAll('[data-en]')];
  translated.forEach(element => { element.dataset.es = element.textContent; });
  let language = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'es';
  let toastTimer;

  function setLanguage(next) {
    language = next;
    document.documentElement.lang = next;
    translated.forEach(element => { element.textContent = element.dataset[next]; });
    $('language').textContent = next === 'es' ? 'EN' : 'ES';
    $('language').setAttribute('aria-label', next === 'es' ? 'Switch to English' : 'Cambiar a español');
    document.title = next === 'es' ? 'KHORA — Luz, tacto y espacio' : 'KHORA — Beyond the screen';
    const url = new URL(location.href);
    url.searchParams.set('lang', next);
    history.replaceState(null, '', url);
  }
  $('language').addEventListener('click', () => setLanguage(language === 'es' ? 'en' : 'es'));
  setLanguage(language);

  function toast(message) {
    clearTimeout(toastTimer);
    $('site-toast').textContent = message;
    $('site-toast').classList.add('visible');
    toastTimer = setTimeout(() => $('site-toast').classList.remove('visible'), 3000);
  }
  $('copy-clone').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText('git clone https://github.com/iriss-dev/khora.git');
      toast(language === 'es' ? 'Comando copiado' : 'Command copied');
    } catch {
      toast(language === 'es' ? 'Selecciona y copia el comando que aparece junto al botón.' : 'Select and copy the command beside the button.');
    }
  });

  const A = KhoraAcoustics;
  let renderer, material, texture, scene, camera;
  try {
    renderer = new THREE.WebGLRenderer({canvas: $('preview-canvas'), antialias: false});
    renderer.setPixelRatio(1);
    renderer.setSize(256, 192, false);
    texture = new THREE.DataTexture(new Uint8Array(1024), 16, 16, THREE.RGBAFormat);
    texture.minFilter = texture.magFilter = THREE.NearestFilter;
    material = new THREE.ShaderMaterial({
      vertexShader: A.vertexShader, fragmentShader: A.fragmentShader,
      uniforms: {driveMap: {value: texture}, k: {value: A.K}, source: {value: 1},
        referencePressure: {value: 1}, sliceOffset: {value: 0}, sliceMode: {value: 0},
        quantity: {value: 0}, forceScale: {value: 1}}, depthTest: false, depthWrite: false
    });
    scene = new THREE.Scene();
    camera = new THREE.Camera();
    scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material));
  } catch {
    renderer = null;
    $('preview-error').hidden = false;
  }
  function preview() {
    const x = Number($('preview-focus').value);
    const focus = [x / 1000, 0, .14];
    const drive = A.synthesize(focus);
    const pressure = A.pressure(focus, drive).rms;
    $('preview-value').textContent = `${x} mm`;
    $('preview-pressure').textContent = `${pressure.toFixed(1)} Pa`;
    $('preview-open').href = `lab.html#x=${x}&y=0&z=140&plane=0&taper=0&quantity=0`;
    if (!renderer) return;
    for (let index = 0; index < 256; index++) {
      texture.image.data[index * 4] = drive.phases[index];
      texture.image.data[index * 4 + 1] = 255;
    }
    texture.needsUpdate = true;
    material.uniforms.referencePressure.value = pressure;
    renderer.render(scene, camera);
  }
  let queued = false;
  $('preview-focus').addEventListener('input', () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; preview(); });
  });
  $('preview-canvas').addEventListener('webglcontextlost', () => { $('preview-error').hidden = false; });
  preview();
})();
