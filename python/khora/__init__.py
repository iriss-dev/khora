"""
KHORA: Deterministic Robotics Kinematics, Spatial Computing & Traversable Light.
"""

__version__ = "0.3.1-alpha"
__author__ = "iriss-dev <contact@iriss.dev>"
__license__ = "MIT"

from .kinematics import (
    SE3Transform,
    KinematicChain,
    SCurvePlanner,
    solve_ik_dls,
    manipulability_index,
)
from .optics import (
    DCRASubstrate,
    Ray,
    simulate_dcra_convergence,
)
from .haptics import (
    AcousticPhasedArray,
    compute_beamforming_phases,
    estimate_radiation_force,
)

__all__ = [
    "SE3Transform",
    "KinematicChain",
    "SCurvePlanner",
    "solve_ik_dls",
    "manipulability_index",
    "DCRASubstrate",
    "Ray",
    "simulate_dcra_convergence",
    "AcousticPhasedArray",
    "compute_beamforming_phases",
    "estimate_radiation_force",
]
