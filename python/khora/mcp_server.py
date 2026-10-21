"""
Model Context Protocol (MCP) Server for KHORA.
Connects non-deterministic AI agents (Claude, GPT, Gemini) to deterministic kinematics,
optical aerial simulations, and ultrasound mid-air haptic synthesis via Stdio JSON-RPC 2.0.
"""

import sys
import json
import math
import argparse
from typing import Dict, Any, List

from .kinematics import (
    KinematicChain, Joint, solve_ik_dls, SCurvePlanner, manipulability_index
)
from .optics import DCRASubstrate, simulate_dcra_convergence
from .haptics import AcousticPhasedArray
from .robot import plan_move, forward_poe
from .hardware import PicoClient, SimulatedPico
from . import __version__


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

TOOLS += [
    {"name": "khora_robot_plan_move", "description": "Plan a reference 6R arm move using DLS and synchronized quintic interpolation. Simulation only; does not enable motors or check collisions.",
     "inputSchema": {"type": "object", "properties": {"target_m": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3}, "start_joints_rad": {"type": "array", "items": {"type": "number"}, "minItems": 6, "maxItems": 6}}, "required": ["target_m"]}},
    {"name": "khora_robot_forward_poe", "description": "Compute the reference arm's SE(3) pose using a product of screw exponentials. No hardware writes.",
     "inputSchema": {"type": "object", "properties": {"joints_rad": {"type": "array", "items": {"type": "number"}, "minItems": 6, "maxItems": 6}}, "required": ["joints_rad"]}},
    {"name": "khora_hardware_status", "description": "Read the explicitly configured Pico connection, firmware capabilities and fault state. Does not enable outputs.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "khora_hardware_stage_focus", "description": "Stage 16 phases for the 4x4, 16 mm pitch Pico array with outputs disabled. Requires --simulate-device or an explicitly configured serial port. No ARM tool is exposed.",
     "inputSchema": {"type": "object", "properties": {"focal_point_m": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3}}, "required": ["focal_point_m"]}}
]
for tool in TOOLS:
    tool['inputSchema']['additionalProperties'] = False
    tool['annotations'] = {'readOnlyHint': tool['name'] != 'khora_hardware_stage_focus', 'destructiveHint': False}
    for key, schema in tool['inputSchema']['properties'].items():
        if schema['type'] == 'array':
            schema['minItems'] = schema['maxItems'] = 6 if key in ('q_init', 'joint_angles', 'joints_rad', 'start_joints_rad') else 3
        if key == 'grid_size':
            schema.update(minimum=1, maximum=32)
        if key in ('v_max', 'a_max', 'j_max'):
            schema.update(exclusiveMinimum=0, maximum=100)

_hardware = None


def validate_arguments(name, arguments):
    tool = next((tool for tool in TOOLS if tool['name'] == name), None)
    if tool is None:
        raise ValueError(f'Unknown tool: {name}')
    if not isinstance(arguments, dict):
        raise ValueError('Tool arguments must be an object')
    schema = tool['inputSchema']
    if set(arguments) - set(schema['properties']):
        raise ValueError('Unexpected tool argument')
    for key in schema.get('required', []):
        if key not in arguments:
            raise ValueError(f'Missing argument: {key}')
    for key, value in arguments.items():
        item = schema['properties'][key]
        if item['type'] == 'array':
            if not isinstance(value, list) or len(value) != item['minItems']:
                raise ValueError(f'{key} must contain {item["minItems"]} numbers')
            numbers = value
        else:
            numbers = [value]
            if item['type'] == 'integer' and type(value) is not int:
                raise ValueError(f'{key} must be an integer')
        if any(isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) for number in numbers):
            raise ValueError(f'{key} must contain finite numbers')
        if 'minimum' in item and value < item['minimum'] or 'maximum' in item and value > item['maximum'] or 'exclusiveMinimum' in item and value <= item['exclusiveMinimum']:
            raise ValueError(f'{key} is outside the allowed range')


