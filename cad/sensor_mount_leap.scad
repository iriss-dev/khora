// =============================================================================
// KHORA // Leap Motion Controller 2 / Stereo IR Sensor Forward Bracket
// License: MIT
// Author: iriss-dev <contact@iriss.dev>
// =============================================================================

$fn = 32;

sensor_width = 84.0;
sensor_depth = 24.0;
sensor_height = 12.0;

bracket_angle = 35.0; // Angled forward facing floating optical plane

module sensor_bracket() {
    difference() {
        // Base wedge
        cube([sensor_width + 16, 50, 30], center = true);

        // Angled recess for sensor
        translate([0, 5, 5])
            rotate([bracket_angle, 0, 0])
            cube([sensor_width + 1.0, sensor_depth + 1.0, 40], center = true);

        // USB-C cable exit port
        translate([sensor_width/2 - 5, 0, 0])
            cube([20, 12, 15], center = true);

        // M3 mount slots
        translate([-sensor_width/2 - 2, -15, 0])
            cylinder(h = 60, d = 3.2, center = true);
        translate([sensor_width/2 + 2, -15, 0])
            cylinder(h = 60, d = 3.2, center = true);
    }
}

sensor_bracket();
