(function (root) {
  'use strict';
  const axes = [
    [0, 0, 1],
    [0, 1, 0],
    [0, 1, 0],
    [0, 0, 1],
    [0, 1, 0],
    [0, 0, 1],
  ];
  const heights = [0.15, 0.15, 0.3, 0.25, 0.1, 0.08];
  const limits = [
    [-1, 1],
    [-0.75, 0.75],
    [-0.8, 0.8],
    [-1, 1],
    [-0.75, 0.75],
    [-1, 1],
  ].map((pair) => pair.map((x) => x * Math.PI));
  const home = [0.1, 0.4, -0.7, 0, 0.3, 0];
  const add = (a, b) => a.map((x, i) => x + b[i]);
  const sub = (a, b) => a.map((x, i) => x - b[i]);
  const cross = (a, b) => [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
  const mv = (m, v) => m.map((row) => row.reduce((sum, x, i) => sum + x * v[i], 0));
  const mm = (a, b) =>
    a.map((row) => b[0].map((_, col) => row.reduce((sum, x, i) => sum + x * b[i][col], 0)));
  function vector(value, n, name) {
    if (
      !Array.isArray(value) ||
      value.length !== n ||
      !value.every((x) => typeof x === 'number' && Number.isFinite(x))
    )
      throw new Error(`${name}: se requieren ${n} números finitos / ${n} finite numbers required`);
    return value.slice();
  }
  function joints(value) {
    const q = vector(value, 6, 'joints_rad');
    q.forEach((x, i) => {
      if (x < limits[i][0] || x > limits[i][1])
        throw new Error(`Joint ${i + 1}: fuera de límites / outside limits`);
    });
    return q;
  }
  function rotation([x, y, z], q) {
    const c = Math.cos(q),
      s = Math.sin(q),
      v = 1 - c;
    return [
      [x * x * v + c, x * y * v - z * s, x * z * v + y * s],
      [y * x * v + z * s, y * y * v + c, y * z * v - x * s],
      [z * x * v - y * s, z * y * v + x * s, z * z * v + c],
    ];
  }
  function forward(value) {
    const q = joints(value),
      points = [],
      directions = [];
    let orientation = [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
      ],
      position = [0, 0, 0];
    q.forEach((angle, i) => {
      position = add(position, mv(orientation, [0, 0, heights[i]]));
      points.push(position.slice());
      directions.push(mv(orientation, axes[i]));
      orientation = mm(orientation, rotation(axes[i], angle));
    });
    return { position, orientation, points, directions };
  }
  function solve3(matrix, rhs) {
    const a = matrix.map((row, i) => [...row, rhs[i]]);
    for (let col = 0; col < 3; col++) {
      let pivot = col;
      for (let row = col + 1; row < 3; row++)
        if (Math.abs(a[row][col]) > Math.abs(a[pivot][col])) pivot = row;
      [a[col], a[pivot]] = [a[pivot], a[col]];
      const d = a[col][col];
      if (Math.abs(d) < 1e-14) throw new Error('Singular system');
      for (let j = col; j < 4; j++) a[col][j] /= d;
      for (let row = 0; row < 3; row++)
        if (row !== col) {
          const k = a[row][col];
          for (let j = col; j < 4; j++) a[row][j] -= k * a[col][j];
        }
    }
    return a.map((row) => row[3]);
  }
  function inverse(target, start = home) {
    target = vector(target, 3, 'target_m');
    if (Math.hypot(...target.slice(0, 2)) > 0.7 || target[2] < 0.15 || target[2] > 0.95)
      throw new Error('Fuera del espacio de trabajo / Outside reference workspace');
    const q = joints(start);
    for (let iteration = 0; iteration < 300; iteration++) {
      const fk = forward(q),
        error = sub(target, fk.position);
      if (Math.hypot(...error) < 1e-5) return q;
      const columns = fk.directions.map((axis, i) => cross(axis, sub(fk.position, fk.points[i])));
      const a = Array.from({ length: 3 }, (_, row) =>
        Array.from(
          { length: 3 },
          (_, col) =>
            columns.reduce((sum, j) => sum + j[row] * j[col], 0) + (row === col ? 0.0001 : 0),
        ),
      );
      const y = solve3(a, error);
      q.forEach((value, i) => {
        const step = columns[i].reduce((sum, x, k) => sum + x * y[k], 0);
        q[i] = Math.max(
          limits[i][0],
          Math.min(limits[i][1], value + Math.max(-0.25, Math.min(0.25, step))),
        );
      });
    }
    throw new Error('No se encontró una solución / No reachable solution found');
  }
  function durationFor(start, end, v = 0.8, a = 1.5, j = 8) {
    const distance = Math.max(...end.map((x, i) => Math.abs(x - start[i])));
    return Math.max(
      0.25,
      (1.875 * distance) / v,
      Math.sqrt(((10 / Math.sqrt(3)) * distance) / a),
      Math.cbrt((60 * distance) / j),
    );
  }
  function plan(target, start = home) {
    const end = inverse(target, start),
      duration = durationFor(start, end);
    return {
      schema: 'khora.robot-plan/1',
      model: 'khora-reference-6r',
      execution: 'simulation_only',
      target_m: target.slice(),
      duration_s: duration,
      motion_limits: { velocity_rad_s: 0.8, acceleration_rad_s2: 1.5, jerk_rad_s3: 8 },
      samples: Array.from({ length: 101 }, (_, i) => {
        const u = i / 100,
          s = 10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5,
          q = start.map((x, k) => x + (end[k] - x) * s);
        return { time_s: duration * u, joints_rad: q, position_m: forward(q).position };
      }),
    };
  }
  function validatePlan(data) {
    if (
      !data ||
      data.schema !== 'khora.robot-plan/1' ||
      data.model !== 'khora-reference-6r' ||
      data.execution !== 'simulation_only' ||
      !Array.isArray(data.samples) ||
      data.samples.length !== 101
    )
      throw new Error('Formato de plan no compatible / Unsupported plan format');
    const target = vector(data.target_m, 3, 'target_m'),
      start = joints(data.samples[0].joints_rad),
      end = joints(data.samples[100].joints_rad);
    if (
      !Number.isFinite(data.duration_s) ||
      data.duration_s < durationFor(start, end) - 1e-9 ||
      data.duration_s > 120
    )
      throw new Error('Duración fuera de límites / Duration outside limits');
    data.samples.forEach((sample, index) => {
      const u = index / 100,
        s = 10 * u ** 3 - 15 * u ** 4 + 6 * u ** 5,
        q = joints(sample.joints_rad);
      if (
        !Number.isFinite(sample.time_s) ||
        Math.abs(sample.time_s - data.duration_s * u) > 1e-7 ||
        q.some((x, i) => Math.abs(x - start[i] - (end[i] - start[i]) * s) > 1e-7)
      )
        throw new Error('Trayectoria inconsistente / Inconsistent trajectory');
      sample.position_m = forward(q).position;
    });
    if (Math.hypot(...sub(data.samples[100].position_m, target)) > 0.001)
      throw new Error('El plan no alcanza el objetivo / Plan does not reach target');
    return data;
  }
  const api = { axes, heights, limits, home, forward, inverse, plan, validatePlan, durationFor };
  if (typeof module !== 'undefined') module.exports = api;
  else root.KhoraRobot = api;
})(globalThis);
