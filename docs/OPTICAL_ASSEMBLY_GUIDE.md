# KHORA: Optical Assembly & Laboratory Alignment Guide

This guide details the physical assembly and precision alignment of the **KHORA Desktop Traversable Optical-Haptic Rig**.

---

## 1. Geometric Ray Layout ($45^\circ$ Configuration)

To project light into open air while keeping hardware components recessed out of the user's hand trajectory, the DCRA plate is positioned at an exact angle $\theta_{tilt} = 45.0^\circ$ relative to the horizontal base.

```
                  Z (Up)
                  │
                  │              Focal Plane (Floating Image in Open Air)
                  │              ═══════════════════════════════════════
                  │               [ (x_f, y_f, +z_air) ]
                  │                     ^
                  │                    /
                  │                   /  Reflected Retro-Beam
                  │                  /
                  │          ┌──────/──────┐
                  │          │     /       │  DCRA Substrate Plate (θ = 45°)
                  │          └────/────────┘
                  │              /
                  │             /  Incident Light Cone
                  │            /
                  │           v
  ────────────────┴─────────────────────── Y (Forward)
  [ Display Substrate: (x_s, y_s, -z_s) ]
  [ Ultrasonic Transducer Phased Array   ]
```

### Key Dimensional Tolerances
1. **Source Distance = Aerial Image Distance**:
   $$d_{air} = d_{source}$$
   If the display is placed $100\,\text{mm}$ beneath the center of the DCRA plate, the aerial image will float exactly $100\,\text{mm}$ directly above the plate in free space.
2. **Angular Alignment Tolerance**:
   Plate tilt error must remain below $\Delta \theta \le \pm 0.2^\circ$. Angular deviation manifests as a sheared coordinate focal distortion $\Delta y = 2 d \cdot \Delta \theta$.

---

## 2. Step-by-Step Assembly Procedure

### Step 1: Chassis Base & Display Mounting
1. Secure the LCD/OLED panel horizontally to the floor of the 3D-printed chassis.
2. Line the entire interior chamber with non-reflective matte black velvet or high-absorbance paint (Musou Black) to prevent internal secondary bounces.
3. Verify that the display active area is centered on the optical datum $(X = 0, Y = -100\,\text{mm})$.

### Step 2: DCRA Substrate Installation
1. Inspect the DCRA plate for surface contamination. Clean strictly with optical-grade isopropyl alcohol (IPA 99.7%) and lint-free microfiber swabs.
2. Slot the DCRA plate into the $45^\circ$ guide rails.
3. Note the plate orientation mark: Dihedral mirror micro-channels must run **perpendicular** to the retro-reflection axis (indicated by arrow on ASKA3D / DCRA frames).

### Step 3: Ultrasonic Phased Array Integration
1. Mount the 40 kHz transducer PCB directly beneath the focal aperture or behind an acoustically transparent, optically reflective cold mirror if co-axial propagation is used.
2. For the standard offset geometry, position the array at $(0, 0, -50\,\text{mm})$ angled toward the focal zone.
3. Wire transducer columns and rows to the TC4427 driver board and RP2040 GPIO pins.

### Step 4: Stereo IR Tracking Calibration
1. Fasten the Ultraleap Stereo IR sensor to the forward chassis bracket facing the open-air working volume.
2. Run the spatial calibration script:
   ```bash
   python -m khora.mcp_server
   ```
3. Use a physical calibration wand with a retro-reflective spherical tip ($5\,\text{mm}$) placed at the optical focal plane. Verify that sensor readings match simulated coordinates within $\pm 0.5\,\text{mm}$.

---

## 3. Optical Field-of-View (FOV) Optimization

The effective viewing cone of a DCRA plate is bounded by the aspect ratio of its dihedral micro-channels:

$$\text{FOV}_{horizontal} \approx \pm 35^\circ \sim \pm 40^\circ$$
$$\text{FOV}_{vertical} \approx \pm 20^\circ \sim \pm 25^\circ$$

To maximize visibility:
* Position the operator's eye level at approximately $30^\circ - 45^\circ$ relative to the plate normal.
* Maintain room ambient illuminance under $300\,\text{lux}$ (standard office lighting is acceptable, direct sunlight degrades contrast).
