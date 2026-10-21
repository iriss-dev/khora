# KHORA — Comprehensive Legal Terms, Regulatory Compliance & Liability Disclaimers

> **Version:** 1.0.0 (Global Legal Shield)  
> **Effective Date:** October 20, 2026  
> **Governing Framework:** Delaware General Corporation Law, EU Directive 85/374/EEC, UK Consumer Rights & Product Safety Acts, OSHA 1910.95, IEC 60601-2-5, GDPR (EU 2016/679), CCPA/CPRA (Cal. Civ. Code § 1798.100).

---

## 1. Experimental Research Status & Physical Hardware Disclaimer

### 1.1 Academic and Experimental Prototype Only
All technical specifications, mathematical models, kinematic solvers, CAD designs (OpenSCAD/STL), electronic schematics (KiCad), optical substrate calculations, and firmware code within the **KHORA repository** (`https://github.com/iriss-dev/khora`) are provided strictly for **experimental academic, laboratory, and open-source scientific research purposes**. 

Nothing within this repository constitutes a certified consumer product, medical device, industrial automation guarantee, or commercial turnkey system.

### 1.2 Acoustic Wave & Ultrasonic Radiation Safety (OSHA & IEC Standards)
KHORA describes the generation of focused ultrasonic acoustic radiation pressure at frequencies around 40 kHz. Users and builders must adhere to the following mandatory physiological safety limits:
* **OSHA Standard 1910.95 (Occupational Noise Exposure)** and **IEC 60601-2-5**: Airborne ultrasound exceeding 140 dB SPL at close range or sub-harmonic audible frequencies (due to inter-modulation or transducer casing resonance) can cause hearing strain, nausea, or localized epidermal heating if improperly focused.
* **Maximum Permissible Radiation Force**: The beamforming phase array algorithms must never be modified to focus continuous wave energy exceeding **20 milinewtons (mN)** on unprotected human biological tissue.
* **Modulation Duty Cycle**: Acoustic stimulation must operate under pulsed or amplitude-modulated envelopes with duty cycles $\le 25\%$ and modulation frequencies restricted to the mechanoreceptor sensory bandwidth (150–250 Hz). Continuous uninterrupted wave exposure on human skin is strictly unauthorized.

### 1.3 High-Current Electrical & Thermal Hazard Disclaimers
The hardware architectures described herein utilize **24V DC power rails** driving high-speed MOSFET switching matrices (e.g., Microchip TC4427 or discrete H-bridges) with instantaneous peak current draws reaching 8 to 15 Amperes:
* High-frequency switching induces inductive voltage spikes ($V = L \frac{di}{dt}$) that can cause ceramic capacitor thermal runaway, gate dielectric breakdown, or PCB trace combustion if adequate decoupling and ground planes are omitted.
* Builders assume 100% personal responsibility for integrating emergency crowbar over-voltage protection, fuses, temperature sensors, and emergency mechanical power cut-off switches.
* The maintainers (including `iris` / `iriss-dev`) and project contributors shall have zero liability for property damage, fire, component destruction, or electrical injury resulting from the assembly, soldering, or operation of hardware based on these schematics.

### 1.4 Optical Substrate & High-Luminance Display Precautions
The Dihedral Corner Reflector Array (DCRA) optical assembly requires high-nit displays (typically 1,000 to 3,000 nits) recessed at 45.0° angles. Users are advised:
* Extended direct gaze into high-intensity un-diffused OLED/LCD backlights through the micro-mirror substrate must comply with international eye safety standard **IEC 62471 (Photobiological Safety of Lamps and Lamp Systems)**.
* Any laser diodes or collimated illumination sources integrated into experimental DCRA gantries must adhere to **ANSI Z136.1 Class 1/Class 2** restrictions. Class 3B or Class 4 lasers are strictly prohibited.

---

## 2. Patent Nominative Fair Use & Intellectual Property Declarations

### 2.1 Nominative Prior-Art Reference Only
This project makes technical, historical, and scientific reference to:
1. **AsukaNet Co., Ltd. (ASKA3D)**: References to US Patent 9,678,255 B2 ("Aerial Image Display Device") and related patents are made solely for academic context, nominative prior-art citation, and scientific comparison under the Doctrine of Nominative Fair Use (15 U.S.C. § 1125(c)(3)).
2. **University of Bristol / Ultraleap Ltd. (formerly Ultrahaptics)**: References to 40 kHz phased array acoustic radiation pressure patents are made exclusively to document the scientific history of acoustic levitation and tactile radiation pressure ($P_{rad} = \frac{2\langle I \rangle}{c}$).

