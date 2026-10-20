//! Optical simulation for Dihedral Corner Reflector Arrays (DCRA / AIP).
//! In local coordinate space, retro-reflection inverts in-plane vectors (x -> -x, y -> -y)
//! while preserving normal propagation (z -> z), producing a 1:1 real image in free space.

use crate::kinematics::{Vector3, SE3Transform};

#[derive(Debug, Clone, Copy)]
pub struct OpticalRay {
    pub origin: Vector3,
    pub direction: Vector3,
    pub intensity: f32,
}

#[derive(Debug, Clone)]
pub struct DCRASubstrate {
    pub center: Vector3,
    pub tilt_rad: f32,
    pub width_m: f32,
    pub height_m: f32,
    pub reflectivity: f32,
    pub t_world_plate: SE3Transform,
    pub t_plate_world: SE3Transform,
}

impl DCRASubstrate {
    pub fn new(center: Vector3, tilt_deg: f32, width_mm: f32, height_mm: f32) -> Self {
        let tilt_rad = tilt_deg * (core::f32::consts::PI / 180.0);
        let c = tilt_rad.cos();
        let s = tilt_rad.sin();

        // Rotation around X axis
        let rot_x = SE3Transform {
            m: [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, c,   -s,  0.0],
                [0.0, s,   c,   0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
        };
        let trans = SE3Transform::from_translation(center.x, center.y, center.z);
        let t_world_plate = trans.multiply(&rot_x);
        let t_plate_world = t_world_plate.inverse();

        Self {
            center,
            tilt_rad,
            width_m: width_mm / 1000.0,
            height_m: height_mm / 1000.0,
            reflectivity: 0.88,
            t_world_plate,
            t_plate_world,
        }
    }

    /// Traces an optical ray and returns reflected ray if it strikes the DCRA aperture.
    pub fn trace_ray(&self, ray: &OpticalRay) -> Option<OpticalRay> {
        let local_origin = self.t_plate_world.transform_point(&ray.origin);
        let local_dir = self.t_plate_world.transform_vector(&ray.direction);

        if local_dir.z.abs() < 1e-9 {
            return None; // Parallel to plate plane
        }

        let t = -local_origin.z / local_dir.z;
        if t <= 1e-6 {
            return None; // Points away from plate
        }

        let hit_x = local_origin.x + local_dir.x * t;
        let hit_y = local_origin.y + local_dir.y * t;

        if hit_x.abs() > (self.width_m / 2.0) || hit_y.abs() > (self.height_m / 2.0) {
            return None; // Missed aperture boundaries
        }

        // DCRA Orthogonal Retro-reflection: x -> -x, y -> -y, z -> z
        let refl_local_dir = Vector3::new(-local_dir.x, -local_dir.y, local_dir.z);

        let hit_world = self.t_world_plate.transform_point(&Vector3::new(hit_x, hit_y, 0.0));
        let refl_world_dir = self.t_world_plate.transform_vector(&refl_local_dir);

        Some(OpticalRay {
            origin: hit_world,
            direction: refl_world_dir,
            intensity: ray.intensity * self.reflectivity,
        })
    }
}
