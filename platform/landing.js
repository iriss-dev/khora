(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const translated = [...document.querySelectorAll('[data-en]')];
  const accessible = [...document.querySelectorAll('[data-en-aria]')];
  translated.forEach(element => { element.dataset.es = element.textContent; });
  accessible.forEach(element => { element.dataset.esAria = element.getAttribute('aria-label'); });
  function stored(key, fallback) {
    try { return localStorage.getItem(key) || fallback; } catch { return fallback; }
  }
  function remember(key, value) {
    try { localStorage.setItem(key, value); } catch {}
  }
  const requestedLanguage = new URLSearchParams(location.search).get('lang');
  let language = (requestedLanguage || stored('khora-language', 'es')) === 'en' ? 'en' : 'es';
  let theme = stored('khora-theme', 'dark') === 'light' ? 'light' : 'dark';
  let motion = !reducedMotion.matches;
  let guideTimer, sweepFrame, toastTimer;
  let step = 1, rigMode = 'all', sweep = false;

  const rigCopy = {
    all: {
      tag: ['Montaje completo', 'Complete assembly'],
      heading: ['Dónde coincidirían la imagen y el foco acústico', 'Where the image and the acoustic focus would meet'],
      body: ['La placa forma la imagen aérea sobre la matriz. Las líneas naranjas indican un foco acústico modelado en esa posición. Elige una vista para examinar cada parte.', 'The plate forms the aerial image above the array. The orange lines mark a modeled acoustic focus at that position. Select a view to inspect each part.']
    },
    optics: {
      tag: ['Recorrido de la luz', 'Light path'],
      heading: ['La luz sale de la pantalla y converge al otro lado de la placa', 'Light leaves the display and converges across the plate'],
      body: ['La matriz ultrasónica se oculta en esta vista. Sigue los puntos azules: pasan de la pantalla a la placa y terminan en el plano de la imagen aérea.', 'The ultrasonic array is hidden in this view. Follow the blue dots: they travel from the display to the plate and end at the aerial image plane.']
    },
    haptics: {
      tag: ['Enfoque del ultrasonido', 'Ultrasound focus'],
      heading: ['Los emisores apuntan a un objetivo sobre la matriz', 'The emitters focus on a target above the array'],
      body: ['La pantalla y la placa óptica se ocultan. Los frentes naranjas ilustran la propagación hacia el objetivo; el campo real se calcula en el mapa de abajo.', 'The display and optical plate are hidden. Orange wavefronts illustrate propagation toward the target; the actual field is calculated in the map below.']
    }
  };
  const stepCopy = [
    ['Paso 1: la luz sale de una pantalla convencional situada debajo de la placa.', 'Step 1: light comes from a conventional display below the plate.'],
    ['Paso 2: la placa hace converger los rayos en una imagen al otro lado. Allí no hay una pantalla física.', 'Step 2: the plate makes the rays converge into an image across it. There is no physical screen at that position.'],
    ['Paso 3: la matriz podría enfocar presión acústica en la posición de la imagen. La coincidencia física todavía requiere mediciones.', 'Step 3: the array could focus acoustic pressure at the image position. Physical alignment still requires measurements.']
  ];

  function copy(element, pair) {
    element.dataset.es = pair[0];
    element.dataset.en = pair[1];
    element.textContent = pair[language === 'en' ? 1 : 0];
  }
  function updateLabels() {
    const current = rigCopy[rigMode];
    copy($('rig-mode-tag'), current.tag);
    copy($('rig-heading'), current.heading);
    copy($('rig-description'), current.body);
    copy($('diagram-caption'), stepCopy[step - 1]);
    copy($('rig-motion'), motion ? ['Pausar animación', 'Pause animation'] : ['Reanudar animación', 'Resume animation']);
    copy($('guide-play'), guideTimer ? ['Pausar explicación', 'Pause explanation'] : ['Reproducir explicación', 'Play the explanation']);
    copy($('preview-sweep'), sweep ? ['Detener barrido', 'Stop sweep'] : ['Animar un barrido', 'Animate a sweep']);
    $('theme-label').textContent = theme === 'dark'
      ? (language === 'es' ? 'Tema claro' : 'Light theme')
      : (language === 'es' ? 'Tema oscuro' : 'Dark theme');
    $('theme-toggle').setAttribute('aria-label', $('theme-label').textContent);
    $('theme-toggle').title = $('theme-label').textContent;
  }
  function flash(element, className) {
    element.classList.remove(className);
    void element.offsetWidth;
    element.classList.add(className);
  }
  function toast(message) {
    clearTimeout(toastTimer);
    $('site-toast').textContent = message;
    $('site-toast').classList.add('visible');
    toastTimer = setTimeout(() => $('site-toast').classList.remove('visible'), 2800);
  }
  function setLanguage(next, announce = false) {
    language = next;
    document.documentElement.lang = next;
    translated.forEach(element => { element.textContent = element.dataset[next]; });
    accessible.forEach(element => { element.setAttribute('aria-label', next === 'en' ? element.dataset.enAria : element.dataset.esAria); });
    document.querySelectorAll('[data-language]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.language === next)));
    document.title = next === 'es' ? 'KHORA — Simulador de imágenes aéreas y ultrasonido' : 'KHORA — Aerial imaging and ultrasound simulator';
    const url = new URL(location.href);
    url.searchParams.set('lang', next);
    history.replaceState(null, '', url);
    remember('khora-language', next);
    updateLabels();
    document.querySelectorAll('a[href^="lab.html"]').forEach(link => {
      const target = new URL(link.href);
      target.searchParams.set('lang', next);
      link.href = target.href;
    });
    if (announce) {
      flash($('hero-title'), 'language-updated');
      toast(next === 'es' ? 'Idioma cambiado a español' : 'Language changed to English');
    }
  }
  document.querySelectorAll('[data-language]').forEach(button => button.addEventListener('click', () => setLanguage(button.dataset.language, true)));
  function setTheme(next) {
    theme = next;
    document.documentElement.dataset.theme = next;
    $('theme-toggle').setAttribute('aria-pressed', String(next === 'light'));
    document.querySelector('meta[name="theme-color"]').content = next === 'light' ? '#f5f3ee' : '#080a0e';
    remember('khora-theme', next);
    updateLabels();
    document.dispatchEvent(new CustomEvent('khora:theme', {detail: next}));
  }
  $('theme-toggle').addEventListener('click', () => setTheme(theme === 'dark' ? 'light' : 'dark'));
  function setMotion(playing) {
    motion = playing;
    $('rig-motion').setAttribute('aria-pressed', String(playing));
    document.dispatchEvent(new CustomEvent('khora:motion', {detail: playing}));
    updateLabels();
  }
  $('rig-motion').addEventListener('click', () => setMotion(!motion));
  reducedMotion.addEventListener('change', () => { if (reducedMotion.matches) { setMotion(false); setGuide(false); stopSweep(); } });
  document.querySelectorAll('[data-rig]').forEach(button => button.addEventListener('click', () => {
    rigMode = button.dataset.rig;
    $('assembly').dataset.mode = rigMode;
    $('rig-step').textContent = `${String(['all', 'optics', 'haptics'].indexOf(rigMode) + 1).padStart(2, '0')} / 03`;
    updateLabels();
    flash($('assembly'), 'scene-updated');
  }));

  function showStep(next) {
    step = next;
    $('process-diagram').dataset.step = String(next);
    document.querySelectorAll('.process-step').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.step) === next)));
    updateLabels();
  }
  function setGuide(playing) {
    clearInterval(guideTimer);
    guideTimer = null;
    if (playing) guideTimer = setInterval(() => showStep(step % 3 + 1), 4800);
    $('guide-play').setAttribute('aria-pressed', String(playing));
    updateLabels();
  }
  document.querySelectorAll('.process-step').forEach(button => button.addEventListener('click', () => { setGuide(false); showStep(Number(button.dataset.step)); }));
  $('guide-play').addEventListener('click', () => setGuide(!guideTimer));
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
    $('preview-marker').hidden = true;
  }
  function preview() {
    const x = Number($('preview-focus').value), z = Number($('preview-height').value);
    const focus = [x / 1000, 0, z / 1000];
    const drive = A.synthesize(focus);
    const pressure = A.pressure(focus, drive).rms;
    $('preview-value').textContent = `${x} mm`;
    $('preview-height-value').textContent = `${z} mm`;
    $('preview-pressure').textContent = `${pressure.toFixed(1)} Pa`;
    $('preview-open').href = `lab.html?lang=${language}#x=${x}&y=0&z=${z}&plane=0&taper=0&quantity=0`;
    $('preview-marker').style.left = `${(x / 320 + .5) * 100}%`;
    $('preview-marker').style.top = `${(1 - (z - 20) / 240) * 100}%`;
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
  function schedulePreview() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; preview(); });
  }
  function stopSweep() {
    sweep = false;
    cancelAnimationFrame(sweepFrame);
    $('preview-sweep').setAttribute('aria-pressed', 'false');
    updateLabels();
  }
  $('preview-sweep').addEventListener('click', () => {
    if (sweep) return stopSweep();
    sweep = true;
    $('preview-sweep').setAttribute('aria-pressed', 'true');
    updateLabels();
    const start = performance.now();
    let last = 0;
    function sweepTick(now) {
      if (!sweep) return;
      if (now - last >= 120) {
        last = now;
        $('preview-focus').value = Math.round(50 * Math.sin((now - start) / 2400));
        preview();
      }
      sweepFrame = requestAnimationFrame(sweepTick);
    }
    sweepFrame = requestAnimationFrame(sweepTick);
  });
  ['preview-focus', 'preview-height'].forEach(id => $(id).addEventListener('input', () => { stopSweep(); schedulePreview(); }));
  $('preview-reset').addEventListener('click', () => {
    stopSweep();
    $('preview-focus').value = 0;
    $('preview-height').value = 140;
    schedulePreview();
  });
  function pointToFocus(event) {
    const bounds = $('preview-canvas').getBoundingClientRect();
    $('preview-focus').value = Math.round(((event.clientX - bounds.left) / bounds.width - .5) * 320);
    $('preview-height').value = Math.round(20 + (1 - (event.clientY - bounds.top) / bounds.height) * 240);
    schedulePreview();
  }
  $('preview-canvas').addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    stopSweep();
    $('preview-canvas').setPointerCapture(event.pointerId);
    pointToFocus(event);
  });
  $('preview-canvas').addEventListener('pointermove', event => {
    if ($('preview-canvas').hasPointerCapture(event.pointerId)) pointToFocus(event);
  });
  ['pointerup', 'pointercancel'].forEach(name => $('preview-canvas').addEventListener(name, event => {
    if ($('preview-canvas').hasPointerCapture(event.pointerId)) $('preview-canvas').releasePointerCapture(event.pointerId);
  }));
  $('preview-canvas').addEventListener('webglcontextlost', () => { renderer = null; stopSweep(); $('preview-error').hidden = false; $('preview-marker').hidden = true; });
  document.addEventListener('visibilitychange', () => { if (document.hidden) { stopSweep(); setGuide(false); } });
  new IntersectionObserver(([entry]) => { if (!entry.isIntersecting) stopSweep(); }).observe($('explore'));

  if (!reducedMotion.matches) {
    const reveal = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('is-visible'); reveal.unobserve(entry.target); }
    }), {threshold: .08});
    document.querySelectorAll('.section-heading, .explanation-layout, .field-preview, .build-table, .invitation').forEach(element => {
      element.classList.add('reveal-ready');
      reveal.observe(element);
    });
  }
  setLanguage(language);
  setTheme(theme);
  setMotion(motion);
  preview();
})();
