"""
Mid-Air Ultrasound Acoustic Radiation Pressure & Phased Array Beamforming (RFC-0001).
Calculates transducer phase synthesis for contactless tactile sensation at the optical focal point.
"""

import math
from typing import List, Tuple, Dict, Any


AIR_SPEED_OF_SOUND_20C = 343.0  # m/s
AIR_DENSITY_20C = 1.204          # kg/m^3
DEFAULT_CARRIER_FREQ = 40000.0   # 40 kHz ultrasound
DEFAULT_MODULATION_FREQ = 200.0  # 200 Hz AM for cutaneous Pacinian receptors


def speed_of_sound_at_temp(temp_celsius: float) -> float:
    return 331.3 * math.sqrt(1.0 + temp_celsius / 273.15)


def acoustic_wavenumber(frequency: float = DEFAULT_CARRIER_FREQ, temp_c: float = 20.0) -> float:
    c = speed_of_sound_at_temp(temp_c)
    return (2.0 * math.pi * frequency) / c


def compute_beamforming_phases(
    focal_point: List[float],
    transducers: List[List[float]],
    frequency: float = DEFAULT_CARRIER_FREQ,
    temp_c: float = 20.0,
) -> Tuple[List[float], List[int]]:
    """
    Synthesizes phase delay for each transducer in the array to construct
    constructive spherical interference at focal_point = [x, y, z] (in meters).
    Returns (phases_rad, timer_quantized_8bit).
    """
    k = acoustic_wavenumber(frequency, temp_c)
    phases_rad: List[float] = []
    phases_8bit: List[int] = []

    for t_pos in transducers:
        dx = focal_point[0] - t_pos[0]
        dy = focal_point[1] - t_pos[1]
        dz = focal_point[2] - t_pos[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        # Phase delay: phi = -k * dist (mod 2*pi)
        phi = (-k * dist) % (2.0 * math.pi)
        if phi < 0.0:
            phi += 2.0 * math.pi

        phases_rad.append(phi)
        # Quantize to 8-bit timer register (0 - 255)
        quant = int(round((phi / (2.0 * math.pi)) * 255.0)) % 256
        phases_8bit.append(quant)

    return phases_rad, phases_8bit


class AcousticPhasedArray:
    """
    Planar rectangular transducer grid (e.g. 16x16 40kHz transducers).
    """

    def __init__(
        self,
        grid_rows: int = 16,
        grid_cols: int = 16,
        pitch_mm: float = 10.0,
        center_m: List[float] = [0.0, 0.0, -0.05],
        element_power_pa_at_1m: float = 120.0,
    ):
        self.rows = grid_rows
        self.cols = grid_cols
        self.pitch_m = pitch_mm / 1000.0
        self.center = center_m
        self.p0 = element_power_pa_at_1m  # Transducer acoustic output pressure at 1m

        # Precompute transducer element coordinates
        self.elements: List[List[float]] = []
        x_offset = (grid_cols - 1) * self.pitch_m / 2.0
        y_offset = (grid_rows - 1) * self.pitch_m / 2.0

        for r in range(grid_rows):
            for c in range(grid_cols):
                self.elements.append([
                    self.center[0] + (c * self.pitch_m - x_offset),
                    self.center[1] + (r * self.pitch_m - y_offset),
                    self.center[2],
                ])

    @property
    def total_transducers(self) -> int:
        return self.rows * self.cols

    def synthesize_focus(
        self,
        focal_point: List[float],
        frequency: float = DEFAULT_CARRIER_FREQ,
    ) -> Dict[str, Any]:
        """
        Calculates beamforming phase map and estimates peak acoustic radiation
        pressure and normal force (mN) at the focal zone.
        """
        phases_rad, phases_8bit = compute_beamforming_phases(
            focal_point, self.elements, frequency
        )

        # Calculate complex pressure at the focal point:
        # p_total = sum( (p0 / d_i) * exp(j * (phi_i + k * d_i)) )
        k = acoustic_wavenumber(frequency)
        real_sum = 0.0
        imag_sum = 0.0

        for pos, phi in zip(self.elements, phases_rad):
            dx = focal_point[0] - pos[0]
            dy = focal_point[1] - pos[1]
            dz = focal_point[2] - pos[2]
            d = math.sqrt(dx*dx + dy*dy + dz*dz)
            if d < 1e-4:
                d = 1e-4

            amp = self.p0 / d
            total_phase = phi + k * d
            real_sum += amp * math.cos(total_phase)
            imag_sum += amp * math.sin(total_phase)

        p_peak = math.sqrt(real_sum * real_sum + imag_sum * imag_sum)
        p_rms = p_peak / math.sqrt(2.0)

        # Radiation pressure on reflective human skin: P_rad = 2 * <I> / c = p_rms^2 / (rho0 * c^2)
        c = AIR_SPEED_OF_SOUND_20C
        rho0 = AIR_DENSITY_20C
        radiation_pressure_pa = (p_rms ** 2) / (rho0 * (c ** 2))

        # Effective focal spot area: ~ circle of diameter lambda = c / f
        wavelength = c / frequency
        focal_spot_radius = wavelength / 2.0
        focal_area_m2 = math.pi * (focal_spot_radius ** 2)

        # Force in millinewtons: F = P_rad * Area * 1000
        normal_force_mn = radiation_pressure_pa * focal_area_m2 * 1000.0

        # Safety check (<130 dB SPL equivalent)
        spl_db = 20.0 * math.log10(max(1e-12, p_rms) / 20e-6)

        return {
            "focal_point_m": focal_point,
            "transducer_count": self.total_transducers,
            "phases_8bit": phases_8bit,
            "carrier_frequency_hz": frequency,
            "wavelength_mm": wavelength * 1000.0,
            "peak_pressure_pa": p_peak,
            "rms_pressure_pa": p_rms,
            "spl_db": spl_db,
            "radiation_pressure_pa": radiation_pressure_pa,
            "estimated_normal_force_mn": normal_force_mn,
            "tactile_discernible": normal_force_mn >= 1.5,
            "recommended_am_modulation_hz": DEFAULT_MODULATION_FREQ,
        }


def estimate_radiation_force(rms_pressure_pa: float, radius_mm: float = 4.28) -> float:
    """Helper to compute normal force in mN from RMS pressure."""
    c = AIR_SPEED_OF_SOUND_20C
    rho0 = AIR_DENSITY_20C
    rad_press = (rms_pressure_pa ** 2) / (rho0 * (c ** 2))
    area_m2 = math.pi * ((radius_mm / 1000.0) ** 2)
    return rad_press * area_m2 * 1000.0
