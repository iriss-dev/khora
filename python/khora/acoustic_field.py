"""Linear baffled-piston field model; SI units and peak-pressure phasors.

Convention: Re{p exp(-i omega t)}, outgoing exp(+i k r). The real-time
model uses element far-field directivity, retaining spherical array paths.
It excludes scattering, absorption, nonlinear propagation and transducer coupling.
"""

import cmath
import math


def piston_directivity(argument: float) -> float:
    """2 J1(x)/x using its convergent series; supported range |x| <= 8."""
    if not math.isfinite(argument) or abs(argument) > 8:
        raise ValueError("Piston directivity requires finite |ka sin(theta)| <= 8")
    term = total = 1.0
    for m in range(1, 32):
        term *= -(argument * argument / 4) / (m * (m + 1))
        total += term
    return total


def pressure_phasor(point, elements, phases, *, frequency=40000.0,
                    sound_speed=343.0, radius_m=0.005,
                    peak_pa_at_1m=1.0, weights=None):
    """Sum circular pistons facing +Z; source strength is peak Pa at 1 m.

    The 20 mm exclusion zone avoids presenting the element far-field
    approximation as a solution on the radiating surface.
    """
    if (len(point) != 3 or not all(math.isfinite(v) for v in point)
            or not all(math.isfinite(v) and v > 0 for v in
                       (frequency, sound_speed, radius_m))
            or not math.isfinite(peak_pa_at_1m) or peak_pa_at_1m < 0):
        raise ValueError("Invalid field parameters")
    if len(elements) != len(phases) or (weights is not None and len(weights) != len(elements)):
        raise ValueError("Element, phase and weight counts must match")
    k = 2 * math.pi * frequency / sound_speed
    if k * radius_m > 8:
        raise ValueError("Piston ka exceeds supported range")
    result = 0j
    for i, (element, phase) in enumerate(zip(elements, phases)):
        if len(element) != 3 or not all(math.isfinite(v) for v in element) or not math.isfinite(phase):
            raise ValueError("Invalid element or phase")
        weight = 1.0 if weights is None else weights[i]
        if not math.isfinite(weight) or not 0 <= weight <= 1:
            raise ValueError("Weights must be in [0, 1]")
        delta = [point[j] - element[j] for j in range(3)]
        if delta[2] < 0.02:
            raise ValueError("Field samples must be at least 20 mm above every piston")
        distance = math.sqrt(sum(v * v for v in delta))
        directivity = piston_directivity(k * radius_m * math.hypot(*delta[:2]) / distance)
        result += (peak_pa_at_1m * weight * directivity / distance
                   * cmath.exp(1j * (k * distance + phase)))
    return result


def radiation_pressure(rms_pa, *, reflection_power=1.0, density=1.204, sound_speed=343.0):
    """Normal-incidence plane-wave estimate, opaque surface: (1+R) I/c.

    R is reflected acoustic POWER fraction (0 absorbing, 1 reflecting).
    This boundary approximation is not a full skin or standing-wave model.
    """
    if (not all(math.isfinite(v) for v in (rms_pa, reflection_power, density, sound_speed))
            or rms_pa < 0 or not 0 <= reflection_power <= 1 or density <= 0 or sound_speed <= 0):
        raise ValueError("Invalid radiation-pressure parameters")
    return (1 + reflection_power) * rms_pa**2 / (density * sound_speed**2)


def integrate_patch_force(center, elements, phases, *, side_m=0.01, samples=16,
                          reflection_power=1.0, density=1.204, **field_options):
    """Midpoint integral over an XY square patch, returned in mN.

    Assumes locally normal incidence on an opaque flat patch. Increasing samples
    should be used to check convergence; a point value times lambda² is not used.
    """
    if not math.isfinite(side_m) or side_m <= 0 or not isinstance(samples, int) or samples < 1:
        raise ValueError("Invalid integration grid")
    step = side_m / samples
    total = 0.0
    for row in range(samples):
        for col in range(samples):
            point = [center[0] + (col + 0.5 - samples / 2) * step,
                     center[1] + (row + 0.5 - samples / 2) * step, center[2]]
            rms = abs(pressure_phasor(point, elements, phases, **field_options)) / math.sqrt(2)
            total += radiation_pressure(rms, reflection_power=reflection_power,
                                        density=density, sound_speed=field_options.get("sound_speed", 343.0))
    return total * step**2 * 1000


def rayleigh_piston_pressure(point, *, radius_m=0.005, velocity_peak_m_s=0.01,
                            frequency=40000.0, sound_speed=343.0, density=1.204,
                            radial_samples=24, angular_samples=64):
    """Reference Rayleigh integral on a uniformly vibrating disk in a rigid baffle.

    p = -i rho omega/(2 pi) integral_S v exp(i k R)/R dS.
    Equal-area radial midpoint quadrature avoids a singular r=0 weight.
    Slower than the directivity model; intended for convergence checks.
    """
    if (len(point) != 3 or not all(math.isfinite(v) for v in point) or point[2] <= 0
            or not all(math.isfinite(v) and v > 0 for v in
                       (radius_m, frequency, sound_speed, density))
            or not math.isfinite(velocity_peak_m_s) or velocity_peak_m_s < 0
            or not isinstance(radial_samples, int) or radial_samples < 1
            or not isinstance(angular_samples, int) or angular_samples < 1):
        raise ValueError("Invalid Rayleigh integration parameters")
    omega = 2 * math.pi * frequency
    total = 0j
    for radial in range(radial_samples):
        r = radius_m * math.sqrt((radial + 0.5) / radial_samples)
        for angular in range(angular_samples):
            angle = 2 * math.pi * (angular + 0.5) / angular_samples
            distance = math.sqrt((point[0] - r * math.cos(angle))**2
                                 + (point[1] - r * math.sin(angle))**2 + point[2]**2)
            total += cmath.exp(1j * omega / sound_speed * distance) / distance
    area = math.pi * radius_m**2 / (radial_samples * angular_samples)
    return -1j * density * omega / (2 * math.pi) * velocity_peak_m_s * total * area
