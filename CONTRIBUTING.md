# Contributing to KHORA

Start with the [engineering audit](docs/ENGINEERING_AUDIT.md) and the [lab](https://iriss-dev.github.io/khora/platform/lab.html). Open an issue with a reproducible observation, proposed experiment, or focused implementation change.

## Useful contributions

- Measure a single 40 kHz emitter with geometry, calibration method, uncertainty, and raw data.
- Compare the piston approximation with a measured field or a higher-fidelity model.
- Measure DCRA image position, angular acceptance, and optical throughput.
- Implement a board-specific driver behind the phase-staging interface, with an independently measured output-disable path.
- Improve accessibility, rendering performance, or numerical parity in the browser lab.

Distinguish simulation results from physical measurements. Include SI units, coordinate frames, phase conventions, and assumptions. A watchdog test does not establish acoustic safety or certify a hardware system; see [validation status](docs/PHYSICAL_PROOF_AND_VALIDATION.md).

## Development

Serve the repository with `python -m http.server 8765`, then open `http://localhost:8765/platform/`. Run the relevant checks listed in the [README](README.md#validate). Add regression tests for numerical behavior, transport failures, or other meaningful failure cases.

Keep changes focused. Use descriptive names and short comments only where the reason or physical convention would otherwise be unclear. Preserve third-party license notices. Do not add telemetry or external dependencies to the browser without explaining the need.

The current Rust checks use the default `std` feature. Embedded timing, `no_std` support, and hardware operation need their own evidence.

Contributions are licensed under [MIT](LICENSE).
