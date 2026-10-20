"""
High-Frequency Spatial Telemetry & Contactless Hand Interaction Bridge (RFC-0001).
Filters sub-5ms 3D hand tracking coordinates and calculates virtual haptic collision forces.
"""

import math
import time
from typing import List, Tuple, Optional, Dict, Any
from .kinematics import vec3_norm, vec3_normalize
from .haptics import AcousticPhasedArray, compute_beamforming_phases


class SpatialKalmanFilter:
    """1D/3D low-pass spatial smoothing filter for noisy IR/optical hand trackers."""

    def __init__(self, alpha: float = 0.75):
        self.alpha = alpha  # Higher = more responsive, lower = smoother
        self.filtered_pos: Optional[List[float]] = None
        self.velocity: List[float] = [0.0, 0.0, 0.0]
        self.last_timestamp: float = time.time()

    def update(self, raw_pos: List[float], timestamp: Optional[float] = None) -> List[float]:
        t = timestamp if timestamp is not None else time.time()
        dt = max(1e-4, t - self.last_timestamp)
        self.last_timestamp = t

        if self.filtered_pos is None:
            self.filtered_pos = [float(x) for x in raw_pos]
            self.velocity = [0.0, 0.0, 0.0]
            return self.filtered_pos

        new_filtered = []
        for i in range(3):
            # Exponential smoothing
            val = self.alpha * raw_pos[i] + (1.0 - self.alpha) * self.filtered_pos[i]
            vel = (val - self.filtered_pos[i]) / dt
            self.velocity[i] = vel
            new_filtered.append(val)

        self.filtered_pos = new_filtered
        return self.filtered_pos


class HolographicInteractiveVolume:
    """
    Defines an axis-aligned bounding box (AABB) in open air representing the floating light image.
    When a human fingertip penetrates the boundary, calculates tactile resistance force.
    """

    def __init__(
        self,
        center: List[float] = [0.0, 0.16, 0.03],  # meters
        size: List[float] = [0.04, 0.04, 0.04],   # 40x40x40 mm floating cube
        stiffness_n_per_m: float = 120.0,         # Virtual mechanical spring constant
    ):
        self.center = center
        self.size = size
        self.stiffness = stiffness_n_per_m

        self.min_bounds = [center[i] - size[i] / 2.0 for i in range(3)]
        self.max_bounds = [center[i] + size[i] / 2.0 for i in range(3)]

    def check_penetration(self, fingertip_pos: List[float]) -> Tuple[bool, float, List[float]]:
        """
        Returns (is_inside, penetration_depth_m, normal_vector).
        """
        for i in range(3):
            if fingertip_pos[i] < self.min_bounds[i] or fingertip_pos[i] > self.max_bounds[i]:
                return False, 0.0, [0.0, 0.0, 0.0]

        # Calculate closest surface normal and penetration depth
        dist_to_min = [fingertip_pos[i] - self.min_bounds[i] for i in range(3)]
        dist_to_max = [self.max_bounds[i] - fingertip_pos[i] for i in range(3)]

        min_depth = 1e9
        normal = [0.0, 0.0, 1.0]

        for i in range(3):
            if dist_to_min[i] < min_depth:
                min_depth = dist_to_min[i]
                normal = [0.0, 0.0, 0.0]
                normal[i] = -1.0
            if dist_to_max[i] < min_depth:
                min_depth = dist_to_max[i]
                normal = [0.0, 0.0, 0.0]
                normal[i] = 1.0

        return True, min_depth, normal

    def compute_haptic_force(self, penetration_depth_m: float, normal: List[float]) -> Dict[str, Any]:
        """Calculates physical force vector to be synthesized by ultrasonic radiation pressure."""
        # Force magnitude F = k * x (clamped to max ultrasound capability of ~15 mN)
        force_n = min(0.015, self.stiffness * penetration_depth_m)
        force_mn = force_n * 1000.0

        return {
            "force_mn": force_mn,
            "force_vector": [normal[i] * force_mn for i in range(3)],
            "depth_mm": penetration_depth_m * 1000.0,
            "tactile_active": force_mn >= 1.0,
        }


class SpatialInteractionManager:
    """Coordinates hand telemetry with ultrasonic phased-array beamforming."""

    def __init__(self, phased_array: Optional[AcousticPhasedArray] = None):
        self.filter = SpatialKalmanFilter(alpha=0.8)
        self.volume = HolographicInteractiveVolume()
        self.array = phased_array if phased_array is not None else AcousticPhasedArray(16, 16)
        self.last_event_time = 0.0

    def process_hand_frame(self, raw_fingertip: List[float]) -> Dict[str, Any]:
        """Processes a single 3D tracking frame and outputs real-time haptic instructions."""
        smooth_pos = self.filter.update(raw_fingertip)
        is_inside, depth, normal = self.volume.check_penetration(smooth_pos)

        haptic_result = None
        phases_8bit = None

        if is_inside:
            force_data = self.volume.compute_haptic_force(depth, normal)
            synth = self.array.synthesize_focus(smooth_pos)
            haptic_result = {
                "force_mn": force_data["force_mn"],
                "depth_mm": force_data["depth_mm"],
                "spl_db": synth["spl_db"],
            }
            phases_8bit = synth["phases_8bit"]

        return {
            "fingertip_filtered": smooth_pos,
            "velocity": self.filter.velocity,
            "intersecting_hologram": is_inside,
            "haptic_feedback": haptic_result,
            "phases_8bit": phases_8bit,
        }
