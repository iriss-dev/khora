# KHORA v0.3.1-alpha

This release includes the robotics, MCP, RP2040 and community features introduced in v0.3, with an additional isolation fix: arming the **servo-only** group leaves the acoustic PIO state machine disabled and GPIO0–15 low. This avoids driving the phase inputs of an unpowered acoustic stage. The external power gates and commissioning requirements still apply.

**[Robot + AI demo](https://iriss-dev.github.io/khora/platform/robot.html)** · **[Pico controller](https://iriss-dev.github.io/khora/platform/hardware.html)** · **[Public forum](https://github.com/iriss-dev/khora/discussions)**

- Six-joint simulated planning/playback and JSON exchange with nine MCP tools.
- Product-of-exponentials forward kinematics and bounded reference trajectories.
- 16-channel PIO/DMA firmware, explicit output groups and independent heartbeat expiry.
- Feetech STS3215 calibration, packets and telemetry; Ultraleap adapter and optional webcam target selection.

The attached UF2 has physical outputs disabled by default. Hardware output, stopping time, tracking accuracy and acoustic exposure have not been bench-validated on the development host. Follow the [Pico commissioning guide](https://github.com/iriss-dev/khora/blob/master/docs/PICO_HARDWARE.md) before building an output-capable image.

This patch supersedes v0.3.0-alpha for builds intended to use servo-only output. The attached Python wheel, screen recording and launch kit accompany the source release. The recording shows simulation, not a physical robot.
