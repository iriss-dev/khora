# Pico / RP2040 hardware profile

KHORA v0.3 adds a standalone C++ firmware target for a Raspberry Pi Pico, a 4 × 4 array of 16 emitters at 16 mm pitch, and a Feetech STS3215 TTL bus. The 256-element browser study remains a separate model.

The firmware builds against Pico SDK 2.2.0. Compilation and portable state-machine tests have passed in CI; electrical timing, power interruption, acoustic output, real servos and tracking hardware have not been measured on this development host. No board is flashed automatically.

## Connections

| Pico GPIO | Function |
| --- | --- |
| 0–15 | Channel 0–15 logic inputs, row-major 4 × 4 order |
| 16 | External acoustic supply gate, active high, external pull-down required |
| 17 | Normally closed stop-loop contact to GND, internal pull-up; open circuit trips |
| 18 | Momentary physical ARM button to GND, internal pull-up |
| 20 | UART1 TX to a suitable half-duplex TTL transceiver |
| 21 | UART1 RX from that transceiver |
| 22 | Transceiver transmit direction, high while sending |
| 26 | Separate servo supply gate, active high, external pull-down required |

The TC4427 is a dual non-inverting driver and has **no dedicated enable input**. GPIO16 therefore needs an external power-disable circuit. Do not treat a software variable as a power gate. The stop loop must also interrupt power independently of firmware. GPIO17 only lets the firmware observe the loop. Use compatible 3.3 V logic, common signal reference, appropriate supply isolation/decoupling, and a separately rated servo supply. Do not apply 12 V to a Pico GPIO. TC4428 has an inverting channel; it is not interchangeable without accounting for phase inversion in the wiring/profile.

STS3215 uses a single-wire TTL bus. Do not directly join Pico TX/RX or substitute an RS485 interface. Dynamixel XL430 uses a different packet/control-table protocol and is not supported by this driver. Use the exact servo voltage variant's rated supply. De-energizing a loaded arm can release its holding torque; mechanically support the arm during commissioning.

## Build

Install the official Pico SDK, an ARM embedded GCC toolchain and CMake. Set `PICO_SDK_PATH` to the SDK checkout, including its TinyUSB submodule.

```sh
cmake -S firmware/rp2040 -B build/pico -DPICO_BOARD=pico
cmake --build build/pico --parallel
```

`build/pico/khora_pico.uf2` has outputs disabled by default. It supports USB connection, phase preparation and protocol testing. Flash by holding BOOTSEL and copying that UF2 onto the Pico's USB mass-storage volume. Do not copy an output-enabled build onto an uncommissioned assembly.

After installing and independently testing the power-disable and stop circuits, an output-capable build is explicit:

```sh
cmake -S firmware/rp2040 -B build/pico-enabled -DPICO_BOARD=pico -DKHORA_ENABLE_OUTPUTS=ON
cmake --build build/pico-enabled --parallel
```

## Phase engine

One PIO state machine executes `out pins, 16`. Autopull supplies two 16-bit samples per DMA word. A 256-sample period gives 8-bit phase and a nominal 40 kHz carrier. Two chained DMA channels stream a waveform and reload its read address without a CPU interrupt for each period. Three aligned banks allow a newly generated waveform to be published at a DMA block boundary while the active and pending banks remain unchanged.

The 133 MHz clock and fractional divider target 10.24 million samples/s. The average phase step is 97.65625 ns. Fractional division has deterministic clock-cycle variation; this is **not zero-jitter output**. DMA contention and electrical propagation also need measurement. Phase byte q delays the square-wave edge by q samples, matching the source-phasor convention `Re{p exp(-iωt)}` used by the model. Channel duty is 50%; this revision does not synthesize a 200 Hz tactile envelope.

See the official [RP2040 datasheet](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf), [Pico SDK DMA/PIO API](https://www.raspberrypi.com/documentation/pico-sdk/hardware.html), and [Microchip TC4427 reference](https://www.microchip.com/en-us/product/TC4427).

## KH v2 protocol

The frame keeps the KH header/CRC layout from [v1](HARDWARE_TRANSPORT.md), but byte 2 is **2**. Clients must not send v1 256-channel frames to this target. USB CDC baud is a host setting, not a carrier clock; the supplied clients select 921600.

| Type | Payload | Response |
| --- | --- | --- |
| 1 HELLO | Random nonce, 4 bytes | READY 0x82: nonce4, channel count uint16=16, capabilities1, fault1, firmware revision1=3 |
| 2 PHASES | Exactly 16 phase bytes | ACK 0x80 status; stage or publish phase bank, never arm |
| 3 STOP | Empty | Disable both gates, end session; ACK |
| 4 ARM | nonce4, output mask1 | ACK; mask 1 acoustic, 2 servo, 3 both |
| 5 HEARTBEAT | Empty | ACK; renew an active lease |
| 6 SERVO_WRITE | Whitelisted STS3215 packet | ACK of forwarding, not measured motion |
| 8 SERVO_READ | Servo ID 1–6 | 0x83: ID1, packet error1, registers 56–67 inclusive (12 bytes) |
| 9 STATUS | Empty | 0x84: armed1, fault1, staged1, output-build permission1, output mask1 |

READY capability 1 is dry-run; output-capable builds report 0x0e. ACK codes: 0 accepted, 1 no valid session/fault latched, 2 replay or stale sequence, 3 ARM unavailable, 4 unsupported command/payload, 5 servo-read timeout. Frames use CRC-16/CCITT-FALSE and little-endian integers. CRC detects corruption, not malicious access.

ARM requires the output-enabled build, a fresh session, staged phases, the closed stop loop and a held ARM button. It never clears a fault. Acoustic and servo gates are selected separately. The browser control page requests only acoustic output; the Python servo example requests only servo output.

The controller checks a 50,000 µs lease every 250 µs using a repeating hardware alarm. At or after the deadline, or on an open stop loop, the state latches a fault and drives the gate GPIOs low. A late heartbeat cannot revive it. USB disconnection also trips an armed controller. The practical upper bound includes alarm/interrupt delay and gate propagation and must be measured. Reset the board after a latched fault; reconnecting USB or sending HELLO does not reset it.

On a stop, the servo gate goes low and the main loop attempts broadcast torque-off. The GPIO-controlled gate is the independent interruption path; the UART message is best effort. Neither is a robot braking trajectory or a certified emergency-stop system.

## Commissioning record

Start with power drivers disconnected and dry firmware. Capture all 16 logic outputs, carrier period, phase offsets, bank changes and FIFO continuity. Inject malformed CRC, replayed frames, USB loss and a heartbeat arriving at 49,999/50,000 µs. Measure the gate signal and actual rail interruption with the physical stop loop open and with the host frozen. Publish the waveform, supply/load conditions and timing uncertainty before treating the firmware as validated hardware.

The reference STS3215 firmware envelope accepts IDs 1–6, positions 500–3500 and raw speed values 1–800, only in an armed servo session. EEPROM writes, ID changes, mode changes and reset commands are rejected. These bounds are a starting envelope, not mechanical calibration of your robot.

For the optical profile, record whether the specified 85 mm source spacing is measured along the plate normal or vertically. Use a measured plate pose and source point in the DCRA model; 45° and nominal dimensions alone do not register the optical image to the array.
