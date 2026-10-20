import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from khora.mcp_server import handle_tool_call, TOOLS


class TestMCPTools(unittest.TestCase):

    def test_tools_registered(self):
        names = [t["name"] for t in TOOLS]
        self.assertIn("khora_kinematic_solve_ik", names)
        self.assertIn("khora_simulate_aerial_ray_trace", names)
        self.assertIn("khora_compute_haptic_focal_plane", names)
        self.assertIn("khora_plan_trajectory", names)
        self.assertIn("khora_safety_envelope_verify", names)

    def test_kinematic_ik_tool(self):
        res = handle_tool_call("khora_kinematic_solve_ik", {"target_pos": [0.25, 0.15, 0.55]})
        self.assertTrue(res["converged"])
        self.assertEqual(len(res["solution_joint_angles"]), 6)

    def test_aerial_ray_trace_tool(self):
        res = handle_tool_call("khora_simulate_aerial_ray_trace", {"source_point": [0.0, -0.1, 0.0]})
        self.assertTrue(res["converged"])
        self.assertTrue(res["free_space_traversable"])

    def test_haptic_tool(self):
        res = handle_tool_call("khora_compute_haptic_focal_plane", {"focal_point": [0.0, 0.1, 0.1], "grid_size": 8})
        self.assertEqual(res["transducers"], 64)
        self.assertIn("normal_force_mn", res)

    def test_safety_envelope_tool(self):
        res_ok = handle_tool_call("khora_safety_envelope_verify", {"joint_angles": [0.0, 0.5, -0.5, 0.0, 0.2, 0.0]})
        self.assertTrue(res_ok["within_joint_limits"])
        self.assertEqual(res_ok["status"], "APPROVED")

        res_bad = handle_tool_call("khora_safety_envelope_verify", {"joint_angles": [0.0, 50.0, 0.0, 0.0, 0.0, 0.0]})
        self.assertFalse(res_bad["within_joint_limits"])
        self.assertEqual(res_bad["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
