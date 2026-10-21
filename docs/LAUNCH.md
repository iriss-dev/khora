# KHORA v0.2.0-alpha launch kit

Demo: https://iriss-dev.github.io/khora/platform/?lang=en

Lab: https://iriss-dev.github.io/khora/platform/lab.html

Source: https://github.com/iriss-dev/khora

## Positioning

KHORA is an open laboratory for aerial imaging and mid-air haptics. This release makes a 256-element acoustic model explorable in the browser and provides reference calculations and a phase-staging transport. It is an alpha simulation and engineering toolkit. Do not describe the illustrative assembly as a working prototype or the uncalibrated field as measured tactile performance.

## English announcement

KHORA v0.2.0-alpha is an open-source lab for exploring aerial imaging and mid-air haptics.

Move the focus of a 16 × 16 ultrasonic array in your browser, inspect interference in three planes, compare aperture weighting, and download the phase map. Configurations can be shared by URL. No signup or installation is needed for the demo.

The repo includes Python reference calculations, a numerical Rayleigh comparison, an ideal DCRA optical model, and a C/Web Serial phase-staging protocol. The browser field is computed from complex pressure superposition, including piston directivity and 8-bit phase quantization.

This is uncalibrated simulation, not a demonstrated hardware system. The next useful step is single-emitter calibration data: amplitude, directivity, phase delay, and measurement uncertainty. Contributions or critiques of the model are welcome.

Try it: https://iriss-dev.github.io/khora/platform/?lang=en

## Anuncio en español

KHORA v0.2.0-alpha: un laboratorio abierto para explorar imágenes aéreas y háptica en el aire.

Puedes mover el foco de una matriz ultrasónica de 16 × 16 emisores, observar la interferencia en tres planos, comparar la ponderación de la apertura y descargar el mapa de fases. Las configuraciones se comparten con un enlace. La demo funciona en el navegador sin registro.

El repositorio incluye modelos de referencia en Python, una comparación numérica de Rayleigh, un modelo óptico DCRA ideal y un protocolo C/Web Serial para preparar fases con las salidas deshabilitadas.

Es una simulación sin calibrar. El siguiente paso necesita mediciones de un emisor: amplitud, directividad, retardo de fase e incertidumbre. Buscamos experimentos reproducibles y revisiones del modelo.

Demo: https://iriss-dev.github.io/khora/

## Hacker News draft

Title: Show HN: KHORA – Explore a 256-element ultrasonic field in your browser

Link: https://iriss-dev.github.io/khora/platform/?lang=en

Opening comment:

KHORA is an open-source spatial-computing research toolkit. This release focuses on a usable acoustic field inspector: move the focus, switch cross-sections, adjust aperture weighting, and export the phase bytes. The same model has Python reference tests and three GPU/CPU readback checks.

The amplitude is illustrative, so the pressure/force display is not a hardware measurement. The optical assembly is also a visualization. I would especially value feedback on the piston approximation near the array and on a minimal, reproducible calibration experiment. Code and assumptions: https://github.com/iriss-dev/khora

## Embedded and acoustics community draft

Title: An open 40 kHz array simulator seeking single-emitter calibration data

KHORA now has a browser field inspector for a modeled 16 × 16 array and an inspectable Python reference. It includes piston directivity, 8-bit phase quantization, and patch-integrated radiation force. A separate KH v1 serial receiver stages phase bytes with outputs disabled; it is not a board driver.

The most useful missing input is a measured single-emitter response. If you have calibrated amplitude/directivity data, what geometry and uncertainty budget would you use to compare it with a baffled-piston model? A reproducible experiment or critique is more useful than a performance claim.

Demo: https://iriss-dev.github.io/khora/platform/?lang=en

Methods: https://github.com/iriss-dev/khora/blob/master/docs/ENGINEERING_AUDIT.md

## Assets and posting status

- `assets/press/khora-social.png`: 1200 × 630 preview image.
- `assets/press/khora-rig.png`: illustrative assembly captured from the local renderer.
- `assets/press/khora-lab.png`: screenshot of the running field inspector.
- `assets/press/khora-launch-kit.zip`: copy, images, logo, and MIT license.

Community messages above are drafts. No Hacker News, Reddit, Discord, or other external community post is implied by this file. Choose a relevant community, check its current submission rules, and post from the project owner's account with the project relationship stated. Do not cross-post identical messages in bulk or ask for votes.
