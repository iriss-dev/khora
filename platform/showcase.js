(() => {
  'use strict';

  const canvas = document.getElementById('rig-canvas');
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({canvas, antialias: true, alpha: true});
  } catch {
    document.getElementById('rig-fallback').hidden = false;
    document.querySelectorAll('[data-rig], #rig-reset').forEach(button => button.disabled = true);
    return;
  }

  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.55;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(36, 1, 1, 1800);
  const home = new THREE.Vector3(300, 245, 340);
  camera.position.copy(home);
  const controls = new THREE.OrbitControls(camera, canvas);
  controls.target.set(0, 68, -5);
  controls.enableDamping = true;
  controls.dampingFactor = .08;
  controls.enableZoom = false;
  controls.enablePan = false;
  controls.minPolarAngle = .35;
  controls.maxPolarAngle = Math.PI / 2.1;
  controls.update();

  scene.add(new THREE.HemisphereLight(0xe9f1ff, 0x40352b, 1.1));
  function light(color, intensity, position) {
    const lamp = new THREE.DirectionalLight(color, intensity);
    lamp.position.set(...position);
    scene.add(lamp);
  }
  light(0xffffff, 3, [150, 260, 180]);
  light(0x6ec8ed, 1.5, [-160, 120, -100]);
  light(0xff7749, 1.8, [20, 80, 230]);

  const chassis = new THREE.MeshStandardMaterial({color: 0x202329, metalness: .72, roughness: .32});
  const edge = new THREE.MeshStandardMaterial({color: 0x626971, metalness: .85, roughness: .25});
  const dark = new THREE.MeshStandardMaterial({color: 0x101114, metalness: .5, roughness: .5});
  const orange = new THREE.MeshStandardMaterial({color: 0xff642d, emissive: 0xff4918, emissiveIntensity: .6, metalness: .35, roughness: .3});
  const optics = new THREE.Group();
  const acoustics = new THREE.Group();
  scene.add(optics, acoustics);

  function box(width, height, depth, material, x, y, z, parent = scene) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), material);
    mesh.position.set(x, y, z);
    parent.add(mesh);
    return mesh;
  }
  function line(points, color, opacity = .5, parent = scene) {
    const geometry = new THREE.BufferGeometry().setFromPoints(points.map(point => new THREE.Vector3(...point)));
    const mesh = new THREE.Line(geometry, new THREE.LineBasicMaterial({color, transparent: true, opacity}));
    parent.add(mesh);
    return mesh;
  }
  function label(text, position, color = '#c3c8cf', parent = scene) {
    const sheet = document.createElement('canvas');
    sheet.width = 512;
    sheet.height = 64;
    const context = sheet.getContext('2d');
    context.fillStyle = color;
    context.font = '24px Consolas, monospace';
    context.fillText(text, 4, 40);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({map: new THREE.CanvasTexture(sheet), transparent: true, depthTest: false}));
    sprite.position.set(...position);
    sprite.scale.set(100, 12.5, 1);
    parent.add(sprite);
  }

  box(204, 16, 220, chassis, 0, -3, -10);
  box(200, 2, 216, edge, 0, 6, -10);
  box(196, 2, 212, dark, 0, 8, -10);
  for (const x of [-87, 87]) for (const z of [-105, 85]) {
    box(13, 7, 13, dark, x, -14, z);
    const screw = new THREE.Mesh(new THREE.CylinderGeometry(2, 2, 1, 16), edge);
    screw.position.set(x, 9.5, z);
    scene.add(screw);
    box(2.5, .2, .4, dark, x, 10.1, z);
  }
  for (let z = -90; z <= 65; z += 9) box(.5, 4, 5, dark, 102.3, -3, z);
  box(27, 4, 1, orange, -59, -2, 100.5);
  label('KHORA / 01', [-46, 12, 100], '#c3c8cf');

  const cylinder = new THREE.CylinderGeometry(4.1, 4.1, 6, 20);
  const transducers = new THREE.InstancedMesh(cylinder, edge, 256);
  const caps = new THREE.InstancedMesh(new THREE.CylinderGeometry(3.45, 3.45, .3, 20), dark, 256);
  const rings = new THREE.InstancedMesh(new THREE.TorusGeometry(3.65, .22, 4, 20), orange, 256);
  const transform = new THREE.Object3D();
  const phaseMap = KhoraAcoustics.synthesize([0, 0, .126]).phases;
  const color = new THREE.Color();
  for (let index = 0; index < 256; index++) {
    const x = (index % 16 - 7.5) * 10;
    const z = (Math.floor(index / 16) - 7.5) * 10 + 20;
    transform.rotation.set(0, 0, 0);
    transform.position.set(x, 13, z);
    transform.updateMatrix();
    transducers.setMatrixAt(index, transform.matrix);
    transform.position.y = 16.2;
    transform.updateMatrix();
    caps.setMatrixAt(index, transform.matrix);
    transform.position.y = 16.5;
    transform.rotation.x = -Math.PI / 2;
    transform.updateMatrix();
    rings.setMatrixAt(index, transform.matrix);
    color.setRGB(.4 + .6 * phaseMap[index] / 255, .17, .035);
    rings.setColorAt(index, color);
  }
  scene.add(transducers, caps, rings);

  const plate = new THREE.Mesh(new THREE.BoxGeometry(168, 142, 1.7),
    new THREE.MeshPhysicalMaterial({color: 0xbce5e9, metalness: .03, roughness: .14,
      transmission: .65, transparent: true, opacity: .28, side: THREE.DoubleSide, depthWrite: false}));
  plate.rotation.x = -Math.PI / 4;
  plate.position.set(0, 70, 0);
  optics.add(plate);
  const outline = new THREE.LineSegments(new THREE.EdgesGeometry(plate.geometry), new THREE.LineBasicMaterial({color: 0x9ec8d0, transparent: true, opacity: .65}));
  outline.rotation.copy(plate.rotation);
  outline.position.copy(plate.position);
  optics.add(outline);
  for (const x of [-88, 88]) {
    const support = box(3, 144, 3, chassis, x, 70, 0, optics);
    support.rotation.x = -Math.PI / 4;
    box(11, 5, 17, edge, x, 21, 50, optics);
  }
  box(100, 5, 36, chassis, 0, 27, -90, optics);
  const display = box(91, .2, 29, new THREE.MeshBasicMaterial({color: 0x74cfd5}), 0, 30, -90, optics);
  display.material.transparent = true;
  display.material.opacity = .75;
  for (let x = -50; x <= 50; x += 25) {
    for (const localY of [-35, 35]) {
      const hit = [x, 70 + localY / Math.SQRT2, -localY / Math.SQRT2];
      line([[0, 30, -90], hit, [0, 140, 20]], 0x9adce5, .32, optics);
    }
  }
  label('DCRA / 45°', [96, 117, -30], '#98c9d0', optics);

  const hologramCanvas = document.createElement('canvas');
  hologramCanvas.width = hologramCanvas.height = 256;
  const ctx = hologramCanvas.getContext('2d');
  ctx.strokeStyle = '#b0f4ff';
  ctx.lineWidth = 2;
  ctx.strokeRect(16, 16, 224, 224);
  ctx.beginPath();ctx.arc(128, 117, 62, 0, Math.PI * 2);ctx.stroke();
  ctx.fillStyle = '#ff622a';
  ctx.beginPath();ctx.arc(128, 117, 46, 0, Math.PI * 2);ctx.fill();
  ctx.fillStyle = '#07090b';ctx.font = '48px Arial';ctx.textAlign = 'center';ctx.fillText('+', 128, 134);
  ctx.fillStyle = '#b0f4ff';ctx.font = '13px Consolas';ctx.fillText('AERIAL IMAGE', 128, 219);
  const image = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), new THREE.MeshBasicMaterial({
    map: new THREE.CanvasTexture(hologramCanvas), transparent: true, side: THREE.DoubleSide, depthWrite: false}));
  image.position.set(0, 140, 20);
  scene.add(image);
  label('IMAGE PLANE', [52, 180, 20], '#e6e9e9');
  line([[0, 169, 20], [20, 180, 20], [80, 180, 20]], 0xa2a9b0, .4);

  for (const x of [-65, -30, 30, 65]) for (const z of [-45, 75]) {
    line([[x, 17, z], [0, 140, 20]], 0xff6b36, .17, acoustics);
  }
  for (const y of [45, 76, 107]) {
    const radius = (140 - y) * .46;
    const ring = new THREE.Mesh(new THREE.TorusGeometry(radius, .25, 4, 64), new THREE.MeshBasicMaterial({color: 0xff6938, transparent: true, opacity: .25, depthWrite: false}));
    ring.rotation.x = -Math.PI / 2;
    ring.position.set(0, y, 20);
    acoustics.add(ring);
  }
  label('256 × 40 kHz', [-104, 38, 75], '#ed9c73', acoustics);
  const grid = new THREE.GridHelper(340, 34, 0x34363c, 0x1b1e24);
  grid.position.y = -19;
  grid.material.transparent = true;
  grid.material.opacity = .45;
  scene.add(grid);

  function render() { renderer.render(scene, camera); }
  function resize() {
    const bounds = canvas.getBoundingClientRect();
    renderer.setSize(bounds.width, bounds.height, false);
    camera.aspect = bounds.width / bounds.height;
    camera.fov = 36 * Math.max(1, Math.min(1.5, 1.1 / camera.aspect));
    camera.updateProjectionMatrix();
    render();
  }
  new ResizeObserver(resize).observe(canvas.parentElement);
  controls.addEventListener('change', render);
  let visible = true;
  new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; }).observe(canvas);
  function tick() {
    requestAnimationFrame(tick);
    if (visible && !document.hidden) controls.update();
  }
  tick();
  document.querySelectorAll('[data-rig]').forEach(button => button.addEventListener('click', () => {
    const mode = button.dataset.rig;
    optics.visible = mode !== 'haptics';
    acoustics.visible = mode !== 'optics';
    rings.visible = mode !== 'optics';
    document.querySelectorAll('[data-rig]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    render();
  }));
  document.getElementById('rig-reset').addEventListener('click', () => {
    camera.position.copy(home);
    controls.target.set(0, 68, -5);
    controls.update();
    render();
  });
  canvas.addEventListener('webglcontextlost', () => { document.getElementById('rig-fallback').hidden = false; });
  resize();
})();
