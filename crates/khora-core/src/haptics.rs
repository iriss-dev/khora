//! 40 kHz Ultrasonic Phased Array Delay-and-Sum Beamformer (RFC-0001).

use crate::kinematics::Vector3;

pub const SPEED_OF_SOUND_AIR_20C: f32 = 343.0; // m/s
pub const AIR_DENSITY_20C: f32 = 1.204;         // kg/m^3
pub const DEFAULT_FREQ_HZ: f32 = 40000.0;       // 40 kHz

pub fn acoustic_wavenumber(freq_hz: f32) -> f32 {
    (2.0 * core::f32::consts::PI * freq_hz) / SPEED_OF_SOUND_AIR_20C
}

/// Computes the 8-bit quantized PWM timer phase offset [0, 255] for a transducer.
pub fn compute_phase_8bit(focal_pt: &Vector3, transducer_pt: &Vector3, freq_hz: f32) -> u8 {
    let k = acoustic_wavenumber(freq_hz);
    let dx = focal_pt.x - transducer_pt.x;
    let dy = focal_pt.y - transducer_pt.y;
    let dz = focal_pt.z - transducer_pt.z;
    let dist = (dx*dx + dy*dy + dz*dz).sqrt();

    let two_pi = 2.0 * core::f32::consts::PI;
    let mut phi = (-k * dist) % two_pi;
    if phi < 0.0 {
        phi += two_pi;
    }

    let quant = ((phi / two_pi) * 255.0).round() as u32;
    (quant % 256) as u8
}

#[derive(Debug, Clone)]
pub struct AcousticPhasedArray {
    pub rows: usize,
    pub cols: usize,
    pub pitch_m: f32,
    pub center: Vector3,
}

impl AcousticPhasedArray {
    pub fn new(rows: usize, cols: usize, pitch_mm: f32, center: Vector3) -> Self {
        Self {
            rows,
            cols,
            pitch_m: pitch_mm / 1000.0,
            center,
        }
    }

    pub fn get_transducer_coord(&self, row: usize, col: usize) -> Vector3 {
        let x_offset = (self.cols as f32 - 1.0) * self.pitch_m / 2.0;
        let y_offset = (self.rows as f32 - 1.0) * self.pitch_m / 2.0;

        Vector3::new(
            self.center.x + (col as f32 * self.pitch_m - x_offset),
            self.center.y + (row as f32 * self.pitch_m - y_offset),
            self.center.z,
        )
    }
}
