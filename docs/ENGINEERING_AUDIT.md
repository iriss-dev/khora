# Spatial field and hardware transport audit

This records the v0.2 audit. The v0.3 standalone Pico target, robot/MCP tools
and tracking adapters are documented in [Pico hardware](PICO_HARDWARE.md),
[AI and robotics](AI_AND_ROBOTICS.md) and [tracking](TRACKING.md).
Historical statements about a missing board adapter describe the original v1 target.

Date: 2026-10-20. Baseline: `3c6c96e`. Scope: local platform, acoustic models,
optical assumptions and portable firmware. Numerical validation is distinct
from validation of an assembled optical-acoustic instrument.

## Findings and changes

| Baseline finding | Change | Remaining boundary |
| --- | --- | --- |
| 8-bit phases scaled by 255; timer decoded with 256 | Circular nearest-bin quantization in Python, JavaScript and Rust | Board timer quantization must also be characterized |
| Source pressure of 120 Pa at 1 m treated as calibrated | Explicit illustrative 1 Pa **peak** at 1 m and uncalibrated labels | Replace with measured complex element responses before predicting a device |
| Reflecting boundary comment omitted a factor of two | Explicit reflected power fraction; pressure and force have different units | Skin, angular incidence and standing waves need a boundary model |
| Focal force obtained from pressure at one point times an assumed wavelength disk | Midpoint integral over a stated 10 × 10 mm patch | Grid convergence and physical patch geometry matter |
| Rigid plate tilt fabricated astigmatism and changed magnification | Ideal conjugation remains a plane reflection | Micro-mirror errors, finite aperture, scatter and alignment require measurements |
| UI displayed a fixed watchdog PASS and armed interlock | Unmeasured state; hardware ACK RTT is measured separately | ACK is not acoustic onset or sensor-to-skin latency |
| Camera/export buttons called missing functions | Unsupported controls are disabled and labelled; 3D switching no longer calls a missing stop function | No calibrated webcam, LeapC adapter or target-specific export is shipped |
| Watchdog feed never set its timestamp; cutoff used `> 50` | Timestamped feed, `>= 50`, sequence freshness, wrap handling and latched fault | Portable state cannot turn off a physical GPIO without board integration |
| AM LUT exceeded Q15 and modulation depth was ignored | Bounded periodic LUT and fixed-point depth | Duty trimming is not a calibrated linear acoustic-amplitude control |
| Titles, replies and bodies entered HTML sinks unescaped | Text encoding at these sinks; citation uses an ID | Legacy inline handlers remain; no ASVS Level 3 certification |

The 18 original tests passed before changes. Those tests were insufficient to
establish the physical claims above. In particular, `telemetry.py` contained
neither a watchdog nor a FIFO, and its `SpatialKalmanFilter` is an exponential
smoother, not a covariance-based Kalman estimator.

## Interface architecture

The primary surface is an acoustic instrument with an explicit coordinate
frame, physical units, a pressure scale and numerical provenance. Section
selection, field quantity and aperture weighting form one control group;
focus coordinates form another. A separate transport strip owns connection
and acknowledgement state. Colour represents a scalar field, not an animated
suggestion of acoustic intensity.

The three section planes cut the same 3D model. XZ and YZ span 320 × 240 mm;
XY spans 320 × 320 mm at the focal height. The circle marks the commanded focus,
which need not equal the actual pressure maximum. Relative colour is clipped
at the focal reference and rescales on focus changes. The force-density view
uses mN/mm²; the patch integral uses mN; its lateral derivative uses mN/mm.
The UI explicitly states these distinctions.

The older optical and assembly views remain under a disclosure. The notebook
places experiment content before voting. Scientific status must eventually
come from attached data, code and review records; vote counts cannot determine
whether an experiment is reproducible. The current feed is bundled example
content and session-local submissions, not a network community service.

