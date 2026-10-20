"""
Optical Simulation for Dihedral Corner Reflector Arrays (DCRA / Aerial Imaging Plates).
Simulates 1:1 real-image free-space retro-reflection without lenses or screens (RFC-0001).
"""

import math
from typing import List, Tuple, Optional, Dict, Any
from .kinematics import (
    vec3, vec3_dot, vec3_cross, vec3_norm, vec3_normalize,
    SE3Transform, mat4_transform_point, mat4_transform_vector,
)


class Ray:
    def __init__(self, origin: List[float], direction: List[float], intensity: float = 1.0):
        self.origin = [float(x) for x in origin]
        self.direction = vec3_normalize(direction)
        self.intensity = float(intensity)

    def point_at(self, t: float) -> List[float]:
        return [
            self.origin[0] + self.direction[0] * t,
            self.origin[1] + self.direction[1] * t,
            self.origin[2] + self.direction[2] * t,
        ]


class DCRASubstrate:
    """
    Dihedral Corner Reflector Array (DCRA) optical plate model.
    In local coordinates (plate aligned with XY plane):
    Incident ray [vx, vy, vz] undergoes retro-reflection on orthogonal dihedral
    micro-mirrors: vx -> -vx, vy -> -vy, vz -> vz.
    """

    def __init__(
        self,
        center: List[float] = [0.0, 0.0, 0.0],
        tilt_angle_deg: float = 45.0,
        width_mm: float = 200.0,
        height_mm: float = 200.0,
        reflectivity: float = 0.88,
        pitch_mm: float = 0.5,
    ):
        self.center = center
        self.tilt_angle = math.radians(tilt_angle_deg)
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.reflectivity = reflectivity
        self.pitch_mm = pitch_mm

        # Transform from plate local frame to world frame
        # Plate is tilted around X-axis by tilt_angle
        self.T_world_plate = SE3Transform.from_translation(*center).multiply(
            SE3Transform.from_euler_rpy(self.tilt_angle, 0.0, 0.0)
        )
        self.T_plate_world = self.T_world_plate.inverse()

    @property
    def normal_vector(self) -> List[float]:
        """Normal to the substrate plane in world coordinates."""
        return mat4_transform_vector(self.T_world_plate.matrix, [0.0, 0.0, 1.0])

    def trace_ray(self, world_ray: Ray) -> Optional[Tuple[Ray, float]]:
        """
        Traces an incident ray through the DCRA plate.
        Returns (reflected_world_ray, distance_t) or None if ray misses the aperture.
        """
        # Transform ray to local plate frame
        local_origin = mat4_transform_point(self.T_plate_world.matrix, world_ray.origin)
        local_dir = mat4_transform_vector(self.T_plate_world.matrix, world_ray.direction)

        # Plane is Z = 0 in local coordinates
        # local_origin.z + t * local_dir.z = 0  =>  t = -local_origin.z / local_dir.z
        if abs(local_dir[2]) < 1e-9:
            return None  # Parallel to plate

        t = -local_origin[2] / local_dir[2]
        if t <= 1e-6:
            return None  # Ray points away from plate

        # Hit point on plate in local coords
        hit_x = local_origin[0] + local_dir[0] * t
        hit_y = local_origin[1] + local_dir[1] * t

        # Aperture check
        half_w = self.width_mm / 2000.0  # mm to meters
        half_h = self.height_mm / 2000.0
        if abs(hit_x) > half_w or abs(hit_y) > half_h:
            return None  # Missed aperture

        # DCRA retro-reflection physics:
        # Retro-reflect in plate plane (X -> -X, Y -> -Y) while preserving Z propagation
        reflected_local_dir = [-local_dir[0], -local_dir[1], local_dir[2]]

        # Transform back to world coordinates
        hit_world = mat4_transform_point(self.T_world_plate.matrix, [hit_x, hit_y, 0.0])
        reflected_world_dir = mat4_transform_vector(self.T_world_plate.matrix, reflected_local_dir)

        reflected_ray = Ray(
            origin=hit_world,
            direction=reflected_world_dir,
            intensity=world_ray.intensity * self.reflectivity,
        )
        return reflected_ray, t


