import cmath
import math
import os
import sys
import unittest
import json
import shutil
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'python')))
from khora.acoustic_field import (piston_directivity, pressure_phasor,
    radiation_pressure, integrate_patch_force, rayleigh_piston_pressure)
from khora.haptics import AcousticPhasedArray, compute_beamforming_phases, acoustic_wavenumber
from khora.haptics import speed_of_sound_at_temp
from khora.optics import DCRASubstrate, simulate_dcra_convergence


class TestAcousticField(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js required for cross-language field comparison')
    def test_python_browser_phase_and_pressure_parity(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        output = subprocess.check_output(['node', '-e',
            "const A=require('./platform/acoustic-field.js');const f=[.013,-.009,.14];"
            "const d=A.synthesize(f);console.log(JSON.stringify({phases:[...d.phases],rms:A.pressure(f,d).rms}));"],
            cwd=root, text=True)
        browser = json.loads(output)
        array = AcousticPhasedArray(center_m=[0,0,0])
        _, phases = compute_beamforming_phases([.013,-.009,.14], array.elements)
        self.assertEqual(phases, browser['phases'])
        rms = abs(pressure_phasor([.013,-.009,.14],array.elements,
            [q*2*math.pi/256 for q in phases],sound_speed=speed_of_sound_at_temp(20))) / math.sqrt(2)
        self.assertAlmostEqual(rms,browser['rms'],places=8)

    def test_piston_axis_and_first_null(self):
        self.assertEqual(piston_directivity(0), 1)
        self.assertAlmostEqual(piston_directivity(3.8317059702), 0, places=10)
        self.assertLess(piston_directivity(5), 0)  # preserve phase sign of sidelobes

    def test_quantization_circular_error(self):
        # Crosses the wrap boundary repeatedly; 255-step quantization fails this bound.
        elements = [[i / 12345, 0, 0] for i in range(256)]
        phases, quantized = compute_beamforming_phases([0, 0, .14], elements)
        for phase, byte in zip(phases, quantized):
            error = (byte * 2 * math.pi / 256 - phase + math.pi) % (2 * math.pi) - math.pi
            self.assertLessEqual(abs(error), math.pi / 256 + 1e-12)

    def test_reflector_absorber_and_quadratic_scaling(self):
        self.assertAlmostEqual(radiation_pressure(1000), 2 * radiation_pressure(1000, reflection_power=0))
        self.assertAlmostEqual(radiation_pressure(2000), 4 * radiation_pressure(1000))

    def test_interference_null(self):
        elements = [[-.01, 0, 0], [.01, 0, 0]]
        self.assertLess(abs(pressure_phasor([0, 0, .1], elements, [0, math.pi])), 1e-10)

    def test_rayleigh_matches_axial_disk_solution(self):
        z, a, c, f, rho, v = .04, .005, 343, 40000, 1.204, .01
        k = 2 * math.pi * f / c
        exact = rho*c*v*(cmath.exp(1j*k*z)-cmath.exp(1j*k*math.sqrt(z*z+a*a)))
        numerical = rayleigh_piston_pressure([0,0,z], radial_samples=64)
        self.assertLess(abs(numerical-exact)/abs(exact), 1e-6)

    def test_far_field_matches_rayleigh_magnitude(self):
        # On-axis asymptote; omitted global -i phase cancels in relative beamforming.
        rho, c, f, a, v = 1.204, 343, 40000, .005, .01
        source = rho * (2*math.pi*f) * a*a * v / 2
        approximate = pressure_phasor([0,0,.2], [[0,0,0]], [0], peak_pa_at_1m=source)
        reference = rayleigh_piston_pressure([0,0,.2])
        self.assertLess(abs(abs(reference)-abs(approximate))/abs(reference), .001)

    def test_force_integral_convergence_and_scaling(self):
        array = AcousticPhasedArray(8,8,center_m=[0,0,0])
        focus = [0,0,.14]
        phases, _ = compute_beamforming_phases(focus,array.elements)
        a = integrate_patch_force(focus,array.elements,phases,samples=8)
        b = integrate_patch_force(focus,array.elements,phases,samples=16)
        doubled = integrate_patch_force(focus,array.elements,phases,samples=16,peak_pa_at_1m=2)
        self.assertLess(abs(a-b)/b, .005)
        self.assertAlmostEqual(doubled,4*b)

    def test_invalid_inputs(self):
        for frequency in [0,-1,float('nan'),float('inf')]:
            with self.assertRaises(ValueError): acoustic_wavenumber(frequency)
        with self.assertRaises(ValueError): pressure_phasor([0,0,0],[[0,0,0]],[0])
        with self.assertRaises(ValueError): radiation_pressure(100,reflection_power=2)
        with self.assertRaises(ValueError): compute_beamforming_phases([float('nan'),0,.1],[[0,0,0]])

    def test_rigid_dcra_tilt_does_not_create_astigmatism(self):
        for tilt in [30,44.8,45,45.2,60]:
            result=simulate_dcra_convergence([0,-.08,0], DCRASubstrate(
                tilt_angle_deg=tilt,width_mm=300,height_mm=300),num_cone_rays=24)
            self.assertTrue(result['converged'])
            self.assertLess(result['rms_spot_radius_mm'],1e-10)


if __name__ == '__main__': unittest.main()
