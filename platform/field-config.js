(function (root) {
  'use strict';

  const bounds = {x: [-60, 60, 0], y: [-60, 60, 0], z: [40, 240, 140], plane: [0, 2, 0], quantity: [0, 1, 0], taper: [0, 1, 0]};

  function parse(hash) {
    const params = new URLSearchParams(hash.replace(/^#/, ''));
    return Object.fromEntries(Object.entries(bounds).map(([key, [min, max, fallback]]) => {
      const raw = params.get(key);
      const value = raw === null || raw.trim() === '' ? fallback : Number(raw);
      return [key, Number.isFinite(value) ? Math.min(max, Math.max(min, Math.round(value))) : fallback];
    }));
  }

  function encode(config) {
    const normalized = parse(new URLSearchParams(config).toString());
    return new URLSearchParams(normalized).toString();
  }

  function phaseExport(config, drive) {
    const normalized = parse(encode(config));
    return {
      schema: 'khora.phase-map/1',
      purpose: 'uncalibrated simulation',
      carrier_hz: 40000,
      temperature_c: 20,
      frame: 'array XY, propagation +Z, metres',
      focus_m: [normalized.x, normalized.y, normalized.z].map(value => value / 1000),
      array: {rows: 16, columns: 16, pitch_m: .01, piston_radius_m: .005, order: 'row-major'},
      source_peak_pa_at_1m: 1,
      phase_convention: 'Re{p exp(-i omega t)}, outgoing exp(+i k r)',
      phase_step_rad: 2 * Math.PI / 256,
      phase_u8: Array.from(drive.phases),
      amplitude_u8: Array.from(drive.weights),
      phase_only_serial_compatible: !normalized.taper
    };
  }

  const api = {parse, encode, phaseExport};
  if (typeof module !== 'undefined') module.exports = api;
  else root.KhoraFieldConfig = api;
})(globalThis);
