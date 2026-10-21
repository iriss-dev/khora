(() => {
  'use strict';
  const R = KhoraRobot,
    $ = (id) => document.getElementById(id),
    t = KhoraUI.t;
  let q = R.home.slice(),
    planned = null,
    running = false,
    started = 0,
    renderer,
    scene,
    camera,
    controls,
    pathLine;
  const links = [],
    joints = [];
  let targetMesh, tipMesh;
  const world = (p) => new THREE.Vector3(p[0], p[2], -p[1]);
  function state(name) {
    $('robot-state').dataset.state = name;
    $('robot-state').textContent = {
      idle: t('SIMULACIÓN', 'SIMULATION'),
      ready: t('PLAN DISPONIBLE', 'PLAN READY'),
      running: t('SIMULANDO', 'SIMULATING'),
      stopped: t('DETENIDO', 'STOPPED'),
      complete: t('COMPLETADO', 'COMPLETED'),
    }[name];
  }
  function target() {
    return ['x', 'y', 'z'].map((axis) => Number($(`robot-${axis}`).value) / 1000);
  }
  function render() {
    if (renderer) renderer.render(scene, camera);
  }
  function setPose(value) {
    q = value.slice();
    const fk = R.forward(q);
    $('robot-joints').replaceChildren(
      ...q.map((angle, index) => {
        const cell = document.createElement('span');
        cell.textContent = `J${index + 1}: ${((angle * 180) / Math.PI).toFixed(1)}°`;
        return cell;
      }),
    );
    if (!renderer) return;
    const points = [[0, 0, 0], ...fk.points];
    links.forEach((link, index) => {
      const a = world(points[index]),
        b = world(points[index + 1]),
        direction = b.clone().sub(a);
      link.position.copy(a).add(b).multiplyScalar(0.5);
      link.scale.set(1, direction.length(), 1);
      link.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
      joints[index].position.copy(b);
    });
    tipMesh.position.copy(world(fk.position));
    render();
  }
  function updateTarget() {
    ['x', 'y', 'z'].forEach((axis) => {
      $(`robot-${axis}-value`).textContent = `${$(`robot-${axis}`).value} mm`;
    });
    if (targetMesh) targetMesh.position.copy(world(target()));
    render();
  }
  function loadPlan(plan) {
    planned = R.validatePlan(plan);
    running = false;
    $('robot-run').disabled = false;
    $('robot-export').disabled = false;
    $('robot-duration').textContent = `${planned.duration_s.toFixed(2)} s`;
    const last = planned.samples[100].position_m;
    $('robot-error').textContent =
      `${(Math.hypot(...last.map((x, i) => x - planned.target_m[i])) * 1000).toFixed(3)} mm`;
    $('robot-progress').textContent = '0%';
    $('robot-message').textContent = '';
    ['x', 'y', 'z'].forEach((axis, index) => {
      $(`robot-${axis}`).value = Math.round(planned.target_m[index] * 1000);
    });
    if (renderer) {
      if (pathLine) {
        scene.remove(pathLine);
        pathLine.geometry.dispose();
        pathLine.material.dispose();
      }
      pathLine = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(
          planned.samples.map((sample) => world(sample.position_m)),
        ),
        new THREE.LineBasicMaterial({ color: 0xff7849, transparent: true, opacity: 0.55 }),
      );
      scene.add(pathLine);
    }
    setPose(planned.samples[0].joints_rad);
    updateTarget();
    state('ready');
  }
  function attempt(action) {
    try {
      action();
    } catch (error) {
      $('robot-message').textContent = error.message;
    }
  }
  $('robot-plan').addEventListener('click', () => attempt(() => loadPlan(R.plan(target(), q))));
  $('robot-run').addEventListener('click', () => {
    if (!planned) return;
    started = performance.now();
    running = true;
    $('robot-run').disabled = true;
    state('running');
  });
  $('robot-stop').addEventListener('click', () => {
    running = false;
    $('robot-run').disabled = true;
    state('stopped');
  });
  $('robot-home').addEventListener('click', () => {
    running = false;
    planned = null;
    setPose(R.home);
    $('robot-run').disabled = true;
    $('robot-export').disabled = true;
    $('robot-progress').textContent = '0%';
    $('robot-duration').textContent = '—';
    $('robot-error').textContent = '—';
    state('idle');
  });
  ['x', 'y', 'z'].forEach((axis) =>
    $(`robot-${axis}`).addEventListener('input', () => {
      running = false;
      planned = null;
      $('robot-run').disabled = true;
      $('robot-export').disabled = true;
      updateTarget();
      state('idle');
    }),
  );
  $('robot-tool-apply').addEventListener('click', () =>
    attempt(() => {
      const request = JSON.parse($('robot-tool').value);
      if (
        request.name !== 'khora_robot_plan_move' ||
        !request.arguments ||
        Object.keys(request.arguments).some(
          (key) => !['target_m', 'start_joints_rad'].includes(key),
        )
      )
        throw new Error(t('Solicitud MCP no compatible', 'Unsupported MCP request'));
      loadPlan(R.plan(request.arguments.target_m, request.arguments.start_joints_rad || q));
    }),
  );
  $('robot-import').addEventListener('change', async () => {
    const file = $('robot-import').files[0];
    if (!file) return;
    if (file.size > 1048576) {
      $('robot-message').textContent = t('El plan supera 1 MiB', 'Plan exceeds 1 MiB');
      return;
    }
    try {
      loadPlan(JSON.parse(await file.text()));
    } catch (error) {
      $('robot-message').textContent = error.message;
    }
    $('robot-import').value = '';
  });
  $('robot-export').addEventListener('click', () => {
    if (!planned) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(planned, null, 2)], { type: 'application/json' }),
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = 'khora-robot-plan.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  try {
    renderer = new THREE.WebGLRenderer({ canvas: $('robot-canvas'), antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    renderer.setClearColor(0x0b1018);
    renderer.outputEncoding = THREE.sRGBEncoding;
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(40, 1, 0.01, 20);
    camera.position.set(1.35, 1.1, 1.6);
    controls = new THREE.OrbitControls(camera, $('robot-canvas'));
    controls.target.set(0.05, 0.5, 0);
    controls.enableDamping = true;
    controls.enablePan = false;
    controls.minDistance = 0.8;
    controls.maxDistance = 4;
    controls.update();
    controls.addEventListener('change', render);
    scene.add(new THREE.HemisphereLight(0xc5e6ff, 0x202c42, 1.4));
    const light = new THREE.DirectionalLight(0xffffff, 1.8);
    light.position.set(2, 3, 2);
    scene.add(light);
    scene.add(new THREE.GridHelper(1.6, 16, 0x435565, 0x263342));
    const body = new THREE.MeshStandardMaterial({
      color: 0x7894a5,
      metalness: 0.4,
      roughness: 0.45,
    });
    const motor = new THREE.MeshStandardMaterial({
      color: 0x232f3d,
      metalness: 0.3,
      roughness: 0.5,
    });
    const horn = new THREE.MeshBasicMaterial({ color: 0xff7849 });
    for (let i = 0; i < 6; i++) {
      const link = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.023, 1, 12), body);
      scene.add(link);
      links.push(link);
      const joint = new THREE.Group();
      joint.add(new THREE.Mesh(new THREE.BoxGeometry(0.062, 0.052, 0.042), motor));
      const axle = new THREE.Mesh(new THREE.CylinderGeometry(0.026, 0.026, 0.014, 20), horn);
      axle.rotation.x = Math.PI / 2;
      axle.position.z = 0.026;
      joint.add(axle);
      const encoder = new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.011, 0.016, 16), body);
      encoder.rotation.x = Math.PI / 2;
      encoder.position.z = 0.033;
      joint.add(encoder);
      scene.add(joint);
      joints.push(joint);
    }
    const base = new THREE.Mesh(
      new THREE.CylinderGeometry(0.1, 0.12, 0.035, 32),
      new THREE.MeshStandardMaterial({ color: 0x263544, metalness: 0.5, roughness: 0.5 }),
    );
    base.position.y = 0.018;
    scene.add(base);
    targetMesh = new THREE.Group();
    for (let axis = 0; axis < 3; axis++) {
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.035, 0.0016, 5, 36),
        new THREE.MeshBasicMaterial({ color: 0x75e5ec }),
      );
      if (axis === 1) ring.rotation.x = Math.PI / 2;
      if (axis === 2) ring.rotation.y = Math.PI / 2;
      targetMesh.add(ring);
    }
    scene.add(targetMesh);
    tipMesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.012, 16, 12),
      new THREE.MeshBasicMaterial({ color: 0xfff3cf }),
    );
    scene.add(tipMesh);
    new ResizeObserver(() => {
      const bounds = $('robot-canvas').getBoundingClientRect();
      renderer.setSize(bounds.width, bounds.height, false);
      camera.aspect = bounds.width / bounds.height;
      camera.updateProjectionMatrix();
      render();
    }).observe($('robot-canvas').parentElement);
  } catch {
    $('robot-fallback').hidden = false;
    renderer = null;
  }
  let visible = true;
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
  }).observe($('robot-canvas'));
  function tick(now) {
    requestAnimationFrame(tick);
    if (running && planned) {
      const progress = Math.min(1, (now - started) / (planned.duration_s * 1000)),
        at = progress * 100,
        index = Math.min(99, Math.floor(at)),
        fraction = at - index;
      const a = planned.samples[index].joints_rad,
        b = planned.samples[index + 1].joints_rad;
      setPose(a.map((x, i) => x + (b[i] - x) * fraction));
      $('robot-progress').textContent = `${Math.round(progress * 100)}%`;
      if (progress === 1) {
        running = false;
        $('robot-run').disabled = false;
        state('complete');
      }
    }
    if (visible && !document.hidden) controls?.update();
  }
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && running) {
      running = false;
      $('robot-run').disabled = true;
      state('stopped');
    }
  });
  document.addEventListener('khora:camera-target', (event) => {
    if (running) return;
    const value = event.detail;
    if (!Array.isArray(value) || value.length !== 3 || !value.every(Number.isFinite)) return;
    ['x', 'y', 'z'].forEach((axis, index) => {
      $(`robot-${axis}`).value = Math.round(value[index] * 1000);
    });
    planned = null;
    $('robot-run').disabled = true;
    $('robot-export').disabled = true;
    updateTarget();
    state('idle');
  });
  setPose(q);
  updateTarget();
  state('idle');
  requestAnimationFrame(tick);
})();
