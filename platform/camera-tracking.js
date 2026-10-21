(() => {
  'use strict';
  const button = document.getElementById('camera-start'),
    status = document.getElementById('camera-status'),
    video = document.getElementById('camera-video');
  let stream,
    landmarker,
    frame,
    active = false,
    lastVideo = -1,
    lastSample = 0,
    loading = false,
    generation = 0;
  const t = (es, en) => KhoraUI.t(es, en);
  function stop() {
    generation++;
    active = false;
    cancelAnimationFrame(frame);
    stream?.getTracks().forEach((track) => track.stop());
    stream = null;
    video.srcObject = null;
    video.hidden = true;
    landmarker?.close();
    landmarker = null;
    button.textContent = t(
      'Activar cámara para elegir el objetivo',
      'Use camera to choose the target',
    );
    button.setAttribute('aria-pressed', 'false');
    status.textContent = t(
      'Cámara detenida. Los controles manuales siguen disponibles.',
      'Camera stopped. Manual controls remain available.',
    );
  }
  async function start() {
    if (loading) return;
    if (active) return stop();
    loading = true;
    button.disabled = true;
    const session = ++generation;
    function current() {
      if (session !== generation || document.hidden)
        throw new Error('Camera initialization cancelled');
    }
    status.textContent = t(
      'Descargando el modelo de manos y solicitando acceso a la cámara…',
      'Downloading the hand model and requesting camera access…',
    );
    try {
      const { HandLandmarker, FilesetResolver } = await import(
        'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/vision_bundle.mjs'
      );
      current();
      const files = await FilesetResolver.forVisionTasks(
        'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/wasm',
      );
      landmarker = await HandLandmarker.createFromOptions(files, {
        baseOptions: {
          modelAssetPath:
            'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
          delegate: 'CPU',
        },
        runningMode: 'VIDEO',
        numHands: 1,
      });
      current();
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false,
      });
      current();
      video.srcObject = stream;
      video.hidden = false;
      await video.play();
      active = true;
      button.textContent = t('Detener cámara', 'Stop camera');
      button.setAttribute('aria-pressed', 'true');
      function tick(now) {
        if (!active) return;
        if (video.readyState >= 2 && video.currentTime !== lastVideo && now - lastSample >= 120) {
          lastVideo = video.currentTime;
          lastSample = now;
          let result;
          try {
            result = landmarker.detectForVideo(video, now);
          } catch (error) {
            stop();
            status.textContent = error.message;
            return;
          }
          const tip = result.landmarks[0]?.[8];
          if (tip) {
            document.dispatchEvent(
              new CustomEvent('khora:camera-target', {
                detail: [0.15 + 0.25 * (1 - tip.x), 0.3 * (0.5 - tip.x), 0.25 + 0.55 * (1 - tip.y)],
              }),
            );
            status.textContent = t(
              'Índice detectado. Revisa el objetivo y pulsa Calcular plan. Coordenadas virtuales, sin escala física.',
              'Index fingertip detected. Review the target, then choose Calculate plan. Virtual coordinates without physical scale.',
            );
          } else
            status.textContent = t(
              'No se detecta una mano. Acerca el índice a la cámara.',
              'No hand detected. Bring your index finger into view.',
            );
        }
        frame = requestAnimationFrame(tick);
      }
      frame = requestAnimationFrame(tick);
    } catch (error) {
      stop();
      status.textContent =
        t('No se pudo activar la cámara: ', 'Could not start camera: ') + error.message;
    } finally {
      loading = false;
      button.disabled = false;
    }
  }
  button.addEventListener('click', start);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stop();
  });
  window.addEventListener('pagehide', stop);
})();