### 2.2 Independent Clean-Room Implementation
All algorithms in this repository—including:
* Snell vector retro-reflection in the substrate normal plane ($v' = [-v_x, -v_y, v_z]^T$),
* Huygens-Fresnel constructive interference phase calculations ($\phi_i = -k \cdot d_i$),
* Buss-damped least squares (DLS) Jacobian singularity avoidance,
* 7-phase S-curve trajectory profiling,
—have been independently authored from first mathematical principles without the use, decompilation, or reverse-engineering of any proprietary binary firmware or trade secrets belonging to AsukaNet, Ultraleap, or any third party.

### 2.3 Territorial Patent Disclaimers
The publication of open-source equations and algorithms does not grant or imply patent indemnification in jurisdictions where specific apparatus claims may be enforced by third parties. **Community fabricators, researchers, and commercial entities are solely responsible for conducting independent patent clearance (Freedom-to-Operate / FTO analyses) in their respective national territories prior to physical commercialization.**

---

## 3. Absolute Disclaimer of Warranties (AS-IS)

TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW:
* THE KHORA SOURCE CODE, HARDWARE SCHEMATICS, CAD FILES, FIRMWARE, AND PLATFORM SERVICES ARE PROVIDED **"AS IS"** AND **"AS AVAILABLE"**, WITH ALL FAULTS AND DEFECTS, WITHOUT WARRANTY OF ANY KIND.
* THE MAINTAINERS AND CONTRIBUTORS EXPRESSLY DISCLAIM ALL WARRANTIES, WHETHER EXPRESS, IMPLIED, STATUTORY, OR OTHERWISE, INCLUDING, WITHOUT LIMITATION:
  1. WARRANTIES OF MERCHANTABILITY;
  2. FITNESS FOR A PARTICULAR PURPOSE;
  3. TITLE AND NON-INFRINGEMENT;
  4. WARRANTIES ARISING OUT OF COURSE OF DEALING, USAGE, OR TRADE PRACTICE;
  5. FREEDOM FROM PROGRAMMING BUGS, SINGULARITIES IN ROBOTIC KINEMATICS, OR HARDWARE INTERRUPT TIMING JITTER.

---

## 4. Maximum Limitation of Liability & Indemnification

### 4.1 Exclusion of Consequential and Incidental Damages
TO THE FULLEST EXTENT PERMITTED BY LAW (INCLUDING THE DELAWARE GENERAL CORPORATION LAW, THE LAWS OF ENGLAND AND WALES, AND THE EU PRODUCT LIABILITY DIRECTIVE 85/374/EEC):
* IN NO EVENT SHALL THE PROJECT MAINTAINER (`iris` / `iriss-dev`), CONTRIBUTORS, OR SPONSORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, PUNITIVE, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; BUSINESS INTERRUPTION; BODILY INJURY; PROPERTY DAMAGE; HEARING IMPAIRMENT; EYE STRAIN; OR ROBOTIC COLLISION DAMAGE) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF, REPRODUCTION OF, OR RELIANCE UPON THIS CODEBASE OR HARDWARE DESIGNS.

### 4.2 Absolute Cumulative Liability Cap
IN ANY EVENT, THE TOTAL AGGREGATE LIABILITY OF THE MAINTAINERS AND CONTRIBUTORS ARISING OUT OF OR RELATED TO THIS PROJECT, REGARDLESS OF THE FORUM AND REGARDLESS OF WHETHER ANY ACTION OR CLAIM IS BASED ON CONTRACT, TORT, OR OTHERWISE, SHALL BE STRICTLY LIMITED TO **$0.00 USD (ZERO UNITED STATES DOLLARS)**.