The implementation uses local Three.js, keyboard-accessible native controls,
responsive metric panels and visible focus indicators. The renderer evaluates
320 × 240 samples on input changes, not on a permanent animation loop. The
displayed CPU/submit duration is not a GPU timing measurement. Real 40 kHz wave
motion cannot be represented temporally by a 60 Hz display without aliasing.

## Acoustic model

Use `Re{p exp(-i omega t)}` and outgoing `exp(+i k r)`. Therefore:

\[
\phi_i=(-k\|r_f-r_i\|)\bmod 2\pi,\qquad
q_i=\lfloor256\phi_i/(2\pi)+1/2\rfloor\bmod256.
\]

The reconstructed phase is `2 pi q_i / 256`. The circular rounding error is at
most `pi/256` radians, or 0.703125 degrees. Changing the phasor convention changes
both signs; a hardware driver must document whether its register is a delay or
an advancing phase. At 40 kHz, one phase bin corresponds to 97.65625 ns. A 125 MHz
timer has 3125 ticks per carrier period, so not every phase bin maps to the same
integer tick interval. The protocol is an acoustic phase command, not a
guarantee of a particular timer or GPIO implementation.

For a circular element of radius `a`, the interactive approximation is

\[
\tilde p(r)=\sum_i {A_i w_i\over R_i}
 {2J_1(ka\sin\theta_i)\over ka\sin\theta_i}
 e^{i(kR_i+2\pi q_i/256)},\quad R_i=\|r-r_i\|.
\]

`A_i` is peak pressure at 1 m times 1 m; `w_i` is the aperture amplitude.
The directivity limit on axis is one, and negative sidelobe values retain
their sign. The 16-term series used by the shader is evaluated only within
`ka ≈ 3.66` for the fixed 40 kHz, 5 mm radius configuration. This is the
far-field approximation of **each element**; spherical propagation across
the entire aperture remains in the sum. Samples below 20 mm are excluded by
the CPU model. This is not a full near-field or nonlinear solver.

The slower Python reference evaluates the baffled-piston Rayleigh integral:

\[
\tilde p(r)={-i\rho\omega\over2\pi}
 \int_S v(s){e^{ik|r-s|}\over|r-s|}\,dS.
\]

