# KHORA: Open Hardware CAD Fixtures

Parametric algorithmic 3D models for physical laboratory assembly.

---

## 1. File Manifest

| File | Purpose | Material / Print Specs |
| :--- | :--- | :--- |
| **`dcra_mount_45deg.scad`** | $45.0^\circ$ optical fixture holding the $200 \times 200\,\text{mm}$ DCRA plate over the recessed OLED/LCD display. | PETG / PLA+, $0.2\,\text{mm}$ layer height, $30\%$ gyroid infill, 4 perimeters. |
| **`ultrasonic_array_16x16.scad`** | Precision alignment grid for 256 piezo transducers ($10.0\,\text{mm}$ pitch). | PETG / ABS, $0.2\,\text{mm}$ layer height, $100\%$ infill for acoustic rigidity. |
| **`sensor_mount_leap.scad`** | $35^\circ$ forward bracket for Leap Motion / Stereo IR 170 tracking camera. | PLA+, $0.2\,\text{mm}$ layer height, $20\%$ infill. |

---

## 2. Compiling to STL via CLI

Using OpenSCAD (available on Linux, macOS, and Windows):

```bash
# Generate STL for 45-degree DCRA mount
openscad -o dcra_mount_45deg.stl dcra_mount_45deg.scad

# Generate STL for 16x16 ultrasonic array grid
openscad -o ultrasonic_array_16x16.stl ultrasonic_array_16x16.scad

# Generate STL for sensor bracket
openscad -o sensor_mount_leap.stl sensor_mount_leap.scad
```

---

## 3. Tolerances & Machining Notes

- **Optical Slot**: Formatted with $+0.5\,\text{mm}$ clearance tolerance to allow insertion of glass/acrylic DCRA plates without mechanical stress or birefringence.
- **Transducer Push-Fit**: Formatted with $+0.4\,\text{mm}$ diametric tolerance for snug friction fit of Murata MA40S4S transducers prior to backplate soldering.
