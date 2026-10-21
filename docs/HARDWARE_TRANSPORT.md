# KHORA staging transport, version 1

Status: browser client and portable C receiver implemented. USB CDC/UART board
initialization, physical drivers, sensor acquisition and a native LeapC bridge
are integration work. This version intentionally has no ARM command. A valid
ACK means a phase bank was staged in memory, not emitted acoustically.

## Frame layout

All multi-byte integers and float32 values use little-endian order.

| Offset | Bytes | Field |
| --- | ---: | --- |
| 0 | 2 | Magic `4b 48` (ASCII KH) |
| 2 | 1 | Version `01` |
| 3 | 1 | Message type |
| 4 | 2 | Payload length, 0–256 |
| 6 | 4 | Sequence number, modulo 2^32 |
| 10 | n | Payload |
| 10+n | 2 | CRC-16/CCITT-FALSE over header and payload |

CRC polynomial is `0x1021`, initial value `0xffff`, no reflection, no final XOR;
`123456789` gives `0x29b1`. The CRC is stored little-endian. It detects accidental
corruption and is not authentication. Receivers bound retained parsing state
to at most 268 bytes and recover from invalid version, length and CRC by
scanning for the next magic sequence. Partial and coalesced reads are valid.

| Type | Direction | Payload / semantics |
| --- | --- | --- |
| `01` HELLO | Host → device | Four random nonce bytes. Disables staging outputs and begins a sequence session. |
| `82` READY | Device → host | Echo nonce (4), channel count `0x0100` (2), capabilities `01` (1: dry staging only). Echo request sequence. |
| `02` PHASES | Host → device | Exactly 256 bytes in row-major order. Each byte q represents advancing phasor phase `2 pi q/256` under `exp(-i omega t)`. |
| `80` ACK | Device → host | One byte: 0 accepted, 1 invalid command/session, 2 stale sequence. Echo request sequence. |
| `03` STOP | Host → device | Empty payload. Disable channels and end staging session. |
| `81` TRACK | Device → host | Optional future board sensor: uint32 device time in us, float32 XYZ in array-frame metres, uint8 confidence 0–100. |

Array ordering is `i = 16*row + column`, position
`[(column-7.5)*0.01, (row-7.5)*0.01, 0] m`. Element normals face +Z. PHASES
must advance the session sequence by a modular difference in `(0, 2^31)`.
HELLO establishes a new dry session; it must not reset a separate fault latch
in a future physical controller. The current C receiver does not generate
TRACK samples; the browser decodes the schema without mapping it to actuation.
Replayed or backwards tracking sequences are dropped, including across wrap.
The UI labels reception stale after 100 ms without a packet; this host timer
does not establish sensor acquisition age or implement a hardware interlock.

The client allows one outstanding command and retains no outgoing phase
queue. Handshake timeout is 1000 ms; phase ACK timeout is 100 ms. These are
transport timeouts, unrelated to a 50 ms output watchdog. A timeout, stream
failure, explicit disconnect or hidden document closes the browser session.
Permission to select a serial port is a browser security dialog, invoked only
by the Connect button. No application `alert`, `confirm` or `prompt` is used.

`stage(phases)` sends the actual quantized phase bytes and waits for a matching
ACK. Hann amplitude weights are absent from this protocol; the UI blocks
staging while Hann is selected. The browser closes streams without relying on
a final STOP reaching a device. A future physical receiver must enforce
expiry independently, since a browser can be suspended or unplugged.

See the official [WebSerial API guide](https://developer.chrome.com/docs/capabilities/serial)
for secure-context, permission and stream lifetime requirements.

## Board adapter

The board must supply serial receive bytes to `khora_protocol_receive` and
write callback responses to the same transport. The portable library has no
GPIO initialization and no MCU `main`, and cannot be flashed as a complete
firmware image. `khora_phased_array_update_phases` stages timer values without
enabling channels. No watchdog heartbeat is inferred from phase preview
messages.

`khora_watchdog_feed(ctx, seq, now_ms)` now takes a controller monotonic tick.
Duplicate or backwards sequences do not extend the lease. A feed at or after
the deadline latches a fault even if it arrives before the periodic check.
Unsigned subtraction handles one timer wrap; callers must not leave a session
unchecked for a full 32-bit timer period. Faults require explicit controller
reinitialization under a board-defined manual reset procedure.

The board's periodic interrupt must call the deadline check, and drive output
enable inactive when it fails. The library clears software channel state, but
does not manipulate GPIO or brake a robot. Robot deceleration and ultrasound
gate disable are separate actions, with separately assessed stopping times.

## WebHID alternative

Use a vendor-defined usage page and explicit product filter, not unrestricted
access to arbitrary HID interfaces. An adapter can carry this same logical
frame as five 64-byte reports: a 4-byte transfer header (transfer ID uint16,
fragment index uint8, total fragments uint8) followed by up to 60 frame bytes.
Pad the last report and use the KHORA payload length to recover frame length.
Assemble into a fixed 268-byte buffer; reject duplicates, mismatched transfer
IDs and incomplete transfers after a bounded deadline. Validate the whole
CRC before staging. The five-report latency must be measured for the selected
device descriptor and OS. WebHID support is a design, not an implemented UI
transport in this revision. See the official
[WebHID API guide](https://developer.chrome.com/docs/capabilities/hid).

## Acceptance criteria for physical operation

Before adding any ARM capability, define the board identity, calibration ID,
protocol version, output voltage and current limits, channel response map,
physical output-enable circuit, temperature feedback and a latched stop path.
Fault injection must include truncated packets, CRC errors, stale sensor
timestamps, replayed commands, host disconnect, frozen browser, USB reset,
controller overload and sensor loss. Verify shutdown on the output-enable
line with an oscilloscope; a software state or UI badge is insufficient.
