# Physical principles and validation status

KHORA combines models of aerial imaging and mid-air ultrasound haptics. Both
technologies have published and commercial precedents. Their existence does
not establish that a particular KHORA assembly meets its intended optical,
tactile, timing or exposure specifications. This repository currently supplies
analytical models, a local visual inspector and a dry phase-staging transport.
It does not contain a measured end-to-end hardware validation record.

## Aerial imaging

An ideal dihedral corner-reflector array reverses the two components parallel
to its substrate and preserves the normal component. For plate origin `o` and
unit normal `n`, a source `s` is conjugated to

\[
s'=s-2n[n\cdot(s-o)].
\]

This creates a real image of the source across the plate. Equal source/image
distances are normal distances. A rigid tilt changes image pose, not ideal
magnification. A flat source remains a plane image; arbitrary volumetric
content requires additional optical degrees of freedom.

[Asukanet describes its aerial imaging technology](https://www.asukanet.co.jp/contents/product/aerialimaging.html).
A generic corner-cube retroreflective sheet is not interchangeable with a
transmissive DCRA imaging plate. Optical validation should identify the plate,
record source and plate poses, measure image registration and point-spread
functions, and quantify transmission, ghost images and viewing aperture.
Numerical ideal-ray convergence cannot replace these measurements.

## Acoustic haptics

A phased array can interfere constructively near a target. Mid-air haptic
devices are described in [Ultraleap's documentation](https://docs.ultraleap.com/).
The source amplitude, aperture, phase accuracy, distance and skin boundary
conditions determine force. The number of transducers alone does not imply
a 5–15 mN output or a sensation indistinguishable from a mechanical switch.

For the local plane-wave, normal-incidence opaque-boundary approximation:

\[
p_{rms}=|\tilde p|/\sqrt{2},\qquad
P_{rad}=(1+R)p_{rms}^2/(\rho c^2),\qquad F=\int_S P_{rad}\,dS.
\]

R is the reflected power fraction. Pressure has units Pa; force has units N.
The implementation uses a circular-piston directivity model with spherical
paths, plus a numerical Rayleigh integral for reference checks. See
[the field audit](ENGINEERING_AUDIT.md) for equations, assumptions and tests.

A stable levitation trap is not established merely by aiming two or four
uncharacterized emitters at a point. Particle trapping and skin stimulation
have different boundary conditions and validation criteria. No inexpensive
DIY levitation demonstration is offered as proof of KHORA's tactile output.

## Required experimental record

1. Identify array hardware, drive voltage, carrier, element geometry and each
   element's measured complex acoustic response with a suitable calibrated sensor.
2. Scan pressure around the target, including sidelobes and off-target exposure.
   Record temperature, coordinates, calibration uncertainty and modulation waveform.
3. Measure force independently on a specified surface with a characterized force
   sensor. Compare to a surface integral and publish residuals at held-out points.
4. Register sensor, optical and array coordinate systems using independent
   landmarks. Report error throughout the interaction volume, not just at its centre.
5. Measure source-frame-to-output timing and verified physical shutdown under
   injected faults. A 50 ms software setting is not a certification.

The current browser shows model provenance and transaction timing separately.
No human-subject result, regulatory conformity or end-to-end latency bound is
inferred from unit tests or rendered images.
