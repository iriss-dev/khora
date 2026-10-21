# KHORA: Hardware Bill of Materials (BOM)

The active 16-emitter RP2040 / STS3215 profile and required external power
gates are specified in [the v0.3 Pico guide](PICO_HARDWARE.md). The larger array
below is an earlier design study, not the profile assumed by that firmware.

- **Target System**: Desktop Traversable Optical-Haptic Rig (v1.0)
- **Clearance Working Volume**: $150 \times 150 \times 120\,\text{mm}$ (Unobstructed Free Air)
- **Acoustic Radiation Force**: $5 \sim 15\,\text{mN}$ (Skin-perceptible touch sensation)

---

## 1. Optical Imaging Subsystem

| Item | Component | Specification | Quantity | Estimated Cost | Source / Notes |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **OPT-01** | **DCRA Aerial Imaging Plate** | $200 \times 200\,\text{mm}$ Dihedral Corner Reflector Array (ASKA3D or compatible plastic DCRA) | 1 | $180 - $350 | Retro-reflects orthogonal ray vectors $1:1$ into free space. |
| **OPT-02** | **High-Brightness Display** | 5.5" ~ 7.0" LCD / AMOLED, $\ge 1920 \times 1080$, $\ge 800\,\text{cd/m}^2$ (nits), MIPI/HDMI interface | 1 | $45 - $80 | Waveshare 5.5" AMOLED or Raspberry Pi DSI high-nit panel. |
| **OPT-03** | **Anti-Reflective Optical Shroud** | Matte black acrylic ($3\,\text{mm}$) / Musou Black light-absorbing velvet | 1 set | $15 - $25 | Eliminates secondary phantom reflections behind the plate. |

---

## 2. Mid-Air Acoustic Haptic Subsystem

| Item | Component | Specification | Quantity | Estimated Cost | Source / Notes |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **HAP-01** | **40 kHz Ultrasonic Transducers** | MA40S4S (Murata) or generic $10\,\text{mm}$ piezoelectric emitters ($40 \pm 1\,\text{kHz}$, $120\,\text{dB}$ SPL) | 64 - 256 | $35 - $110 | Arranged in $8 \times 8$ or $16 \times 16$ Cartesian grid ($10\,\text{mm}$ pitch). |
| **HAP-02** | **MOSFET Gate Drivers** | TC4427A / MIC4427 Dual High-Speed MOSFET Drivers (SOIC-8 or DIP-8) | 32 - 128 | $20 - $60 | Steps up $3.3\,\text{V}$ MCU logic to $12\,\text{V} - 24\,\text{V}$ transducer excitation. |
| **HAP-03** | **High-Voltage Boost Rail** | DC-DC Step-Up Converter ($5\,\text{V} \to 12\,\text{V} - 24\,\text{V}$, $3\,\text{A}$) | 1 | $8 - $15 | XL6009 or TPS61088 boost module. |

---

## 3. Real-Time Hardware & Spatial Tracking

| Item | Component | Specification | Quantity | Estimated Cost | Source / Notes |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **MCU-01** | **Core Microcontroller** | Raspberry Pi Pico (RP2040 Dual ARM Cortex-M0+ @ 125MHz) or STM32F401 | 1 | $5 - $12 | Candidate coordinator for an external phase driver fabric; target-specific firmware is not implemented. |
| **TRK-01** | **Spatial Tracking Sensor** | Ultraleap Stereo IR 170 / Leap Motion Controller 2 (tracking latency must be measured) | 1 | $90 - $140 | Direct 3D fingertip coordinate ingestion. |
| **PWR-01** | **Bench Power Supply** | $12\,\text{V} / 5\,\text{A}$ regulated switching DC supply | 1 | $15 - $25 | Standard barrel jack or XT60 connector. |

---

## 4. Mechanical Fixtures & Enclosure

| Item | Component | Specification | Quantity | Estimated Cost | Source / Notes |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **MEC-01** | **$45^\circ$ Optical Chassis** | 3D Printed PETG / Extruded Aluminum 2020 Profile Frame | 1 | $20 - $35 | Holds DCRA plate tilted at $45.0^\circ \pm 0.2^\circ$. |
| **MEC-02** | **Acoustic Dampening Baffle** | Open-cell polyurethane acoustic foam ($15\,\text{mm}$) | 1 | $8 | Absorbs rear acoustic echoes. |

---

## 5. Total Prototype Budget Summary

* **Minimal Viable Rig ($8 \times 8$ Haptics, 5.5" Display)**: $\approx \$380 - \$490$ USD
* **Laboratory Reference Rig ($16 \times 16$ Haptics, 7.0" AMOLED, Ultraleap 2)**: $\approx \$650 - \$820$ USD
