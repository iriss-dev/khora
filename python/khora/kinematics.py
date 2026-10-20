"""
SE(3) Spatial Kinematics, DLS Inverse Kinematics & S-Curve Jerk-Bounded Profiling.
Pure standard-library implementation for deterministic execution across any environment.
"""

import math
from typing import List, Tuple, Optional, Dict, Any


# ---------------------------------------------------------------------------
# Vector & Matrix Utilities (4x4 Homogeneous Transformations)
# ---------------------------------------------------------------------------

def vec3(x: float, y: float, z: float) -> List[float]:
    return [float(x), float(y), float(z)]

def vec3_dot(a: List[float], b: List[float]) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]

def vec3_cross(a: List[float], b: List[float]) -> List[float]:
    return [
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0]
    ]

def vec3_norm(a: List[float]) -> float:
    return math.sqrt(vec3_dot(a, a))

def vec3_normalize(a: List[float]) -> List[float]:
    n = vec3_norm(a)
    if n < 1e-12:
        return [0.0, 0.0, 0.0]
    return [a[0]/n, a[1]/n, a[2]/n]

def mat4_identity() -> List[List[float]]:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]

def mat4_mul(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    C = [[0.0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            C[i][j] = sum(A[i][k] * B[k][j] for k in range(4))
    return C

def mat4_transform_point(M: List[List[float]], p: List[float]) -> List[float]:
    x = M[0][0]*p[0] + M[0][1]*p[1] + M[0][2]*p[2] + M[0][3]
    y = M[1][0]*p[0] + M[1][1]*p[1] + M[1][2]*p[2] + M[1][3]
    z = M[2][0]*p[0] + M[2][1]*p[1] + M[2][2]*p[2] + M[2][3]
    w = M[3][0]*p[0] + M[3][1]*p[1] + M[3][2]*p[2] + M[3][3]
    if abs(w - 1.0) > 1e-9 and abs(w) > 1e-12:
        return [x/w, y/w, z/w]
    return [x, y, z]

def mat4_transform_vector(M: List[List[float]], v: List[float]) -> List[float]:
    return [
        M[0][0]*v[0] + M[0][1]*v[1] + M[0][2]*v[2],
        M[1][0]*v[0] + M[1][1]*v[1] + M[1][2]*v[2],
        M[2][0]*v[0] + M[2][1]*v[1] + M[2][2]*v[2],
    ]

def mat4_inverse_se3(M: List[List[float]]) -> List[List[float]]:
    """Inversion of a rigid transformation in SE(3): R^T and -R^T * t."""
    R_T = [
        [M[0][0], M[1][0], M[2][0]],
        [M[0][1], M[1][1], M[2][1]],
        [M[0][2], M[1][2], M[2][2]],
    ]
    t = [M[0][3], M[1][3], M[2][3]]
    inv_t = [
        -(R_T[0][0]*t[0] + R_T[0][1]*t[1] + R_T[0][2]*t[2]),
        -(R_T[1][0]*t[0] + R_T[1][1]*t[1] + R_T[1][2]*t[2]),
        -(R_T[2][0]*t[0] + R_T[2][1]*t[1] + R_T[2][2]*t[2]),
    ]
    return [
        [R_T[0][0], R_T[0][1], R_T[0][2], inv_t[0]],
        [R_T[1][0], R_T[1][1], R_T[1][2], inv_t[1]],
        [R_T[2][0], R_T[2][1], R_T[2][2], inv_t[2]],
        [0.0,       0.0,       0.0,       1.0],
    ]


# ---------------------------------------------------------------------------
# SE(3) Transform Wrapper & Euler / Quaternion Conversions
# ---------------------------------------------------------------------------

class SE3Transform:
    def __init__(self, matrix: Optional[List[List[float]]] = None):
        self.matrix = matrix if matrix is not None else mat4_identity()

    @classmethod
    def from_translation(cls, x: float, y: float, z: float) -> "SE3Transform":
        m = mat4_identity()
        m[0][3] = float(x)
        m[1][3] = float(y)
        m[2][3] = float(z)
        return cls(m)

    @classmethod
    def from_euler_rpy(cls, roll: float, pitch: float, yaw: float) -> "SE3Transform":
        """Roll (X), Pitch (Y), Yaw (Z) intrinsic Tait-Bryan angles in radians."""
        cr, sr = math.cos(roll), math.sin(roll)
        cp, sp = math.cos(pitch), math.sin(pitch)
        cy, sy = math.cos(yaw), math.sin(yaw)

        m = [
            [cy*cp, cy*sp*sr - sy*cr, cy*sp*cr + sy*sr, 0.0],
            [sy*cp, sy*sp*sr + cy*cr, sy*sp*cr - cy*sr, 0.0],
            [-sp,   cp*sr,            cp*cr,            0.0],
            [0.0,   0.0,              0.0,              1.0],
        ]
        return cls(m)

    @classmethod
    def from_axis_angle(cls, axis: List[float], angle: float) -> "SE3Transform":
        u = vec3_normalize(axis)
        c, s = math.cos(angle), math.sin(angle)
        v = 1.0 - c

        m = [
            [u[0]*u[0]*v + c,       u[0]*u[1]*v - u[2]*s, u[0]*u[2]*v + u[1]*s, 0.0],
            [u[0]*u[1]*v + u[2]*s, u[1]*u[1]*v + c,       u[1]*u[2]*v - u[0]*s, 0.0],
            [u[0]*u[2]*v - u[1]*s, u[1]*u[2]*v + u[0]*s, u[2]*u[2]*v + c,       0.0],
            [0.0,                  0.0,                  0.0,                  1.0],
        ]
        return cls(m)

    def multiply(self, other: "SE3Transform") -> "SE3Transform":
        return SE3Transform(mat4_mul(self.matrix, other.matrix))

    def inverse(self) -> "SE3Transform":
        return SE3Transform(mat4_inverse_se3(self.matrix))

    @property
    def translation(self) -> List[float]:
        return [self.matrix[0][3], self.matrix[1][3], self.matrix[2][3]]

    def to_quaternion(self) -> List[float]:
        """Returns [w, x, y, z]."""
        m = self.matrix
        tr = m[0][0] + m[1][1] + m[2][2]
        if tr > 0.0:
            S = math.sqrt(tr + 1.0) * 2.0
            w = 0.25 * S
            x = (m[2][1] - m[1][2]) / S
            y = (m[0][2] - m[2][0]) / S
            z = (m[1][0] - m[0][1]) / S
        elif (m[0][0] > m[1][1]) and (m[0][0] > m[2][2]):
            S = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2.0
            w = (m[2][1] - m[1][2]) / S
            x = 0.25 * S
            y = (m[0][1] + m[1][0]) / S
            z = (m[0][2] + m[2][0]) / S
        elif m[1][1] > m[2][2]:
            S = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2.0
            w = (m[0][2] - m[2][0]) / S
            x = (m[0][1] + m[1][0]) / S
            y = 0.25 * S
            z = (m[1][2] + m[2][1]) / S
        else:
            S = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2.0
            w = (m[1][0] - m[0][1]) / S
            x = (m[0][2] + m[2][0]) / S
            y = (m[1][2] + m[2][1]) / S
            z = 0.25 * S
        return [w, x, y, z]


# ---------------------------------------------------------------------------
# Serial Kinematic Chain & Jacobian
# ---------------------------------------------------------------------------

class Joint:
    def __init__(
        self,
        name: str,
        joint_type: str,  # 'revolute' or 'prismatic'
        axis: List[float],
        origin_offset: List[float],
        limits: Tuple[float, float] = (-math.pi, math.pi),
    ):
        self.name = name
        self.joint_type = joint_type
        self.axis = vec3_normalize(axis)
        self.origin_offset = origin_offset
        self.limits = limits

    def get_local_transform(self, q: float) -> SE3Transform:
        T_offset = SE3Transform.from_translation(*self.origin_offset)
        if self.joint_type == 'revolute':
            T_rot = SE3Transform.from_axis_angle(self.axis, q)
            return T_offset.multiply(T_rot)
        else:
            dx = self.axis[0] * q
            dy = self.axis[1] * q
            dz = self.axis[2] * q
            return T_offset.multiply(SE3Transform.from_translation(dx, dy, dz))


class KinematicChain:
    def __init__(self, joints: List[Joint]):
        self.joints = joints

    @property
    def dof(self) -> int:
        return len(self.joints)

    def forward_kinematics(self, q_angles: List[float]) -> SE3Transform:
        if len(q_angles) != self.dof:
            raise ValueError(f"Expected {self.dof} joint values, got {len(q_angles)}")

        T = SE3Transform()
        for joint, q in zip(self.joints, q_angles):
            T = T.multiply(joint.get_local_transform(q))
        return T

    def compute_jacobian(self, q_angles: List[float]) -> List[List[float]]:
        """
        Computes 6xN Geometric Jacobian J:
        Top 3 rows = linear velocity contribution (v = z_i x (p_end - p_joint))
        Bottom 3 rows = angular velocity contribution (omega = z_i)
        """
        n = self.dof
        J = [[0.0]*n for _ in range(6)]
        p_end = self.forward_kinematics(q_angles).translation

        T_curr = SE3Transform()
        for i, joint in enumerate(self.joints):
            T_offset = SE3Transform.from_translation(*joint.origin_offset)
            T_joint_origin = T_curr.multiply(T_offset)
            z_axis = mat4_transform_vector(T_joint_origin.matrix, joint.axis)
            p_joint = T_joint_origin.translation
            r = [p_end[0] - p_joint[0], p_end[1] - p_joint[1], p_end[2] - p_joint[2]]

            if joint.joint_type == 'revolute':
                v = vec3_cross(z_axis, r)
                J[0][i] = v[0]
                J[1][i] = v[1]
                J[2][i] = v[2]
                J[3][i] = z_axis[0]
                J[4][i] = z_axis[1]
                J[5][i] = z_axis[2]
                T_rot = SE3Transform.from_axis_angle(joint.axis, q_angles[i])
                T_curr = T_joint_origin.multiply(T_rot)
            else:
                J[0][i] = z_axis[0]
                J[1][i] = z_axis[1]
                J[2][i] = z_axis[2]
                J[3][i] = 0.0
                J[4][i] = 0.0
                J[5][i] = 0.0
                dx = joint.axis[0] * q_angles[i]
                dy = joint.axis[1] * q_angles[i]
                dz = joint.axis[2] * q_angles[i]
                T_curr = T_joint_origin.multiply(SE3Transform.from_translation(dx, dy, dz))

        return J


# ---------------------------------------------------------------------------
# Linear Algebra Utilities for IK & Manipulability
# ---------------------------------------------------------------------------

def matrix_transpose(M: List[List[float]]) -> List[List[float]]:
    rows = len(M)
    cols = len(M[0])
    return [[M[r][c] for r in range(rows)] for c in range(cols)]

def matrix_multiply(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    rA, cA = len(A), len(A[0])
    rB, cB = len(B), len(B[0])
    if cA != rB:
        raise ValueError("Incompatible matrix dimensions for multiplication")
    res = [[0.0]*cB for _ in range(rA)]
    for i in range(rA):
        for j in range(cB):
            res[i][j] = sum(A[i][k] * B[k][j] for k in range(cA))
    return res

def solve_linear_system_gauss(A: List[List[float]], b: List[float]) -> List[float]:
    """Solves A * x = b via Gaussian elimination with partial pivoting."""
    n = len(A)
    # Augment matrix
    M = [A[i][:] + [b[i]] for i in range(n)]

    for i in range(n):
        # Pivot selection
        max_row = i
        max_val = abs(M[i][i])
        for r in range(i+1, n):
            if abs(M[r][i]) > max_val:
                max_val = abs(M[r][i])
                max_row = r
        if max_val < 1e-12:
            # Singular / near singular
            M[i][i] = 1e-6
        if max_row != i:
            M[i], M[max_row] = M[max_row], M[i]

        # Elimination
        pivot = M[i][i]
        for c in range(i, n+1):
            M[i][c] /= pivot
        for r in range(n):
            if r != i:
                factor = M[r][i]
                for c in range(i, n+1):
                    M[r][c] -= factor * M[i][c]

    return [M[i][n] for i in range(n)]

def manipulability_index(J: List[List[float]]) -> float:
    """Yoshikawa's manipulability index: w = sqrt(det(J * J^T)) for linear task space (3x3)."""
    J_pos = J[:3]  # First 3 rows: position Jacobian
    J_pos_T = matrix_transpose(J_pos)
    JJT = matrix_multiply(J_pos, J_pos_T)  # 3x3

    # Determinant of 3x3 matrix
    det = (
        JJT[0][0] * (JJT[1][1]*JJT[2][2] - JJT[1][2]*JJT[2][1]) -
        JJT[0][1] * (JJT[1][0]*JJT[2][2] - JJT[1][2]*JJT[2][0]) +
        JJT[0][2] * (JJT[1][0]*JJT[2][1] - JJT[1][1]*JJT[2][0])
    )
    return math.sqrt(max(0.0, det))


def solve_ik_dls(
    chain: KinematicChain,
    q_init: List[float],
    target_pos: List[float],
    max_iter: int = 60,
    tolerance: float = 1e-4,
    lambda_base: float = 1e-4,
) -> Tuple[List[float], bool, Dict[str, Any]]:
    """
    Damped Least Squares (Levenberg-Marquardt style) IK for position convergence.
    Prevents joint runaway near singularities with bounded angular step size.
    """
    q = q_init[:]
    converged = False

    for iteration in range(max_iter):
        T_curr = chain.forward_kinematics(q)
        pos_curr = T_curr.translation
        error = [
            target_pos[0] - pos_curr[0],
            target_pos[1] - pos_curr[1],
            target_pos[2] - pos_curr[2],
        ]
        err_norm = vec3_norm(error)
        if err_norm < tolerance:
            converged = True
            break

        J = chain.compute_jacobian(q)
        J_pos = J[:3]  # 3 x DOF
        w = manipulability_index(J)

        # Dynamic damping factor: smooth Buss formulation
        w_thresh = 0.005
        if w >= w_thresh:
            lambda_sq = lambda_base
        else:
            ratio = max(0.0, 1.0 - w / w_thresh)
            lambda_sq = lambda_base + 0.01 * (ratio ** 2)

        # DLS equation: delta_q = J_T * (J * J_T + lambda^2 * I)^(-1) * error
        J_T = matrix_transpose(J_pos)
        JJT = matrix_multiply(J_pos, J_T)  # 3x3

        # Add damping to diagonal
        for k in range(3):
            JJT[k][k] += lambda_sq

        # Solve (JJT + lambda^2*I) * y = error
        y = solve_linear_system_gauss(JJT, error)

        # delta_q = J_T * y with maximum step bounding for numerical stability
        for i in range(chain.dof):
            step = sum(J_T[i][k] * y[k] for k in range(3))
            step = max(-0.25, min(0.25, step))
            q[i] += step
            q_min, q_max = chain.joints[i].limits
            q[i] = max(q_min, min(q_max, q[i]))

    final_T = chain.forward_kinematics(q)
    final_err = vec3_norm([
        target_pos[0] - final_T.translation[0],
        target_pos[1] - final_T.translation[1],
        target_pos[2] - final_T.translation[2],
    ])
    final_w = manipulability_index(chain.compute_jacobian(q))

    return q, converged, {
        "iterations": iteration + 1,
        "final_error_mm": final_err * 1000.0,
        "manipulability": final_w,
        "singularity_risk": final_w < 1e-3,
    }


# ---------------------------------------------------------------------------
# S-Curve Jerk-Bounded Trajectory Planner (RFC-0002)
# ---------------------------------------------------------------------------

class SCurvePlanner:
    """Generates continuous jerk-limited (7-phase) trajectories."""

    def __init__(self, v_max: float, a_max: float, j_max: float):
        self.v_max = abs(v_max)
        self.a_max = abs(a_max)
        self.j_max = abs(j_max)

    def plan_point_to_point(self, q0: float, q1: float) -> Dict[str, Any]:
        """Calculates timestamps and phases for 1D translation."""
        dist = q1 - q0
        sign = 1.0 if dist >= 0 else -1.0
        D = abs(dist)

        # Time to reach a_max with j_max
        t_j = self.a_max / self.j_max
        # Velocity gained during acceleration ramp
        v_j = 0.5 * self.j_max * (t_j ** 2)

        if self.v_max <= 2.0 * v_j:
            # Does not reach a_max
            t_j = math.sqrt(self.v_max / self.j_max)
            t_a = 0.0
            v_peak = self.j_max * (t_j ** 2)
        else:
            t_a = (self.v_max - 2.0 * v_j) / self.a_max
            v_peak = self.v_max

        # Distance covered during acceleration phase
        d_acc = 2.0 * v_j * t_j + (v_peak * t_a)
        
        if D < 2.0 * d_acc:
            # Short move: does not reach v_max, scale back
            scale = math.pow(D / (2.0 * d_acc), 1.0/3.0)
            t_j *= scale
            t_a = 0.0
            t_v = 0.0
        else:
            t_v = (D - 2.0 * d_acc) / v_peak

        total_time = 4.0 * t_j + 2.0 * t_a + t_v

        return {
            "direction": sign,
            "total_duration_s": total_time,
            "phases": {
                "t_jerk": t_j,
                "t_const_accel": t_a,
                "t_cruise": t_v,
            },
            "parameters": {
                "v_peak": v_peak,
                "j_max": self.j_max,
                "a_max": self.a_max,
                "displacement": dist,
            }
        }