def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    validate_arguments(name, arguments)
    if name == 'khora_robot_plan_move':
        return plan_move(**arguments)
    if name == 'khora_robot_forward_poe':
        return {'frame': 'metres, robot base', 'transform': forward_poe(arguments['joints_rad'])}
    if name == 'khora_hardware_status':
        return _hardware.status() if _hardware else {'connected': False, 'reason': 'No serial port or simulator configured'}
    if name == 'khora_hardware_stage_focus':
        if _hardware is None:
            raise ValueError('Configure --simulate-device or --port before staging phases')
        status = _hardware.status()
        if status.get('armed'):
            raise ValueError('MCP phase staging is allowed only with outputs disabled')
        return _hardware.stage_focus(arguments['focal_point_m'])
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
    global _hardware
    parser = argparse.ArgumentParser(description="KHORA MCP stdio server")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--port', help='Explicit local Pico serial device')
    group.add_argument('--simulate-device', action='store_true')
    args = parser.parse_args()
    if args.port:
        _hardware = PicoClient.open(args.port)
    elif args.simulate_device:
        _hardware = PicoClient(SimulatedPico())
        _hardware.connect()
    initialized = False
    ready = False
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            req_id = None
            try:
                if len(line) > 1048576:
                    raise ValueError('Message exceeds 1 MiB')
                req = json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON number')))
                if not isinstance(req, dict) or req.get('jsonrpc') != '2.0' or not isinstance(req.get('method'), str):
                    raise ValueError('Invalid JSON-RPC request')
                req_id = req.get('id')
                method = req['method']
                params = req.get('params', {})
                if req_id is not None and (isinstance(req_id, bool) or not isinstance(req_id, (str, int))):
                    raise ValueError('Invalid request ID')
                if not isinstance(params, dict):
                    raise ValueError('Parameters must be an object')
                if 'id' not in req:
                    if method == 'notifications/initialized' and initialized:
                        ready = True
                    continue
                if method == 'initialize':
                    if initialized:
                        raise ValueError('Session already initialized')
                    requested = params.get('protocolVersion')
                    if not isinstance(requested, str):
                        raise ValueError('protocolVersion is required')
                    version = requested if requested in ('2024-11-05', '2025-03-26', '2025-06-18') else '2025-06-18'
                    result = {'protocolVersion': version, 'serverInfo': {'name': 'khora-mcp', 'version': __version__},
                              'capabilities': {'tools': {}}, 'instructions': 'Plans are simulations. Hardware staging does not enable outputs. No ARM or motor execution tool is exposed.'}
                    initialized = True
                elif method == 'ping':
                    result = {}
                elif not ready:
                    raise ValueError('Initialize and send notifications/initialized first')
                elif method == 'tools/list':
                    result = {'tools': TOOLS}
                elif method == 'tools/call':
                    try:
                        output = handle_tool_call(params.get('name'), params.get('arguments', {}))
                        result = {'content': [{'type': 'text', 'text': json.dumps(output, allow_nan=False)}], 'isError': False}
                    except (ValueError, RuntimeError, TimeoutError, OSError) as error:
                        result = {'content': [{'type': 'text', 'text': str(error)}], 'isError': True}
                else:
                    response = {'jsonrpc': '2.0', 'id': req_id, 'error': {'code': -32601, 'message': 'Method not found'}}
                    sys.stdout.write(json.dumps(response)+'\n')
                    sys.stdout.flush()
                    continue
                response = {'jsonrpc': '2.0', 'id': req_id, 'result': result}
            except (ValueError, TypeError, KeyError) as error:
                response = {'jsonrpc': '2.0', 'id': req_id, 'error': {'code': -32700 if isinstance(error, json.JSONDecodeError) else -32600, 'message': str(error)}}
            sys.stdout.write(json.dumps(response, allow_nan=False)+'\n')
            sys.stdout.flush()
    finally:
        if _hardware:
            try:
                _hardware.stop()
            finally:
                _hardware.close()


if __name__ == '__main__':
    main()
