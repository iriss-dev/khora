# KHORA v0.3.0-alpha

Robot trajectory playback, MCP tools, a 16-channel Pico firmware target and a public community forum.

**[Robot + AI demo](https://iriss-dev.github.io/khora/platform/robot.html)** · **[Pico control panel](https://iriss-dev.github.io/khora/platform/hardware.html)** · **[Community forum](https://github.com/iriss-dev/khora/discussions)**

## New

- Six-joint reference arm: positional DLS, product-of-exponentials forward kinematics, synchronized quintic plans, JSON export/import and 3D playback.
- Installable MCP stdio server with nine tools, lifecycle negotiation, notifications, finite input checks and disabled-output hardware staging.
- Standalone RP2040 C++/PIO firmware: 16 parallel channels, 256 phase steps, nominal 40 kHz carrier, chained DMA and three waveform banks.
- Independent MCU heartbeat lease, latched faults, physical stop/ARM inputs and separate acoustic/servo gate outputs. The default UF2 has outputs disabled.
- Python STS3215 packet/control module with explicit joint calibration, sync-write, telemetry and a 50 ms host command lease.
- Ultraleap Python adapter with rigid registration and frame expiry; optional MediaPipe webcam target selection for simulation.
- Visible forum access throughout the website and a guide to the real GitHub Discussions community. The original BBS remains an archive of local examples.

## Try it

```sh
pip install -e .
khora-mcp --simulate-device
khora-hardware
```

MCP clients can request `khora_robot_plan_move` with `{"target_m":[0.25,0.15,0.55]}` and replay the resulting JSON in the browser. There is no AI tool for ARM or physical motor execution.

## What has and has not been validated

CI covers Python, JavaScript, portable C/C++, Rust, three browser suites, a Python-to-C++ protocol round trip, package building and Pico SDK cross-compilation. Robot FK implementations are compared independently; camera wiring is tested with a mocked detector/video stream.

The 16-emitter hardware profile is separate from the 256-emitter acoustic model. No real Pico output, servo motion, optical registration, tracking accuracy, acoustic exposure or physical stopping time was measured on the development host. PIO timing is quantized and the fractional divider is not zero-jitter. Physical commissioning requires the documented external power gates, stop circuitry, measured mechanism geometry and calibration.

Read [Pico commissioning](https://github.com/iriss-dev/khora/blob/master/docs/PICO_HARDWARE.md), [AI and robotics](https://github.com/iriss-dev/khora/blob/master/docs/AI_AND_ROBOTICS.md), and [tracking](https://github.com/iriss-dev/khora/blob/master/docs/TRACKING.md).

The release's default UF2 is the disabled-output build. Use the source/build guide to produce an output-capable image only after commissioning the physical gate and stop circuits. The attached screen recording shows simulated robot motion, not a physical robot.
