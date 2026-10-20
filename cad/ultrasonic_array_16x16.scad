// =============================================================================
// KHORA // 16x16 Phased Array Transducer Alignment Grid (40 kHz Airborne Ultrasound)
// License: MIT
// Author: iriss-dev <contact@iriss.dev>
// =============================================================================

$fn = 32;

// Standard Murata MA40S4S / 10mm Piezo Dimensions
transducer_diameter = 9.8;
transducer_hole = 10.2; // 0.4mm tolerance for push-fit
transducer_pitch = 10.0; // Distance center-to-center
grid_dim = 16;           // 16x16 = 256 transducers

plate_thickness = 4.0;
border_margin = 12.0;

total_width = (grid_dim - 1) * transducer_pitch + transducer_hole + border_margin * 2;
total_height = total_width;

module ultrasonic_array_grid() {
    difference() {
        // Outer housing plate
        cube([total_width, total_height, plate_thickness], center = true);

        // 256 Transducer through-holes
        offset = (grid_dim - 1) * transducer_pitch / 2;
        for (r = [0 : grid_dim - 1]) {
            for (c = [0 : grid_dim - 1]) {
                translate([c * transducer_pitch - offset, r * transducer_pitch - offset, 0])
                    cylinder(h = plate_thickness * 2, d = transducer_hole, center = true);
            }
        }

        // Corner M3 mounting holes
        for (x = [-total_width/2 + 5, total_width/2 - 5]) {
            for (y = [-total_height/2 + 5, total_height/2 - 5]) {
                translate([x, y, 0])
                    cylinder(h = plate_thickness * 2, d = 3.2, center = true);
            }
        }
    }
}

ultrasonic_array_grid();
