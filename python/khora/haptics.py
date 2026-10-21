"""
Mid-Air Ultrasound Acoustic Radiation Pressure & Phased Array Beamforming (RFC-0001).
Calculates transducer phase synthesis for contactless tactile sensation at the optical focal point.
"""

import math
from typing import List, Tuple, Dict, Any
from .acoustic_field import pressure_phasor, radiation_pressure, integrate_patch_force


AIR_SPEED_OF_SOUND_20C = 343.0  # m/s
AIR_DENSITY_20C = 1.204          # kg/m^3
DEFAULT_CARRIER_FREQ = 40000.0   # 40 kHz ultrasound
DEFAULT_MODULATION_FREQ = 200.0  # 200 Hz AM for cutaneous Pacinian receptors


def speed_of_sound_at_temp(temp_celsius: float) -> float:
    if not math.isfinite(temp_celsius) or temp_celsius <= -273.15:
        raise ValueError("Temperature must exceed absolute zero")
    return 331.3 * math.sqrt(1.0 + temp_celsius / 273.15)


def acoustic_wavenumber(frequency: float = DEFAULT_CARRIER_FREQ, temp_c: float = 20.0) -> float:
    if not math.isfinite(frequency) or frequency <= 0:
        raise ValueError("Frequency must be finite and positive")
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
    if len(focal_point) != 3 or not all(math.isfinite(x) for x in focal_point):
        raise ValueError("Focal point must contain three finite coordinates")
    k = acoustic_wavenumber(frequency, temp_c)
    phases_rad: List[float] = []
    phases_8bit: List[int] = []

    for t_pos in transducers:
        if len(t_pos) != 3 or not all(math.isfinite(x) for x in t_pos):
            raise ValueError("Transducer positions must contain three finite coordinates")
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
        quant = int(math.floor((phi / (2.0 * math.pi)) * 256.0 + 0.5)) % 256
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
        element_power_pa_at_1m: float = 1.0,
    ):
        if (not isinstance(grid_rows, int) or not isinstance(grid_cols, int)
                or grid_rows < 1 or grid_cols < 1 or not math.isfinite(pitch_mm) or pitch_mm <= 0
                or len(center_m) != 3 or not all(math.isfinite(x) for x in center_m)
                or not math.isfinite(element_power_pa_at_1m) or element_power_pa_at_1m < 0):
            raise ValueError("Invalid array geometry or source pressure")
        self.rows = grid_rows
        self.cols = grid_cols
        self.pitch_m = pitch_mm / 1000.0
        self.center = list(center_m)
        self.p0 = element_power_pa_at_1m  # Illustrative PEAK Pa at 1 m; requires calibration

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
        integrate_force: bool = True,
    ) -> Dict[str, Any]:
        """
        Calculates beamforming phase map and estimates peak acoustic radiation
        pressure and normal force (mN) at the focal zone.

        Set integrate_force=False for tracking updates; the force estimate is
        then None and the expensive patch quadrature is omitted. Outputs remain
        uncalibrated estimates and do not establish perceptual discernibility.
        """
        phases_rad, phases_8bit = compute_beamforming_phases(
            focal_point, self.elements, frequency
        )

        # Evaluate the quantized drive, using the same propagation speed as synthesis.
        c = speed_of_sound_at_temp(20.0)
        decoded = [q * 2 * math.pi / 256 for q in phases_8bit]
        options = dict(frequency=frequency, sound_speed=c, peak_pa_at_1m=self.p0)
        p_peak = abs(pressure_phasor(focal_point, self.elements, decoded, **options))
        p_rms = p_peak / math.sqrt(2.0)
        radiation_pressure_pa = radiation_pressure(p_rms, sound_speed=c)
        wavelength = c / frequency
        normal_force_mn = (integrate_patch_force(focal_point, self.elements, decoded, **options)
                           if integrate_force else None)
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
            "model_status": "uncalibrated_estimate",
            "tactile_discernible": None,  # Requires calibrated output and a psychophysical protocol.
            "force_patch_side_mm": 10.0,
            "reflection_power": 1.0,
            "recommended_am_modulation_hz": DEFAULT_MODULATION_FREQ,
        }


def estimate_radiation_force(rms_pressure_pa: float, radius_mm: float = 4.28,
                             reflection_power: float = 1.0) -> float:
    """Helper to compute normal force in mN from RMS pressure."""
    c = AIR_SPEED_OF_SOUND_20C
    rho0 = AIR_DENSITY_20C
    if not math.isfinite(radius_mm) or radius_mm <= 0:
        raise ValueError("Radius must be finite and positive")
    rad_press = radiation_pressure(rms_pressure_pa, reflection_power=reflection_power,
                                  density=rho0, sound_speed=c)
    area_m2 = math.pi * ((radius_mm / 1000.0) ** 2)
    return rad_press * area_m2 * 1000.0
