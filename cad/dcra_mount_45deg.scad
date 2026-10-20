// =============================================================================
// KHORA // 45.0-Degree Dihedral Corner Reflector Array (DCRA) Laboratory Mount
// License: MIT
// Author: iriss-dev <contact@iriss.dev>
// =============================================================================

$fn = 60;

// Dimensions (in millimeters)
plate_width = 200.0;
plate_height = 200.0;
plate_thickness = 4.0;
slot_tolerance = 0.5;

base_width = 240.0;
base_depth = 220.0;
base_height = 16.0;

tilt_angle = 45.0; // Precise retro-reflection angle
screw_diameter = 4.2; // M4 clearance

module dcra_mounting_bracket() {
    difference() {
        // Main structural wedge block
        union() {
            // Horizontal base flange
            cube([base_width, base_depth, base_height], center = true);
            
            // Left angled upright pillar
            translate([-base_width/2 + 20, 0, 70])
                rotate([tilt_angle - 90, 0, 0])
                cube([25, 20, 150], center = true);

            // Right angled upright pillar
            translate([base_width/2 - 20, 0, 70])
                rotate([tilt_angle - 90, 0, 0])
                cube([25, 20, 150], center = true);
        }

        // 45-degree precision slot for DCRA optical plate
        translate([0, 0, 80])
            rotate([tilt_angle - 90, 0, 0])
            cube([plate_width + slot_tolerance, plate_thickness + slot_tolerance, plate_height + 20], center = true);

        // Center optical aperture (clears light cone from display beneath)
        translate([0, -20, 0])
            cube([160, 140, base_height * 2 + 1], center = true);

        // M4 bench mounting holes
        for (x = [-base_width/2 + 15, base_width/2 - 15]) {
            for (y = [-base_depth/2 + 15, base_depth/2 - 15]) {
                translate([x, y, 0])
                    cylinder(h = base_height * 3, d = screw_diameter, center = true);
            }
        }

        // Cable routing channel for lower OLED/LCD display
        translate([0, base_depth/2 - 10, -base_height/4])
            cube([60, 30, base_height], center = true);
    }
}

dcra_mounting_bracket();
