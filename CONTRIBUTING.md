# Contributing to KHORA

Thank you for your interest in contributing to **KHORA**, the open-source platform for traversable spatial computing, Dihedral Corner Reflector Array (DCRA) optics, and airborne ultrasonic radiation force haptics.

We welcome contributions from optical engineers, acoustic physicists, roboticists, embedded systems developers, and spatial computing researchers.

---

## 1. Code of Conduct & Open Science Principles

KHORA is dedicated to open, reproducible engineering:
- **Zero Proprietary Paywalls**: All core algorithms, ray tracing models, and transducer beamforming mathematics remain free and open under the MIT License.
- **Physical Reproducibility**: Theoretical claims must be supported by mathematical derivations, simulation scripts, or physical laboratory benchmarks.
- **Acoustic Safety Compliance**: Any code modifying transducer drive power must adhere to OSHA 1910.95 and IEC 60601-2-5 acoustic safety interlocks (50ms watchdog envelope).

---

## 2. Repository Architecture

```
khora/
├── python/khora/
│   ├── optics.py         # Analytical DCRA ray tracing and Snell retro-reflection
│   ├── haptics.py        # 40 kHz phased array beamforming & Langevin radiation pressure
│   ├── kinematics.py     # Deterministic SE(3) Lie algebra forward/inverse kinematics
│   ├── telemetry.py      # Watchdog interlocks, FIFO metrics, and health monitors
│   └── mcp_server.py     # Model Context Protocol (MCP) server for robotic control
├── crates/khora-core/    # High-performance Rust engine for real-time microsecond loops
├── cad/                  # OpenSCAD parametric mechanical mounts (DCRA, ultrasonic array)
├── platform/             # WebGL / HTML5 spatial workbench & interactive simulator
├── specs/                # Formal RFC architectural specifications (RFC-0001, RFC-0002)
├── tests/                # Automated unit and physical parameter test suites
└── docs/                 # Optical assembly, hardware BOM, and compliance references
```

---

## 3. Development Workflow

### 3.1 Environment Setup
KHORA requires Python 3.10+ (no heavy third-party runtime dependencies for core algorithms).

```bash
# Clone the repository
git clone https://github.com/iriss-dev/khora.git
cd khora

# Run test suite to verify physical invariants
python -m unittest discover tests
```

### 3.2 Running the Interactive Spatial Workbench
Open `platform/index.html` in any modern web browser supporting HTML5 Canvas and Web Audio:
```bash
# Direct local launch
start platform/index.html
```

---

## 4. How to Contribute

### 4.1 Submitting an RFC (Request for Comments)
For major architectural changes or novel physical transducers:
1. Review existing RFCs in `specs/`.
2. Draft a markdown proposal following the structure of `specs/RFC-0001-SPATIAL-LIGHT-AND-HAPTICS.md`.
3. Submit a Pull Request with the label `rfc`.

### 4.2 Code Conventions
- **Python**: PEP 8 style, strict type hints (`typing.List`, `Tuple`, `Optional`), docstrings with SI units (meters, Pascals, millinewtons).
- **Rust**: `cargo fmt` and `cargo clippy` clean, `no_std` compatible where applicable.
- **OpenSCAD**: Parametric variables exposed at the head of every `.scad` file.
- **HTML/JS**: Strict security policy compliance (zero third-party telemetry, zero external trackers).

### 4.3 Testing Requirements
Every pull request must maintain or increase test coverage. Run:
```bash
python -m unittest discover tests -v
```
All 18+ mathematical invariants (DCRA 1:1 parity, acoustic beamforming convergence, SE(3) matrix inverses) must pass before merging.

---

## 5. Licensing

By contributing to KHORA, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
