import unittest
import math
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from khora.optics import DCRASubstrate, Ray, simulate_dcra_convergence


class TestOptics(unittest.TestCase):

    def test_dcra_single_ray_reflection(self):
        # Plate placed at origin, tilted 45 deg around X axis
        substrate = DCRASubstrate(center=[0.0, 0.0, 0.0], tilt_angle_deg=45.0, width_mm=300.0, height_mm=300.0)
        
        # Ray emitted horizontally from display at y = -0.1m towards tilted plate
        ray = Ray(origin=[0.0, -0.1, 0.0], direction=[0.0, 0.1, 0.0])
        res = substrate.trace_ray(ray)
        self.assertIsNotNone(res)
        refl_ray, t = res
        self.assertGreater(t, 0.0)
        self.assertAlmostEqual(refl_ray.intensity, substrate.reflectivity)

    def test_dcra_aerial_convergence(self):
        substrate = DCRASubstrate(center=[0.0, 0.0, 0.0], tilt_angle_deg=45.0, width_mm=300.0, height_mm=300.0)
        source = [0.0, -0.08, 0.0]

        sim = simulate_dcra_convergence(source, substrate, num_cone_rays=12)
        self.assertTrue(sim["converged"])
        self.assertGreater(sim["captured_rays"], 4)
        # RMS spot radius must be tight in free space (< 15 mm)
        self.assertLess(sim["rms_spot_radius_mm"], 15.0)
        self.assertTrue(sim["free_space_traversable"])


if __name__ == "__main__":
    unittest.main()
