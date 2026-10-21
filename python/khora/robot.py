"""Reference arm geometry and joint-space plans, in metres and radians."""
import math
from .kinematics import (Joint, KinematicChain, SE3Transform, mat4_mul,
                         mat4_transform_vector, solve_ik_dls)

HOME = [0.1, 0.4, -0.7, 0.0, 0.3, 0.0]
AXES = [[0, 0, 1], [0, 1, 0], [0, 1, 0], [0, 0, 1], [0, 1, 0], [0, 0, 1]]
OFFSETS = [[0, 0, z] for z in [.15, .15, .30, .25, .10, .08]]
LIMITS = [(-math.pi, math.pi), (-math.pi*.75, math.pi*.75),
          (-math.pi*.8, math.pi*.8), (-math.pi, math.pi),
          (-math.pi*.75, math.pi*.75), (-math.pi, math.pi)]


def vector(value, length, name):
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f"{name} must contain {length} numbers")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in value):
        raise ValueError(f"{name} must contain finite numbers")
    return [float(x) for x in value]


def reference_arm():
    return KinematicChain([Joint(f"joint_{i+1}", "revolute", axis, offset, limits)
                           for i, (axis, offset, limits) in enumerate(zip(AXES, OFFSETS, LIMITS))])


def validate_joints(q):
    q = vector(q, 6, "joints_rad")
    for i, (value, (low, high)) in enumerate(zip(q, LIMITS)):
        if not low <= value <= high:
            raise ValueError(f"Joint {i+1} exceeds model limits")
    return q


def twist_exponential(axis, point, angle):
    rotation = SE3Transform.from_axis_angle(axis, angle).matrix
    rotated = mat4_transform_vector(rotation, point)
    for i in range(3):
        rotation[i][3] = point[i] - rotated[i]
    return rotation


def forward_poe(joints_rad):
    q = validate_joints(joints_rad)
    transform = SE3Transform().matrix
    height = 0.0
    for axis, offset, angle in zip(AXES, OFFSETS, q):
        height += offset[2]
        transform = mat4_mul(transform, twist_exponential(axis, [0, 0, height], angle))
    return mat4_mul(transform, SE3Transform.from_translation(0, 0, height).matrix)


def plan_move(target_m, start_joints_rad=None, v_max=0.8, a_max=1.5, j_max=8.0):
    target = vector(target_m, 3, "target_m")
    if math.hypot(*target[:2]) > .7 or not .15 <= target[2] <= .95:
        raise ValueError("Target is outside the reference workspace (radius 0.7 m, Z 0.15–0.95 m)")
    start = validate_joints(HOME if start_joints_rad is None else start_joints_rad)
    for name, limit in [("v_max", v_max), ("a_max", a_max), ("j_max", j_max)]:
        if isinstance(limit, bool) or not isinstance(limit, (int, float)) or not math.isfinite(limit) or limit <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if v_max > 1.5 or a_max > 3 or j_max > 20:
        raise ValueError("Reference motion limits exceeded")
    chain = reference_arm()
    end, converged, metrics = solve_ik_dls(chain, start, target, max_iter=300, tolerance=1e-5)
    if not converged:
        raise ValueError("Target could not be reached within joint limits")
    validate_joints(end)
    delta = [b-a for a, b in zip(start, end)]
    distance = max(abs(x) for x in delta)
    duration = max(.25, 1.875*distance/v_max,
                   math.sqrt((10/math.sqrt(3))*distance/a_max),
                   (60*distance/j_max)**(1/3))
    samples = []
    for index in range(101):
        u = index/100
        s = 10*u**3 - 15*u**4 + 6*u**5
        q = [a+d*s for a, d in zip(start, delta)]
        pose = forward_poe(q)
        samples.append({"time_s": duration*u, "joints_rad": q,
                        "position_m": [pose[i][3] for i in range(3)]})
    return {"schema": "khora.robot-plan/1", "model": "khora-reference-6r",
            "execution": "simulation_only", "target_m": target,
            "duration_s": duration, "joint_limits_rad": LIMITS,
            "motion_limits": {"velocity_rad_s": v_max, "acceleration_rad_s2": a_max, "jerk_rad_s3": j_max},
            "interpolation": "synchronized quintic, zero endpoint velocity and acceleration",
            "position_error_mm": metrics["final_error_mm"], "samples": samples,
            "collision_check": "not implemented; joint limits do not establish collision clearance"}
