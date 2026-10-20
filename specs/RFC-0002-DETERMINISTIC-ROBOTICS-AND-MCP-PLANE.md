# RFC-0002: Deterministic Robotics Kinematics and Model Context Protocol (MCP) Control Plane

- **Status**: Standard / Approved
- **Author**: iriss-dev <contact@iriss.dev>
- **Date**: 2026-10-20
- **Scope**: Deterministic decoupling of cognitive agents (LLM / MCP) from hard real-time robotic actuation.

---

## 1. Abstract

Large Language Models (LLMs) and autonomous AI agents exhibit probabilistic, non-deterministic latency and stochastic reasoning failures. Exposing raw motor pulses, joint angles, or pulse-width-modulation (PWM) outputs directly to an LLM or network API introduces catastrophic physical safety risks.

`KHORA` defines a strict **Three-Plane Architecture** that enforces mathematical determinism, jerk-bounded trajectory synthesis, and hardware-isolated safety interlocks between cognitive AI agents and physical manipulators.

```
┌─────────────────────────────────────────────────────────────┐
│  PLANE 1: COGNITIVE PLANE (Non-Deterministic, Async)        │
│  LLM Agent (Claude, GPT, Gemini) via Stdio MCP Server       │
│  Issues high-level intents: move_to_spatial_target(x, y, z) │
└──────────────────────────────┬──────────────────────────────┘
                               │ JSON-RPC 2.0 (Stdio / Unix Socket)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  PLANE 2: KINEMATIC SUPERVISORY PLANE (Deterministic Math)  │
│  - Inverse Kinematics (IK) via Damped Least Squares (DLS)   │
│  - Manipulability Index & Singularity Rejection: w > w_min  │
│  - 7-Phase S-Curve Trajectory Generation (Jerk-bounded)     │
│  - Workspace Envelope Clamping & Self-Collision Mesh Check  │
└──────────────────────────────┬──────────────────────────────┘
                               │ Deterministic Ring Buffer (250 Hz)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  PLANE 3: REAL-TIME HARDWARE EXECUTION (Bare-Metal / RTOS)  │
│  - Hardware Timer Interrupts (STM32 / RP2040 / FreeRTOS)   │
│  - Closed-loop FOC Current Control & CAN / Step-Dir Bus     │
│  - Independent Hardware Watchdog (50ms timeout)             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Plane 2: Kinematic Supervisory Math

### 2.1 Inverse Kinematics with Damped Least Squares (DLS)
Given a target spatial velocity vector $\dot{\vec{x}} \in \mathbb{R}^6$ in Cartesian space:

$$\dot{\vec{q}} = J^T \left( J J^T + \lambda^2 I \right)^{-1} \dot{\vec{x}}$$

Where:
- $J(\vec{q})$ is the $6 \times N$ manipulator Jacobian matrix evaluated at current joint vector $\vec{q}$.
- $\lambda \ge 0$ is the dynamic damping factor calculated from the manipulability measure:

$$w(\vec{q}) = \sqrt{\det(J(\vec{q}) J^T(\vec{q}))}$$

If $w(\vec{q}) < w_{threshold}$, damping $\lambda$ increases smoothly to guarantee joint velocities $\|\dot{\vec{q}}\|_\infty \le \dot{q}_{max}$, preventing joint runaway near kinematic singularities.

### 2.2 S-Curve (7-Segment) Jerk-Limited Trajectory Profile
To prevent physical resonance and mechanical fatigue, all point-to-point transitions execute 7-segment trajectory profiles bounding jerk, acceleration, and velocity:

$$|j(t)| \le j_{max}, \quad |a(t)| \le a_{max}, \quad |v(t)| \le v_{max}$$

Segment breakdown:
1. $t \in [0, t_1]$: Constant positive jerk $+j_{max}$ (acceleration increases linearly to $a_{max}$)
2. $t \in [t_1, t_2]$: Zero jerk (constant acceleration $a_{max}$)
3. $t \in [t_2, t_3]$: Constant negative jerk $-j_{max}$ (acceleration decreases to zero as velocity approaches $v_{max}$)
4. $t \in [t_3, t_4]$: Zero jerk, zero acceleration (constant cruise velocity $v_{max}$)
5. $t \in [t_4, t_5]$: Constant negative jerk $-j_{max}$ (deceleration ramps to $-a_{max}$)
6. $t \in [t_5, t_6]$: Zero jerk (constant deceleration $-a_{max}$)
7. $t \in [t_6, t_7]$: Constant positive jerk $+j_{max}$ (deceleration ramps to zero at target setpoint)

---

## 3. Plane 3: Hardware Interlocks & Watchdog Policy

1. **Watchdog Heartbeat**:
   The Supervisory Plane must feed the Hardware Plane a monotonically increasing sequence counter every $10\,\text{ms}$. If no valid frame arrives within $50\,\text{ms}$, the hardware watchdog trips and initiates emergency deceleration (controlled braking) using stored inertial kinetic energy.
2. **Current Limiting**:
   Each actuator driver monitors shunt resistor voltage. If $I_{phase} > I_{peak}$ for $> 3\,\text{ms}$, hardware crowbar disconnects the H-bridge gate drivers independently of software.
3. **Envelope Enclosure**:
   Joint coordinates outside physical hardstops $(\theta_i < \theta_{min} \lor \theta_i > \theta_{max})$ trigger an immediate non-maskable interrupt (NMI).

---

## 4. Model Context Protocol (MCP) Interface Specification

The cognitive layer communicates exclusively through the standard Model Context Protocol. The agent has visibility into state and kinematics, but cannot bypass Plane 2 validations.

### 4.1 Exposed Tools

#### `khora_kinematic_solve_ik`
- Input: Target Cartesian pose `[x, y, z, roll, pitch, yaw]`, current joint configuration `q`.
- Output: Validated joint angles `q_target`, manipulability score `w`, singularity danger flag.

#### `khora_plan_trajectory`
- Input: `q_start`, `q_end`, `max_velocity`, `max_acceleration`.
- Output: 7-segment timestamped trajectory table with bounded jerk.

#### `khora_safety_envelope_verify`
- Input: Proposed trajectory path.
- Output: Pass/Fail with collision margin ($\text{mm}$) and thermal dissipation estimate.

#### `khora_compute_haptic_focal_plane`
- Input: 3D point $(x, y, z)$ relative to the optical baseline.
- Output: 40 kHz transducer phase array register values and estimated acoustic force ($\text{mN}$).
