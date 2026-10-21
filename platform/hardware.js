(() => {
  'use strict';
  const $ = (id) => document.getElementById(id),
    t = KhoraUI.t;
  let current,
    stagedSnapshot = null,
    busy = false;
  const cells = Array.from({ length: 16 }, (_, i) => {
    const cell = document.createElement('div');
    cell.className = 'phase-cell';
    const label = document.createElement('span'),
      value = document.createElement('strong');
    label.textContent = `GPIO ${i}`;
    cell.append(label, value);
    $('phase-grid').append(cell);
    return value;
  });
  const device = new KhoraPico.PicoDevice(update);
  function update() {
    const info = device.info,
      connected = device.connected;
    $('pico-state').textContent = device.armed
      ? t('SALIDA HABILITADA', 'OUTPUT ENABLED')
      : connected
        ? info.mode === 'simulation'
          ? t('SIMULADOR · SALIDA DESACTIVADA', 'SIMULATOR · OUTPUT OFF')
          : t('PICO CONECTADO', 'PICO CONNECTED')
        : t('DESCONECTADO', 'DISCONNECTED');
    $('pico-state').dataset.state = device.armed ? 'armed' : info.fault ? 'fault' : 'idle';
    $('pico-info').textContent =
      `${t('Conexión', 'Connection')}: ${info.mode}\n${t('Canales', 'Channels')}: 16\n${t('Fallo', 'Fault')}: ${info.fault || 0}\n${t('Fases enviadas', 'Phases sent')}: ${Boolean(info.phasesStaged)}`;
    $('pico-simulate').disabled = connected || busy;
    $('pico-connect').disabled = connected || busy || !navigator.serial;
    $('pico-stage').disabled = !connected || busy;
    const currentStaged = stagedSnapshot && current.every((x, i) => x === stagedSnapshot[i]);
    $('pico-arm').disabled =
      !connected ||
      busy ||
      device.armed ||
      !info.outputPermission ||
      Boolean(info.fault) ||
      !currentStaged ||
      !$('pico-interlock').checked;
  }
  function recompute() {
    const focus = ['x', 'y', 'z'].map((axis) => {
      const value = Number($(`pico-${axis}`).value);
      $(`pico-${axis}-value`).textContent = `${value} mm`;
      return value / 1000;
    });
    current = KhoraPico.phasesAt(focus);
    cells.forEach((cell, index) => {
      cell.textContent = `0x${current[index].toString(16).padStart(2, '0').toUpperCase()}`;
    });
    update();
  }
  async function run(action) {
    busy = true;
    update();
    $('pico-message').textContent = '';
    try {
      await action();
    } catch (error) {
      $('pico-message').textContent = error.message;
    } finally {
      busy = false;
      update();
    }
  }
  $('pico-simulate').addEventListener('click', () => run(() => device.simulate()));
  $('pico-connect').addEventListener('click', () => run(() => device.connect()));
  $('pico-stage').addEventListener('click', () =>
    run(async () => {
      const snapshot = current.slice();
      await device.stage(snapshot);
      stagedSnapshot = snapshot;
    }),
  );
  $('pico-arm').addEventListener('click', () => run(() => device.arm()));
  $('pico-stop').addEventListener('click', () =>
    run(async () => {
      await device.stop();
      stagedSnapshot = null;
    }),
  );
  $('pico-interlock').addEventListener('change', update);
  ['x', 'y', 'z'].forEach((axis) => $(`pico-${axis}`).addEventListener('input', recompute));
  $('pico-export').addEventListener('click', () => {
    const payload = {
      schema: 'khora.pico-phase-map/1',
      channels: 16,
      rows: 4,
      columns: 4,
      pitch_m: 0.016,
      carrier_hz: 40000,
      focus_m: ['x', 'y', 'z'].map((axis) => Number($(`pico-${axis}`).value) / 1000),
      phase_u8: Array.from(current),
      output_enabled: false,
    };
    const url = URL.createObjectURL(
        new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }),
      ),
      link = document.createElement('a');
    link.href = url;
    link.download = 'khora-pico-16-phases.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  document.addEventListener('khora:language', update);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) void device.stop();
  });
  window.addEventListener('pagehide', () => void device.close());
  recompute();
})();