Equal-area radial quadrature is compared against the analytic axial disk
solution. The element approximation is checked against that reference at
distance. It does not silently replace the integral at the radiating surface.
The piston model follows the formulation in
[Phase Optimization for Multipoint Haptic Feedback Based on Ultrasound Array](https://www.mdpi.com/1424-8220/22/6/2394).

With peak phasors, `p_rms = |p| / sqrt(2)`. For a locally normally incident
plane wave on an opaque surface with reflected **power** fraction R:

\[
I={p_{rms}^2\over\rho c},\qquad
P_{rad}=(1+R){p_{rms}^2\over\rho c^2},\qquad
F_n=\int_{S_{skin}}P_{rad}\,dS.
\]

R=0 is absorbing and R=1 is perfectly reflecting. The earlier equality
`2 I/c = p_rms²/(rho c²)` was inconsistent under its RMS definition. Applying
this plane-wave estimate locally to a focused field remains an approximation.
Oblique incidence, tissue transmission and deformation are not included.
The UI differentiates the integral using a 1 mm central difference while
holding drive phases fixed; recomputing the focus at both samples would give
the derivative of a different experiment.

At 40 kHz, wavelength is approximately 8.58 mm. A 10 mm pitch exceeds half a
wavelength, so grating lobes are possible. A square array is not a circular
aperture with a universal Airy disk. Both the element directivity and array
interference matter. Hann taper suppresses some sidelobes but broadens the
focus and reduces peak pressure at unchanged per-element gain. The current
wire protocol carries phase only, so tapered drives cannot be staged.

The default focus `[0,0,0.14] m` gives approximately 891.6 Pa RMS and 0.608 mN
over the 10 mm square with the illustrative source strength. These are model
outputs, not measurements. Increasing source amplitude by two multiplies the
predicted force by four. There is no supported universal 8–15 mN claim.

An AM envelope is also squared by radiation pressure. For
`a(t)=(1+m cos(omega_m t))/(1+m)`, mean squared amplitude is
`(1+m²/2)/(1+m)²`. A 200 Hz amplitude envelope produces a force waveform with
DC, 200 Hz and 400 Hz terms. A desired sinusoidal force needs square-root
amplitude shaping followed by measured driver compensation. The field UI
shows unmodulated steady-state estimates; Web Audio is an audible preview.

## Optical geometry

For plate origin `o` and unit normal `n`, ideal source conjugation is

\[
s'=s-2n[n\cdot(s-o)].
\]

The equal distances are measured normal to the plate, not necessarily along
the chassis vertical. A rigid plate rotation changes the reflected image pose
while retaining unity scale. It does not alone create astigmatism in this
model. `2 d delta_theta` can estimate a lateral displacement for a specified
pivot and small angle; it is not a general aberration law. At `d=100 mm` and
`delta_theta=0.2 degrees`, that estimate is 0.698 mm. Therefore a tolerance must
come from the required registration error and actual mounting geometry.

The PBR glass in the assembly view illustrates appearance. Refraction with
IOR 1.52 and transmission 0.88 does not simulate double mirror reflections or
prove DCRA imaging efficiency. A single flat display conjugated by one ideal
plate creates a real image of that plane, not an arbitrary volumetric light
field. See [Asukanet's aerial imaging overview](https://www.asukanet.co.jp/contents/product/aerialimaging.html).

## Transport and closed-loop architecture

See [the byte-level protocol](HARDWARE_TRANSPORT.md) for the implemented
WebSerial client and dry-staging C receiver. The browser owns visualization,
inspection and manual staging. A production control path should be:

```
IR camera -> native LeapC service -> time/SE(3) calibration -> latest sample
         -> deterministic controller -> double-buffered phase engine -> drivers
Browser <- decimated telemetry and measured timing <- controller
```

Leap Motion is not a generic serial XYZ sensor. Its supported tracking path
uses a native service and LeapC; an authenticated local bridge would expose
decimated frames to the browser. The current platform does not ship that
bridge, and its CSP deliberately does not allow arbitrary localhost services.
See [LeapC concepts](https://docs.ultraleap.com/api-reference/tracking-api/leapc-guide/leap-concepts.html)
and [clock rebasing](https://docs.ultraleap.com/api-reference/tracking-api/leapc-guide/using-leapc.html).

The production sample contract should include sensor frame ID, source time,
confidence, calibration ID, frame of reference, covariance and expiry time.
Calibrate `T_array_sensor` against independent landmarks, convert millimetres
to metres once, and reject out-of-workspace or stale samples before phase
synthesis. A latest-only mailbox avoids queued obsolete targets. No camera
heuristic or field-rendering callback should feed a hardware watchdog.

At 1 Mbaud with UART 8N1, the 268-byte phase frame alone consumes 2.68 ms;
a 13-byte ACK consumes 0.13 ms. USB CDC baud configuration need not represent
physical serial bitrate. A proposed **post-tracker-delivery** budget is 1 ms
transform/synthesis, 3 ms transfer, 0.5 ms validation/staging and 0.025 ms
carrier-boundary commit. This is a target, not a measured bound. Camera
exposure, tracker processing, OS scheduling and clock uncertainty must be
added for sensor-to-output latency. A 120 Hz sensor has an 8.33 ms sample
period before these other delays. Browser scheduling has no real-time bound.

Measure p50/p95/p99, worst observed latency and dropout rate using the sensor
timestamp and a controller output marker with synchronized clocks. ACK RTT
only measures a host transaction; it cannot establish <10 ms motion-to-touch.

At 256 independent channels, the MCU is a coordinator for an FPGA/CPLD or a
synchronized driver fabric. RP2040's pin and PIO resources do not provide 256
independent direct outputs. Commit complete phase banks on a shared carrier
boundary; keep envelope generation, physical output-enable, overcurrent and
thermal shutdown on the controller. See the
[RP2040 datasheet](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf).

## Three research directions

These are proposed KHORA research capabilities, not claims of priority.
Robotic haptic-field mapping already exists, as shown in
[Mapping Mid-air Haptics with a Low-cost Tactile Robot](https://arxiv.org/abs/2207.01554),
and combined optical/acoustic interaction has precedents such as
[the Levitate project](https://docs.ultraleap.com/ultralab/levitate-project.html).

1. **A field calibrated by a robotic probe, with uncertainty attached to every
   displayed force.** Scan complex pressure and normal force on a spatial grid,
   estimate per-channel gain/phase and joint optical registration, then solve
   regularized inverse synthesis with exclusion zones. Use held-out points
   to measure prediction error and repeatability. The distinguishing target
   is a reproducible calibration package linking optical, acoustic and robot
   frames, not simply attaching a robot arm to a haptic array.
2. **Tactile display of robotic manipulability and contact uncertainty.** Map
   singular values of a scaled task Jacobian and contact covariance to spatial
   pulse patterns around a floating path handle. Drive rate and intensity from
   bounded, perceptually calibrated mappings. Test whether users detect poor
   approach directions faster than with visual warnings, while the robot's
   independent controller retains trajectory authority. Ultrasound conveys
   cues; it cannot physically restrain an arm or substitute for collision control.
3. **Optical-acoustic registration that adapts to a moving interaction surface.**
   Predict a fingertip tangent patch with a bounded motion model, co-register
   an aerial contour and optimize pressure on that patch while penalizing
   off-target exposure. Encode confidence by reducing or withholding the cue.
   Evaluate spatial registration error, dropout behaviour and task accuracy
   against a static focus. A single DCRA plate does not acquire arbitrary
   optical depth from software; source/plate actuation or additional optical
   channels would be a separate hardware research project.

## Validation and limits

Observed on the audit host: 28 Python tests and 10 Node tests passed. Headless
Edge passed the interaction/layout checks with zero browser errors and zero
external requests. Three selected shader readbacks differed from CPU pressure
by at most 0.007%; Python and JavaScript also agreed on all 256 phase bytes at
an off-axis focus. These samples are regression evidence, not a global error
bound or a hardware benchmark.

Run the Python suite and Node protocol/field tests:

```sh
python -m unittest discover -s tests -v
node --test tests/test_platform.cjs
```

Browser tests require Playwright and an installed Edge (default) or Chrome
(`KHORA_BROWSER_CHANNEL=chrome`). They use only a local test server:

```sh
node tests/browser_smoke.cjs
node tests/landing_smoke.cjs
```

They check controls, three GPU/CPU pressure samples, 3D mode switching,
untrusted text rendering, 390 px layout, console errors and outbound requests.
The landing checks also cover 360/390/768/1536 px layouts, language persistence,
configuration handoff, local links, and the WebGL fallback. The lab checks
exercise configuration reload, pointer interaction, and exported phase data.
Screenshots are written to ignored `build/`. The GPU comparison does not prove
accuracy everywhere; the numerical reference tests provide independent checks.
The C host suite is configured through CTest:

```sh
cmake -S firmware -B build/firmware
cmake --build build/firmware
ctest --test-dir build/firmware --output-on-failure
```

The Windows environment used for this audit lacked an executable C compiler
and Cargo. The [GitHub Actions validation](https://github.com/iriss-dev/khora/actions/runs/39534557397)
subsequently compiled the portable C library, passed its CTest regression,
and compiled the Rust core with default `std` features on Ubuntu. That run
also passed both browser suites in Chromium. It did not test embedded targets.
No physical array, calibrated tracker or acoustic exposure apparatus was
available. No hardware actuation, medical suitability, ASVS level or regulatory
compliance is established by these checks.
