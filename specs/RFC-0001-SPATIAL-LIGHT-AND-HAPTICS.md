# RFC-0001: Traversable Optical Field and Ultrasonic Radiation Pressure Architecture

- **Status**: Standard / Approved
- **Author**: iriss-dev <contact@iriss.dev>
- **Date**: 2026-10-20
- **Scope**: Optical imaging in free space, Dihedral Corner Reflector Arrays (DCRA), and mid-air tactile acoustic radiation pressure.

---

## 1. Abstract

Conventional spatial computing relies either on head-mounted displays (HMDs) that isolate the operator from their physical workspace, or projection surfaces (fog, water vapor, aerogel) that disperse light inefficiently and impede natural tactile interaction. 

`KHORA` specifies an open-source hardware and software pipeline for **traversable spatial light**: generating floating real images in open air that can be physically penetrated by a human hand without physical resistance, accompanied by acoustic radiation pressure (ultrasonic beamforming) to produce deterministic tactile tactile feedback at the focal plane without gloves or wearables.

```
       Physical Display (LCD/OLED)
                   │
                   ▼ (divergent light rays)
         ┌──────────────────┐
         │  DCRA Substrate  │  (Micro-mirror dihedral array, θ = 45°)
         └──────────────────┘
                   │
                   ▼ (convergent retro-reflection)
         ════════════════════  Air Focal Plane (Floating Image at z_air = z_source)
               \      /
                \    /         <--- Operator's hand enters free air
                 \  /
         ┌──────────────────┐
         │ 40kHz Transducer │  (Acoustic Phased Array: 5-15 mN focal point)
         │      Array       │
         └──────────────────┘
```

---

## 2. Optical Subsystem: Dihedral Corner Reflector Array (DCRA)

### 2.1 Geometric Ray Convergence
The optical subsystem utilizes an Aerial Imaging Plate (AIP) structured as a microscopic orthogonal corner reflector array. Each micro-element consists of two orthogonal reflective mirror walls perpendicular to the substrate plane ($xy$).

For an incident ray $\vec{v}_i = [v_x, v_y, v_z]^T$:
1. The ray undergoes internal reflection on the first vertical plane (e.g., $xz$), transforming $v_y \to -v_y$.
2. The ray reflects on the second orthogonal plane (e.g., $yz$), transforming $v_x \to -v_x$.
3. The normal component $v_z$ remains continuous: $v_z \to v_z$.

Resulting reflected vector:
$$\vec{v}_r = [-v_x, -v_y, v_z]^T$$

Because reflection is retro-reflective strictly in the substrate plane while transmissive along the normal axis, all divergent rays emitted from an object at coordinate $(x_0, y_0, -z_0)$ converge symmetrically at $(x_0, y_0, +z_0)$ in open air.

### 2.2 Clearance & Traversability
- The aerial focal distance equals the source distance: $d_{air} = d_{source}$.
- When configured at an angle $\alpha = 45^\circ$, the display source is recessed beneath an opaque enclosure, leaving an open air working volume of $150 \times 150 \times 100\,\text{mm}$ completely unobstructed.
- Hand velocity through the focal plane is unrestricted ($\Delta v = \infty$, zero mechanical resistance).

---

## 3. Mid-Air Acoustic Haptic Engine

### 3.1 Acoustic Radiation Pressure
To provide tactile confirmation when interacting with floating visual elements, an acoustic phased array operates synchronously beneath or behind the optical path.

The time-averaged acoustic radiation pressure $P_{rad}$ exerted on human skin (modelled as an acoustic reflector with reflection coefficient $R \approx 1$) is given by:

$$P_{rad} = \frac{2 \langle I \rangle}{c} = \frac{p_{rms}^2}{\rho_0 c^2}$$

Where:
- $I$: Acoustic intensity ($\text{W/m}^2$)
- $c$: Speed of sound in ambient air ($343\,\text{m/s}$ at $20^\circ\text{C}$)
- $\rho_0$: Air density ($1.204\,\text{kg/m}^3$)
- $p_{rms}$: Root-mean-square acoustic pressure ($\text{Pa}$)

A focused acoustic spot of diameter $\approx \lambda_{sound} = 8.5\,\text{mm}$ generates an integrated normal force of $5 \sim 15\,\text{mN}$, sufficient to stimulate the fast-adapting mechanoreceptors (Meissner corpuscles, Pacini corpuscles) in human glabrous skin.

### 3.2 Phased Array Beamforming Algorithm
Given an array of $M$ ultrasonic transducers at spatial coordinates $\vec{r}_m = [x_m, y_m, z_m]^T$ and a target tactile focal coordinate $\vec{r}_f = [x_f, y_f, z_f]^T$:

The required phase offset $\phi_m$ for the $m$-th emitter is:

$$\phi_m = -k \|\vec{r}_f - \vec{r}_m\| \pmod{2\pi}$$

Where $k = \frac{2\pi f}{c}$ is the acoustic wavenumber ($f = 40\,\text{kHz} \implies k \approx 732.7\,\text{rad/m}$).

To elicit tactile sensation, the continuous 40 kHz carrier must be amplitude-modulated (AM) at human cutaneous perception frequencies ($150\,\text{Hz} \sim 250\,\text{Hz}$):

$$s_m(t) = \frac{1}{2}\left[1 + \sin(2\pi f_{mod} t)\right] \cdot \sin(2\pi f_0 t + \phi_m)$$

---

## 4. Spatio-Temporal Synchronization Loop

```
[ Stereo IR Sensor ]  ──(Sub-5ms ToF)──>  [ Spatial Filter & Kalman ]
                                                    │
                                                    ▼ (3D Fingertip Coordinates)
┌───────────────────────────────────────────────────┴─────────────────────────────────────────┐
│ KHORA Collision Engine                                                                      │
│ ├── Ray Intersection with Floating Virtual Mesh (z = z_air)                                 │
│ └── Target Force Vector: F(x, y, z) = k_spring * depth * normal_vector                      │
└───────────────────────────────────────────────────┬─────────────────────────────────────────┘
                                                    │
                   ┌────────────────────────────────┴───────────────────┐
                   ▼                                                    ▼
       [ Visual Renderer (60-120fps) ]                      [ Phase Synthesis (1kHz) ]
       Depresses virtual button                             Updates PWM phase registers
```

1. **Latency Threshold**: Total loop latency from hand motion to acoustic pressure must remain below $15\,\text{ms}$ to ensure zero perceptual decoupling.
2. **Safety Cutoff**: Acoustic energy density at the focal point must not exceed $120\,\text{dB SPL}$ continuous to prevent thermal accumulation on tissue.
