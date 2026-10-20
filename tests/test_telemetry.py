import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from khora.telemetry import SpatialKalmanFilter, HolographicInteractiveVolume, SpatialInteractionManager


class TestTelemetry(unittest.TestCase):

    def test_kalman_filter_smoothing(self):
        f = SpatialKalmanFilter(alpha=0.5)
        p1 = f.update([10.0, 20.0, 30.0], timestamp=1.0)
        self.assertEqual(p1, [10.0, 20.0, 30.0])

        # Step jump
        p2 = f.update([20.0, 40.0, 60.0], timestamp=1.1)
        # Should be smoothed to midpoint (0.5 * 20 + 0.5 * 10 = 15.0)
        self.assertAlmostEqual(p2[0], 15.0)
        self.assertAlmostEqual(p2[1], 30.0)
        self.assertAlmostEqual(p2[2], 45.0)

    def test_holographic_volume_penetration(self):
        # Center [0.0, 0.16, 0.03], size [0.04, 0.04, 0.04]
        vol = HolographicInteractiveVolume(center=[0.0, 0.16, 0.03], size=[0.04, 0.04, 0.04])
        
        # Outside point
        inside, depth, norm = vol.check_penetration([0.0, 0.0, 0.0])
        self.assertFalse(inside)

        # Inside point (at center)
        inside, depth, norm = vol.check_penetration([0.0, 0.16, 0.03])
        self.assertTrue(inside)
        self.assertGreater(depth, 0.0)

        # Force computation
        force = vol.compute_haptic_force(0.005, norm)
        self.assertGreater(force["force_mn"], 0.1)
        self.assertLessEqual(force["force_mn"], 15.0)

    def test_spatial_interaction_manager(self):
        mgr = SpatialInteractionManager()
        # Outside frame
        res1 = mgr.process_hand_frame([0.5, 0.5, 0.5])
        self.assertFalse(res1["intersecting_hologram"])
        self.assertIsNone(res1["haptic_feedback"])

        # Feed target frames to penetrate hologram center
        for _ in range(4):
            res_settled = mgr.process_hand_frame([0.0, 0.16, 0.03])

        self.assertTrue(res_settled["intersecting_hologram"])
        self.assertIsNotNone(res_settled["haptic_feedback"])
        self.assertGreater(res_settled["haptic_feedback"]["force_mn"], 0.5)
        self.assertIsNotNone(res_settled["phases_8bit"])
        self.assertEqual(len(res_settled["phases_8bit"]), 256)


if __name__ == "__main__":
    unittest.main()
