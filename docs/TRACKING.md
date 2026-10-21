# Tracking inputs

## Ultraleap

`examples/04_leap_tracking.py` uses the official `leap` Python bindings and the installed Ultraleap Tracking Service. It reads the index fingertip from tracking events, converts millimetres to metres and applies an explicitly supplied rigid sensor-to-array transform. It retains the latest frame, rejects replayed frame IDs and expires locally received data after 50 ms.

Install the official [Ultraleap LeapC Python bindings](https://github.com/ultraleap/leapc-python-bindings) using their instructions for your Tracking Service and Python version. KHORA does not assume a WebHID descriptor or an undocumented WebSocket service. Follow the manufacturer's compatibility list for Leap Motion Controller 2 / Stereo IR 170 and the installed Gemini or Hyperion runtime.

Create a JSON file containing `sensor_to_array`, a measured 4 × 4 rigid transform with translation in metres. Identity below illustrates the format only and is **not** a measured registration:

```json
{"sensor_to_array":[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]}
```

```sh
python examples/04_leap_tracking.py --calibration measured-registration.json
```

The optional `--port COM4` stages a 16-channel phase map at up to 50 host updates/s with outputs disabled. It does not arm a device. Losing fresh tracking ends that staging session. Out-of-workspace coordinates cause an error rather than a silently clamped physical target. The transform validator checks orthonormality and handedness; it cannot verify the quality of the measurements you supply.

The example uses the [official tracking listener interface](https://github.com/ultraleap/leapc-python-bindings/blob/main/examples/tracking_event_example.py). It has not been run against a physical Ultraleap sensor on this development host. Local receipt age is not sensor acquisition age. No 160 Hz rate, ±0.5 mm accuracy or end-to-end latency is guaranteed by this code.

## Webcam fallback

The robotics page offers an explicit **Use camera to choose the target** button. It loads MediaPipe Tasks Vision 0.10.21 and a hand-landmarker model on demand. Video stays in the browser. Closing the page, hiding it or choosing Stop releases the stream. Without camera permission or network access, manual sliders remain available.

The index fingertip selects a **virtual simulation target**; this mapping does not estimate a calibrated robot-base position or actuate hardware. Choose Calculate plan to review a path before simulating it. Browser tests verify target selection and stream cleanup with a mocked detector/video stream, not tracking accuracy on real hands.

Model and SDK download hosts are jsDelivr and Google model storage. No download occurs until the camera feature is activated. See the [MediaPipe Hand Landmarker web guide](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/web_js).

The real SDK/model were also initialized in headless Edge with a synthetic blank video stream: inference returned no hand and the page reported no JavaScript error. This checks model loading and CSP compatibility, not performance or accuracy on a physical camera.
