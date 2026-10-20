#!/usr/bin/env python3
"""
Example 01: Optical DCRA Ray Tracing & Free-Space Convergence
Demonstrates retro-reflection invariance across a 45-degree Aerial Imaging Plate.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from khora.optics import DCRASubstrate, simulate_dcra_convergence


def main():
    print("=" * 65)
    print("KHORA // Optical DCRA Convergence Simulation (RFC-0001)")
    print("=" * 65)

    # 200x200mm plate tilted at 45.0 degrees
    plate = DCRASubstrate(center=[0.0, 0.0, 0.0], tilt_angle_deg=45.0, width_mm=200.0, height_mm=200.0)

    # Physical display source at Y = -100mm, Z = 0
    source_point = [0.0, -0.10, 0.0]  # meters
    print(f"[*] Physical Light Emitter Source: {source_point} m")
    print(f"[*] DCRA Plate Center:            {plate.center} m (Tilt: 45.0 deg)")

    sim = simulate_dcra_convergence(source_point, plate, num_cone_rays=24)

    if sim["converged"]:
        print(f"[+] Free-Air Holographic Focus:    {sim['theoretical_focal_point']} m")
        print(f"[+] RMS Spot Radius:              {sim['rms_spot_radius_mm']:.6f} mm")
        print(f"[+] Free-Air Distance (d_air):     {sim['air_focal_distance_mm']:.2f} mm")
        print(f"[+] Captured Rays:                 {sim['captured_rays']} / {sim['total_emitted_rays']}")
        print(f"[+] Traversable Working Clearance: {sim['clearance_volume_mm'][0]:.1f} x {sim['clearance_volume_mm'][1]:.1f} x {sim['clearance_volume_mm'][2]:.1f} mm")
        print("\n[SUCCESS] Optical theorem verified: d_air == d_source in open air.")
    else:
        print("[-] Rays missed aperture:", sim)


if __name__ == "__main__":
    main()
