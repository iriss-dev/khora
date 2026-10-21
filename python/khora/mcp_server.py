"""
Model Context Protocol (MCP) Server for KHORA.
Connects non-deterministic AI agents (Claude, GPT, Gemini) to deterministic kinematics,
optical aerial simulations, and ultrasound mid-air haptic synthesis via Stdio JSON-RPC 2.0.
"""

import sys
import json
import math
from typing import Dict, Any, List

from .kinematics import (
    KinematicChain, Joint, solve_ik_dls, SCurvePlanner, manipulability_index
)
from .optics import DCRASubstrate, simulate_dcra_convergence
from .haptics import AcousticPhasedArray


def build_default_6dof_manipulator() -> KinematicChain:
    """Builds a standard 6-DOF industrial/laboratory serial arm."""
    joints = [
        Joint("joint_1_base", "revolute", [0, 0, 1], [0.0, 0.0, 0.15], (-math.pi, math.pi)),
        Joint("joint_2_shoulder", "revolute", [0, 1, 0], [0.0, 0.0, 0.15], (-math.pi*0.75, math.pi*0.75)),
        Joint("joint_3_elbow", "revolute", [0, 1, 0], [0.0, 0.0, 0.30], (-math.pi*0.8, math.pi*0.8)),
        Joint("joint_4_wrist_1", "revolute", [0, 0, 1], [0.0, 0.0, 0.25], (-math.pi, math.pi)),
        Joint("joint_5_wrist_2", "revolute", [0, 1, 0], [0.0, 0.0, 0.10], (-math.pi*0.75, math.pi*0.75)),
        Joint("joint_6_wrist_3", "revolute", [0, 0, 1], [0.0, 0.0, 0.08], (-math.pi, math.pi)),
    ]
    return KinematicChain(joints)


TOOLS = [
    {
        "name": "khora_kinematic_solve_ik",
        "description": "Solves inverse kinematics for a 6-DOF manipulator using Damped Least Squares (DLS) with singularity avoidance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_pos": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Target [x, y, z] end-effector coordinate in meters.",
                },
                "q_init": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Optional starting joint angles in radians (length 6).",
                }
            },
            "required": ["target_pos"],
        }
    },
    {
        "name": "khora_simulate_aerial_ray_trace",
        "description": "Traces light cone through an Aerial Imaging Plate (DCRA) and computes the 1:1 free-space floating image coordinates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_point": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "[x, y, z] coordinate of physical light emitter in meters.",
                },
                "plate_tilt_deg": {
                    "type": "number",
                    "description": "Tilt angle of DCRA substrate in degrees (default: 45.0).",
                }
            },
            "required": ["source_point"],
        }
    },
    {
        "name": "khora_compute_haptic_focal_plane",
        "description": "Computes 40 kHz phased array ultrasound beamforming delays and estimated tactile radiation pressure on skin.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "focal_point": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "[x, y, z] target haptic coordinate in meters.",
                },
                "grid_size": {
                    "type": "integer",
                    "description": "Transducer grid dimension N (NxN array, default: 16).",
                }
            },
            "required": ["focal_point"],
        }
    },
    {
        "name": "khora_plan_trajectory",
        "description": "Synthesizes an S-Curve (7-phase) trajectory bounding jerk, acceleration, and velocity for vibration-free motion.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "q_start": {"type": "number", "description": "Starting position/angle."},
                "q_end": {"type": "number", "description": "Target setpoint position/angle."},
                "v_max": {"type": "number", "description": "Max velocity (units/s)."},
                "a_max": {"type": "number", "description": "Max acceleration (units/s^2)."},
                "j_max": {"type": "number", "description": "Max jerk (units/s^3)."},
            },
            "required": ["q_start", "q_end", "v_max", "a_max", "j_max"],
        }
    },
    {
        "name": "khora_safety_envelope_verify",
        "description": "Verifies that proposed joint angles adhere to physical hardware limits and evaluates singularity risk.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "joint_angles": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Array of 6 joint angles in radians.",
                }
            },
            "required": ["joint_angles"],
        }
    }
]


def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "khora_kinematic_solve_ik":
        target = arguments.get("target_pos", [0.2, 0.0, 0.5])
        q_init = arguments.get("q_init", [0.0]*6)
        chain = build_default_6dof_manipulator()
        q_sol, converged, meta = solve_ik_dls(chain, q_init, target)
        return {
            "target_pos": target,
            "solution_joint_angles": [round(x, 4) for x in q_sol],
            "converged": converged,
            "metrics": meta,
        }

    elif name == "khora_simulate_aerial_ray_trace":
        source = arguments.get("source_point", [0.0, -0.15, -0.15])
        tilt = arguments.get("plate_tilt_deg", 45.0)
        plate = DCRASubstrate(tilt_angle_deg=tilt)
        sim = simulate_dcra_convergence(source, plate)
        return sim

    elif name == "khora_compute_haptic_focal_plane":
        focal = arguments.get("focal_point", [0.0, 0.15, 0.15])
        grid_n = arguments.get("grid_size", 16)
        array = AcousticPhasedArray(grid_rows=grid_n, grid_cols=grid_n)
        synth = array.synthesize_focus(focal)
        # Summary for JSON output (avoid printing all 256 phases)
        return {
            "focal_point_m": focal,
            "transducers": synth["transducer_count"],
            "normal_force_mn": round(synth["estimated_normal_force_mn"], 2),
            "tactile_discernible": synth["tactile_discernible"],
            "model_status": synth["model_status"],
            "force_patch_side_mm": synth["force_patch_side_mm"],
            "spl_db": round(synth["spl_db"], 1),
            "sample_phases_8bit": synth["phases_8bit"][:8],
            "am_modulation_hz": synth["recommended_am_modulation_hz"],
        }

    elif name == "khora_plan_trajectory":
        q0 = float(arguments["q_start"])
        q1 = float(arguments["q_end"])
        v_max = float(arguments["v_max"])
        a_max = float(arguments["a_max"])
        j_max = float(arguments["j_max"])
        planner = SCurvePlanner(v_max, a_max, j_max)
        return planner.plan_point_to_point(q0, q1)

    elif name == "khora_safety_envelope_verify":
        q = arguments.get("joint_angles", [])
        chain = build_default_6dof_manipulator()
        if len(q) != chain.dof:
            return {"valid": False, "error": f"Expected {chain.dof} joints"}

        violations = []
        for i, (angle, joint) in enumerate(zip(q, chain.joints)):
            q_min, q_max = joint.limits
            if angle < q_min or angle > q_max:
                violations.append({
                    "joint": joint.name,
                    "index": i,
                    "value": angle,
                    "limits": [q_min, q_max]
                })

        J = chain.compute_jacobian(q)
        w = manipulability_index(J)
        return {
            "within_joint_limits": len(violations) == 0,
            "violations": violations,
            "manipulability_index": round(w, 6),
            "near_singularity": w < 1e-3,
            "status": "APPROVED" if len(violations) == 0 and w >= 1e-3 else "REJECTED",
        }

    else:
        raise ValueError(f"Unknown tool: {name}")


def main():
    """Stdio JSON-RPC loop for Model Context Protocol."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "khora-mcp", "version": "0.1.0"},
                    "capabilities": {"tools": {}}
                }
            }
        elif method == "tools/list":
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS}
            }
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})
            try:
                tool_result = handle_tool_call(name, args)
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(tool_result, indent=2)}
                        ]
                    }
                }
            except Exception as e:
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(e)}
                }
        else:
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method {method} not found"}
            }

        sys.stdout.write(json.dumps(res) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
