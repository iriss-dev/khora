#!/usr/bin/env python3
"""
Example 02: 40 kHz Ultrasonic Phased Array Beamforming & Radiation Pressure
Synthesizes 8-bit timer registers for an RP2040/STM32 MCU to focus 10 mN force.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from khora.haptics import AcousticPhasedArray


def main():
    print("=" * 65)
    print("KHORA // Mid-Air Acoustic Haptic Phase Synthesis (RFC-0001)")
    print("=" * 65)

    # 16x16 Transducer grid (256 transducers, 10mm pitch)
    array = AcousticPhasedArray(grid_rows=16, grid_cols=16, pitch_mm=10.0, center_m=[0.0, 0.0, -0.05])
    focal_target = [0.0, 0.0, 0.12]  # 12cm above table in open air

    print(f"[*] Transducer Array: 16x16 ({array.total_transducers} channels) @ 40 kHz")
    print(f"[*] Synthesizing Focus at: {focal_target} m")

    res = array.synthesize_focus(focal_target)

    print(f"[+] Peak Acoustic Pressure:     {res['peak_pressure_pa']:.1f} Pa")
    print(f"[+] Root-Mean-Square Pressure:  {res['rms_pressure_pa']:.1f} Pa")
    print(f"[+] Sound Pressure Level:       {res['spl_db']:.1f} dB SPL")
    print(f"[+] Radiation Pressure:         {res['radiation_pressure_pa']:.2f} Pa")
    print(f"[+] Estimated Normal Force:     {res['estimated_normal_force_mn']:.2f} mN")
    print(f"[+] Tactile Sensation:          {'DISCERNIBLE TOUCH FEELING' if res['tactile_discernible'] else 'SUB-THRESHOLD'}")
    print(f"[+] Modulation Carrier:         {res['recommended_am_modulation_hz']} Hz AM (Pacinian optimal)")

    print("\n[*] First 16 Transducer Timer Registers [0 - 255]:")
    print("    " + ", ".join(f"0x{b:02X}" for b in res["phases_8bit"][:16]))
    print("[SUCCESS] Phase delays ready for DMA transmission to hardware drivers.")


if __name__ == "__main__":
    main()
