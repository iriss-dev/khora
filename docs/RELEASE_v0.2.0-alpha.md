# KHORA v0.2.0-alpha

A usable browser lab for exploring a 256-element ultrasonic field, with reference calculations and explicit validation limits.

**[Try the website](https://iriss-dev.github.io/khora/)** · **[Open the field inspector](https://iriss-dev.github.io/khora/platform/lab.html)**

## Explore

- New Spanish/English website with an interactive assembly study.
- Three acoustic cross-sections, movable focus, aperture weighting, and patch-force estimates.
- Shareable configuration URLs and JSON export of all 256 phase/amplitude channels.
- Local assets, mobile layouts, and a fallback when WebGL is unavailable.

## Inspect and reproduce

- Complex pressure superposition, piston directivity, and numerical Rayleigh reference in Python.
- Consistent 256-step phase quantization across Python, JavaScript, and Rust.
- KH v1 Web Serial frames with CRC, handshake, acknowledgements, and dry phase staging.
- C receiver/watchdog regression tests and automated validation for Python, JavaScript, C, Rust, and the browser.
- Revised engineering audit and hardware documentation.

The field is uncalibrated. The assembly is illustrative. No working hardware prototype, tactile threshold, end-to-end tracking latency, or acoustic compliance is established by this release. The serial receiver stages data with outputs disabled and has no ARM command.

## Help with the next experiment

We are looking for reproducible single-emitter calibration: amplitude, directivity, phase delay, measurement geometry, and uncertainty. [Propose an experiment](https://github.com/iriss-dev/khora/issues/new/choose) or review the [engineering audit](https://github.com/iriss-dev/khora/blob/master/docs/ENGINEERING_AUDIT.md).

The attached launch kit includes English/Spanish copy, actual browser captures, a social preview, the logo, and the MIT license.
