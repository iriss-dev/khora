import unittest
import math
import sys
import os

# Add python directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from khora.kinematics import (
    SE3Transform, Joint, KinematicChain, solve_ik_dls, SCurvePlanner,
    manipulability_index, vec3_norm
)


class TestKinematics(unittest.TestCase):

    def test_se3_translation_and_inverse(self):
        T = SE3Transform.from_translation(1.5, -2.0, 3.25)
        self.assertAlmostEqual(T.translation[0], 1.5)
        self.assertAlmostEqual(T.translation[1], -2.0)
        self.assertAlmostEqual(T.translation[2], 3.25)

        T_inv = T.inverse()
        self.assertAlmostEqual(T_inv.translation[0], -1.5)
        self.assertAlmostEqual(T_inv.translation[1], 2.0)
        self.assertAlmostEqual(T_inv.translation[2], -3.25)

        # Identity test: T * T_inv = I
        T_ident = T.multiply(T_inv)
        for i in range(4):
            for j in range(4):
                expected = 1.0 if i == j else 0.0
                self.assertAlmostEqual(T_ident.matrix[i][j], expected, places=7)

    def test_quaternion_conversion(self):
        # 90 degrees around Z axis
        T = SE3Transform.from_euler_rpy(0.0, 0.0, math.pi / 2.0)
        q = T.to_quaternion()  # [w, x, y, z]
        # For +90 deg Z: w = cos(45 deg) = sqrt(2)/2, z = sin(45 deg) = sqrt(2)/2
        expected_wz = math.sqrt(2.0) / 2.0
        self.assertAlmostEqual(q[0], expected_wz, places=5)
        self.assertAlmostEqual(q[1], 0.0, places=5)
        self.assertAlmostEqual(q[2], 0.0, places=5)
        self.assertAlmostEqual(q[3], expected_wz, places=5)

    def test_forward_kinematics_and_jacobian(self):
        joints = [
            Joint("j1", "revolute", [0, 0, 1], [0, 0, 1.0]),
            Joint("j2", "revolute", [0, 1, 0], [1.0, 0, 0]),
        ]
        chain = KinematicChain(joints)
        T0 = chain.forward_kinematics([0.0, 0.0])
        # Joint 1 origin at (0,0,1), Joint 2 offset by (1,0,0) => end effector at (1, 0, 1)
        self.assertAlmostEqual(T0.translation[0], 1.0, places=5)
        self.assertAlmostEqual(T0.translation[1], 0.0, places=5)
        self.assertAlmostEqual(T0.translation[2], 1.0, places=5)

        J = chain.compute_jacobian([0.0, 0.0])
        self.assertEqual(len(J), 6)
        self.assertEqual(len(J[0]), 2)

    def test_dls_inverse_kinematics(self):
        # 6-DOF standard manipulator
        joints = [
            Joint("j1", "revolute", [0, 0, 1], [0.0, 0.0, 0.15]),
            Joint("j2", "revolute", [0, 1, 0], [0.0, 0.0, 0.15]),
            Joint("j3", "revolute", [0, 1, 0], [0.0, 0.0, 0.30]),
            Joint("j4", "revolute", [0, 0, 1], [0.0, 0.0, 0.25]),
            Joint("j5", "revolute", [0, 1, 0], [0.0, 0.0, 0.10]),
            Joint("j6", "revolute", [0, 0, 1], [0.0, 0.0, 0.08]),
        ]
        chain = KinematicChain(joints)
        target = [0.25, 0.15, 0.55]
        q_init = [0.1, 0.2, -0.2, 0.0, 0.1, 0.0]

        q_sol, converged, meta = solve_ik_dls(chain, q_init, target, max_iter=60, tolerance=1e-3)
        self.assertTrue(converged, f"IK did not converge: {meta}")
        self.assertLess(meta["final_error_mm"], 1.0)

    def test_scurve_trajectory_planner(self):
        planner = SCurvePlanner(v_max=1.0, a_max=2.0, j_max=10.0)
        profile = planner.plan_point_to_point(0.0, 5.0)

        self.assertGreater(profile["total_duration_s"], 0.0)
        self.assertGreater(profile["phases"]["t_jerk"], 0.0)
        self.assertEqual(profile["direction"], 1.0)


if __name__ == "__main__":
    unittest.main()