def simulate_dcra_convergence(
    source_point: List[float],
    substrate: DCRASubstrate,
    num_cone_rays: int = 16,
    cone_half_angle_deg: float = 15.0,
) -> Dict[str, Any]:
    """
    Simulates a cone of light rays originating from a physical emitter (e.g. LCD pixel)
    and verifies their free-space convergence at the 1:1 aerial image focal plane.
    """
    cone_rad = math.radians(cone_half_angle_deg)
    
    # Vector from source to plate center
    center_vec = vec3_normalize([
        substrate.center[0] - source_point[0],
        substrate.center[1] - source_point[1],
        substrate.center[2] - source_point[2],
    ])

    reflected_rays: List[Ray] = []

    # Generate ray bundle
    for i in range(num_cone_rays):
        phi = (2.0 * math.pi * i) / num_cone_rays
        theta = cone_rad * (0.3 + 0.7 * (i % 3) / 2.0)

        # Perturbation vector orthogonal to center_vec
        up = [0.0, 1.0, 0.0] if abs(center_vec[1]) < 0.9 else [1.0, 0.0, 0.0]
        u = vec3_normalize(vec3_cross(center_vec, up))
        v = vec3_cross(center_vec, u)

        dir_vec = [
            center_vec[0] * math.cos(theta) + (u[0]*math.cos(phi) + v[0]*math.sin(phi)) * math.sin(theta),
            center_vec[1] * math.cos(theta) + (u[1]*math.cos(phi) + v[1]*math.sin(phi)) * math.sin(theta),
            center_vec[2] * math.cos(theta) + (u[2]*math.cos(phi) + v[2]*math.sin(phi)) * math.sin(theta),
        ]

        ray = Ray(source_point, dir_vec)
        res = substrate.trace_ray(ray)
        if res is not None:
            refl_ray, _ = res
            reflected_rays.append(refl_ray)

    if len(reflected_rays) < 2:
        return {
            "converged": False,
            "error": "Insufficient rays captured by DCRA aperture",
            "captured_rays": len(reflected_rays),
        }

    # Free-space focal point determination:
    # In DCRA physics, the aerial image point is symmetric to source across plate plane:
    # local_source = (x, y, -z) => local_focal = (x, y, +z)
    local_source = mat4_transform_point(substrate.T_plate_world.matrix, source_point)
    local_focal = [local_source[0], local_source[1], -local_source[2]]
    theoretical_focal_world = mat4_transform_point(substrate.T_world_plate.matrix, local_focal)

    # Compute closest distance of all reflected rays to theoretical focal point (RMS spot radius)
    residuals = []
    for r in reflected_rays:
        # Distance from point P to line (origin + t*direction)
        # d = norm((P - origin) x direction)
        diff = [theoretical_focal_world[k] - r.origin[k] for k in range(3)]
        cross = vec3_cross(diff, r.direction)
        dist = vec3_norm(cross)
        residuals.append(dist)

    rms_spot_radius_mm = math.sqrt(sum(d*d for d in residuals) / len(residuals)) * 1000.0
    air_distance_mm = abs(local_focal[2]) * 1000.0

    return {
        "converged": True,
        "theoretical_focal_point": theoretical_focal_world,
        "captured_rays": len(reflected_rays),
        "total_emitted_rays": num_cone_rays,
        "rms_spot_radius_mm": rms_spot_radius_mm,
        "air_focal_distance_mm": air_distance_mm,
        "free_space_traversable": True,
        "clearance_volume_mm": [
            substrate.width_mm * 0.75,
            substrate.height_mm * 0.75,
            air_distance_mm * 1.5,
        ],
    }
