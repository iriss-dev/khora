# AI, robotics and Feetech control

The [robotics demo](https://iriss-dev.github.io/khora/platform/robot.html) provides positional inverse kinematics for a reference six-joint arm, simulated trajectory playback, JSON export/import and a tool-request inspector. It does not command motors from the public website.

## MCP connection

Python 3.10+:

```sh
pip install -e .
khora-mcp --simulate-device
```

Configure an MCP client to start that command as a **stdio server**. This is a server process, not an interactive terminal chat. A portable alternative is `python /absolute/path/to/khora/tools/run_mcp.py --simulate-device`; see [the configuration example](../examples/mcp-client.json). Replace the placeholder with the actual checkout path and an interpreter available to the client.

The server negotiates supported protocol versions, waits for `notifications/initialized`, handles `ping`, returns tool schemas and emits no replies to notifications. Inputs reject non-finite numbers, wrong vector lengths, unknown fields and oversized grid dimensions. Tool execution failures use MCP's `isError` content result. No ARM or motor execution tool is exposed to the AI.

| Tool | Result |
| --- | --- |
| `khora_robot_plan_move` | Reference-arm trajectory, 101 samples and numerical error |
| `khora_robot_forward_poe` | SE(3) forward pose from screw exponentials |
| `khora_hardware_status` | Configured device/simulator status |
| `khora_hardware_stage_focus` | 16 phases staged with outputs disabled |
| `khora_kinematic_solve_ik` | Existing DLS solver for the reference arm |
| `khora_simulate_aerial_ray_trace` | Ideal optical model |
| `khora_compute_haptic_focal_plane` | Acoustic model summary |
| `khora_plan_trajectory` | Legacy scalar S-curve timing summary |
| `khora_safety_envelope_verify` | Joint-limit and numerical singularity checks |

Ask the client to call `khora_robot_plan_move` with `{"target_m":[0.25,0.15,0.55]}`. Save the returned JSON as a file and select **Load MCP plan** in the browser demo. The importer checks the reference model, finite joint values, joint limits, quintic sample consistency, duration and endpoint. The tool-request text box accepts the same structured request; it does not contain a language model or send prompts to an external provider.

For a real Pico, install `pip install -e '.[hardware]'` and start the server with `--port COM4` or `--port /dev/ttyACM0`. The port is explicit; the server does not open every attached device. MCP refuses phase staging if it observes an armed output. Do not run an independent manual arming client against the same serial session.

The lifecycle follows the [MCP stdio lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle). It supports 2024-11-05, 2025-03-26 and 2025-06-18 and negotiates the last of these when a different version is requested.

## Numerical arm model

The Python module `khora.robot` derives the reference arm's pose using a product of exponentials about spatial screw axes. Tests compare it with the existing serial transform chain at random joint configurations. Positional DLS finds the target; orientation is not constrained.

A shared-duration quintic interpolation `s(u)=10u³−15u⁴+6u⁵` has zero endpoint velocity and acceleration. The duration uses the exact normalized maxima 1.875 for velocity, 10/√3 for acceleration and 60 for jerk. Default limits are 0.8 rad/s, 1.5 rad/s² and 8 rad/s³. Samples are numerical plans, not hard-real-time setpoints or servo feedback. The legacy scalar S-curve helper is separate from this sampled planner.

Joint limits do not establish collision clearance, dynamic feasibility, singularity robustness throughout a path or gravity-load handling. The reference link lengths are not the dimensions of the user's physical arm. Replace the model and verify it from measurements before producing hardware setpoints.

## Feetech STS3215

The Python driver implements STS3215 little-endian packets, position sync-write, torque enable/disable and telemetry decoding through the Pico's guarded UART. Each joint needs an explicit servo ID, measured zero, direction and min/max tick calibration. The host rejects values outside calibration and the MCU enforces a second fixed envelope. No calibration is silently inferred from an AI plan.

```python
from khora.hardware import PicoClient
from khora.servos import JointCalibration, ServoSupervisor

client = PicoClient.open("COM4")
client.stage_focus([0, 0, .14])  # Required staging step; acoustic gate remains off.
# The physical stop loop must be closed and the board's ARM button held.
client.arm(output="servos")
# Supply values measured for your mechanism, not these example numbers.
calibration = [JointCalibration(1, 2048, 1, 1500, 2500)]
controller = ServoSupervisor(client, calibration)
try:
    controller.start_monitor()
    controller.enable_torque()
    # Stream fresh calibrated commands within the 50 ms host lease.
    # This single command is only a packet example, not a complete move.
    controller.submit([0.0], speed_raw=400)
finally:
    controller.close()
```

`ServoSupervisor` latches a host fault at 50 ms without a fresh command. A background monitor can enforce it while Python is scheduled. The Pico independently enforces 50 ms since its last valid heartbeat, including host stalls. These are different clocks/deadlines; Python does not establish a hard 50 ms physical stopping bound. Unexpected packet failure closes the transport and the MCU lease remains responsible for independent gate disable.

`sample_feedback` checks packet/register error flags and configurable temperature/load thresholds, stopping the session on an error. Current load is a signed raw control register, **not calibrated torque or force**. Speed units depend on the servo's phase/configuration setting; `speed_raw` is deliberately not labelled radians/s or ticks/s. Collision detection from load alone is not validated. No EEPROM, mode or ID writes are performed. Dynamixel XL430 is not packet-compatible and is not implemented.

References: [Waveshare servo packet protocol](https://docs.waveshare.com/Servo_Communication_Protocol), [ST memory table](https://docs.waveshare.com/Memory_Map_Explanation/ST_Servo_Memory_Map_Explanation), [pySerial API](https://pyserial.readthedocs.io/en/latest/pyserial_api.html), and [Pico wiring/interlocks](PICO_HARDWARE.md).
