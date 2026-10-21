# KHORA v0.3.0-alpha launch material

## Public destinations

- Website: https://iriss-dev.github.io/khora/
- Robotics + MCP demo: https://iriss-dev.github.io/khora/platform/robot.html
- Pico controller: https://iriss-dev.github.io/khora/platform/hardware.html
- Forum guide: https://iriss-dev.github.io/khora/platform/community.html
- Actual forum: https://github.com/iriss-dev/khora/discussions
- External technical introduction: https://github.com/ultraleap/leapc-python-bindings/discussions/17

The Ultraleap introduction was posted by iriss-dev in its **Show and tell** category. It describes the unvalidated physical tracking boundary and asks about tested binding/runtime combinations. No physical tracking performance is claimed.

## English copy

KHORA v0.3 adds a six-joint robot planning demo, an installable MCP server and a 16-channel RP2040 PIO/DMA target to its optics/acoustics workbench.

Try a target in the browser, inspect the simulated path and export it as JSON. An MCP client can produce a plan for the same reference arm and replay it in the viewer. The Pico panel distinguishes the 16-emitter hardware profile from the existing 256-element acoustic model.

The release includes Feetech STS3215 packets and telemetry, explicit joint calibration, independent host/MCU leases and a commissioning guide. The default UF2 has outputs disabled. CI covers numerical behavior, protocol interoperability, browser flows and Pico cross-compilation; real output and stopping time still need bench measurements.

Demo: https://iriss-dev.github.io/khora/platform/robot.html

Source: https://github.com/iriss-dev/khora

## Texto en español

KHORA v0.3 incorpora una demo de planificación para un brazo de seis articulaciones, un servidor MCP instalable y firmware PIO/DMA para 16 canales en RP2040.

Puedes elegir un objetivo en el navegador, revisar la trayectoria simulada y exportarla a JSON. Un cliente MCP también puede generar un plan para ese brazo de referencia y reproducirlo en el visor. El panel Pico distingue la matriz física de 16 emisores del modelo acústico de 256.

La entrega incluye paquetes y telemetría Feetech STS3215, calibración explícita por articulación, supervisión independiente en PC/Pico y guía de puesta en marcha. El UF2 por defecto tiene las salidas deshabilitadas. La compilación y las pruebas de software no sustituyen las mediciones eléctricas del montaje.

Demo: https://iriss-dev.github.io/khora/platform/robot.html

Foro público: https://github.com/iriss-dev/khora/discussions

## Assets

- `assets/press/khora-robot.gif`: screen recording of the actual browser simulation, not a physical robot.
- `assets/press/khora-robot.png`: running robot demo.
- `assets/press/khora-pico.png`: 16-channel protocol simulator.
- `assets/press/khora-community.png`: forum entry page.
- `assets/press/khora-social.png`: social preview.
- `assets/press/khora-launch-kit.zip`: copy, captures, logo and license.

## Community posting

The copy above can be adapted only where the destination's rules permit it. Use a relevant technical question or reproducible result rather than repeating a generic advertisement. Do not request stars, votes or coordinated engagement.

Hacker News explicitly asks for human-written text and no automated posting. Its submission was not published by this assistant. The project owner must write and submit their own post there; the generated copy in this file is not intended for HN.

Publication is not evidence of audience growth. Stars, forks, replies and useful contributions should be recorded as actual outcomes rather than inferred from the number of posts.