### 4.3 Mandatory User Indemnification
You agree to defend, indemnify, and hold harmless the project maintainers, developers, and affiliated contributors against any and all claims, liabilities, damages, losses, costs, and expenses (including reasonable attorney's fees) arising out of or in any way connected with:
* Your physical assembly, soldering, power provisioning, or laser/ultrasound activation;
* Your breach of regional regulatory or occupational safety standards;
* Your integration of robotic manipulators operating without redundant mechanical safety enclosures or certified e-stop circuits;
* Your infringement of any patent, trademark, trade secret, or copyright in your jurisdiction.

---

## 5. Zero-Leakage Privacy Policy & Data Architecture (GDPR / CCPA / CPRA)

### 5.1 Absolute Zero Data Collection Guarantee
KHORA operates under a strict **Zero-Telemetry, Local-First Privacy Architecture**:
1. **Zero Tracking Pixels or Analytical Beacons**: The platform contains no Google Analytics, no Meta Pixel, no Mixpanel, and no remote behavioral telemetry.
2. **Zero Third-Party CDN Data Leaks**: All scripts, fonts, styles, and vector assets are self-contained. No user IP addresses or browser fingerprints are transmitted to external cloud providers.
3. **Local-Only Credential & Session Storage**: User profiles, two-factor authentication (2FA) TOTP secrets, recovery keys, and workspace preferences are stored exclusively in client-side sandboxed `localStorage` / `sessionStorage`. No sensitive credentials are ever transmitted to an unauthenticated backend server.
4. **Encrypted In-Memory Token Handling**: Session tokens are held in client memory and isolated from cross-site scripting attack vectors via strict input sanitization.

### 5.2 GDPR (Regulation EU 2016/679) Compliance
For European Union residents:
* **Article 15 (Right of Access)**: All data stored by the platform is visible and inspectable directly in your browser's Local Storage inspector.
* **Article 17 (Right to Erasure / "Right to be Forgotten")**: The Settings "Danger Zone" provides a one-click irreversible data eradication button that instantly wipes all local profile records, session tokens, and discussion caches.
* **Article 20 (Right to Data Portability)**: Users can export their entire profile, 2FA keys, and saved discussions as an unencrypted JSON manifest at any time.

### 5.3 California Consumer Privacy Act (CCPA / CPRA)
* **Notice of Non-Sale**: We do not sell, rent, release, disclose, disseminate, make available, transfer, or otherwise communicate personal information to any third party for monetary or valuable consideration.
* **Right to Opt-Out**: Because zero telemetry is collected, no opt-out is required; your privacy is protected by default at the architectural level.

---

## 6. Client-Side Security Sandboxing & OWASP ASVS Level 3

### 6.1 Cross-Site Scripting (XSS) Prevention
* All user-submitted text (discussion titles, markdown bodies, comment trees) is sanitized using strict entity encoding before rendering into the DOM.
* Direct `innerHTML` evaluations of untrusted content are prohibited. Dynamic DOM updates utilize `textContent` or whitelisted tag parsers.

### 6.2 50-Millisecond Hardware Watchdog Interlock
To protect human operators interacting with floating holographic projections:
* RFC-0002 mandates that any robotic arm operating in co-presence with an optical DCRA volume must run a deterministic 50ms heartbeat watchdog.
* If communication between the spatial telemetry tracker (e.g. Leap Motion / stereo camera) and the robotic controller is interrupted for $\ge 50\text{ ms}$, joint velocities must decelerate along an emergency S-curve profile to a complete stop ($v = 0$).

---

## 7. Dual-Use & Export Administration Regulations (EAR)

This software and hardware documentation are published as publicly available open-source scientific research under **15 C.F.R. § 734.7 (Published Information)** of the United States Export Administration Regulations (EAR) and are not subject to the EAR.

However, builders residing in jurisdictions subject to the **Wassenaar Arrangement on Export Controls for Conventional Arms and Dual-Use Goods and Technologies** must verify that high-payload robotic manipulators or custom high-power piezoelectric phased arrays are not deployed in violation of Category 2 (Materials Processing) or Category 6 (Sensors and Lasers) restrictions.

---

## 8. Open-Source Licensing Compatibility

* **Codebase**: Licensed under the **MIT License**.
* **Hardware & Schematics**: Dual-licensed under the **CERN Open Hardware Licence Version 2 - Strongly Reciprocal (CERN-OHL-S-v2)** and the MIT License.
* **Specifications**: Licensed under **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

---
*For legal inquiries or security vulnerability reports, contact the maintainer team via cryptographic GPG-signed issues at `https://github.com/iriss-dev/khora/issues`.*
