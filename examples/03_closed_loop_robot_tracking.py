#!/usr/bin/env python3
"""
Example 03: Deterministic 6-DOF Robotic Tracking with DLS IK & S-Curves
Demonstrates how KHORA solves kinematic trajectories with bounded jerk.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from khora.kinematics import Joint, KinematicChain, solve_ik_dls, SCurvePlanner, manipulability_index


def main():
    print("=" * 65)
    print("KHORA // Deterministic Kinematics & S-Curve Profiler (RFC-0002)")
    print("=" * 65)

    # 6-DOF standard serial manipulator
    joints = [
        Joint("j1_base", "revolute", [0, 0, 1], [0.0, 0.0, 0.15]),
        Joint("j2_shoulder", "revolute", [0, 1, 0], [0.0, 0.0, 0.15]),
        Joint("j3_elbow", "revolute", [0, 1, 0], [0.0, 0.0, 0.30]),
        Joint("j4_wrist1", "revolute", [0, 0, 1], [0.0, 0.0, 0.25]),
        Joint("j5_wrist2", "revolute", [0, 1, 0], [0.0, 0.0, 0.10]),
        Joint("j6_wrist3", "revolute", [0, 0, 1], [0.0, 0.0, 0.08]),
    ]
    arm = KinematicChain(joints)

    # Target pose in Cartesian space (touching floating optical hologram)
    target_pos = [0.22, 0.14, 0.52]  # meters
    q_initial = [0.1, 0.2, -0.2, 0.0, 0.1, 0.0]

    print(f"[*] Solving DLS Inverse Kinematics for target: {target_pos} m")
    q_sol, converged, meta = solve_ik_dls(arm, q_initial, target_pos)

    print(f"[+] Converged:             {converged} (in {meta['iterations']} iterations)")
    print(f"[+] Final Positional Error:{meta['final_error_mm']:.4f} mm")
    print(f"[+] Manipulability Index:  {meta['manipulability']:.6f} (Risk: {meta['singularity_risk']})")
    print(f"[+] Computed Joint Angles: {[round(x, 4) for x in q_sol]} rad")

    # Plan 7-segment S-Curve for base joint rotation
    planner = SCurvePlanner(v_max=1.5, a_max=3.0, j_max=15.0)
    profile = planner.plan_point_to_point(q_initial[0], q_sol[0])

    print("\n[*] S-Curve Jerk-Bounded Trajectory Profile (Joint 1):")
    print(f"[+] Total Move Duration:    {profile['total_duration_s']:.3f} s")
    print(f"[+] Jerk Ramp Duration:     {profile['phases']['t_jerk']:.4f} s")
    print(f"[+] Cruise Duration:        {profile['phases']['t_cruise']:.4f} s")
    print(f"[+] Max Jerk Limit:         {profile['parameters']['j_max']} rad/s^3")
    print("[SIMULATION] Numerical planning complete; validate the measured mechanism before hardware execution.")


if __name__ == "__main__":
    main()
