import unittest
import math
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from khora.haptics import (
    AcousticPhasedArray, compute_beamforming_phases,
    acoustic_wavenumber, estimate_radiation_force
)


class TestHaptics(unittest.TestCase):

    def test_wavenumber_and_wavelength(self):
        k = acoustic_wavenumber(40000.0)
        wavelength_m = (2.0 * math.pi) / k
        # For 40kHz, wavelength in air is ~8.57 mm
        self.assertAlmostEqual(wavelength_m * 1000.0, 8.575, delta=0.2)

    def test_beamforming_phase_synthesis(self):
        focal_pt = [0.0, 0.0, 0.15]  # 15 cm above array
        transducers = [
            [0.0, 0.0, 0.0],
            [0.01, 0.0, 0.0],
            [-0.01, 0.0, 0.0],
        ]
        phases_rad, phases_8bit = compute_beamforming_phases(focal_pt, transducers)
        self.assertEqual(len(phases_rad), 3)
        self.assertEqual(len(phases_8bit), 3)

        for p in phases_rad:
            self.assertGreaterEqual(p, 0.0)
            self.assertLess(p, 2.0 * math.pi)

        for b in phases_8bit:
            self.assertGreaterEqual(b, 0)
            self.assertLessEqual(b, 255)

    def test_array_focus_and_tactile_force(self):
        array = AcousticPhasedArray(grid_rows=16, grid_cols=16, pitch_mm=10.0)
        self.assertEqual(array.total_transducers, 256)

        focal_pt = [0.0, 0.0, 0.12]
        res = array.synthesize_focus(focal_pt)

        self.assertGreater(res["peak_pressure_pa"], 0.0)
        self.assertGreater(res["estimated_normal_force_mn"], 0.1)
        self.assertEqual(len(res["phases_8bit"]), 256)


if __name__ == "__main__":
    unittest.main()
