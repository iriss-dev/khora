"""KH v2 transport for the 16-channel Pico controller."""
import argparse
import json
import secrets
import struct
import threading
import time
from .haptics import AcousticPhasedArray
from .robot import vector


def crc16(data):
    crc = 0xffff
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ (0x1021 if crc & 0x8000 else 0)) & 0xffff
    return crc


def frame(kind, sequence, payload=b''):
    if not isinstance(payload, bytes) or len(payload) > 256:
        raise ValueError("Payload must be bytes, at most 256 bytes")
    header = struct.pack('<2sBBHI', b'KH', 2, kind, len(payload), sequence & 0xffffffff)
    data = header + payload
    return data + struct.pack('<H', crc16(data))


class Decoder:
    def __init__(self):
        self.buffer = bytearray()
        self.errors = 0

    def push(self, data):
        result = []
        for byte in data:
            self.buffer.append(byte)
            while len(self.buffer) >= 2:
                if self.buffer[:2] != b'KH':
                    del self.buffer[0]
                    continue
                if len(self.buffer) < 10:
                    break
                length = struct.unpack_from('<H', self.buffer, 4)[0]
                if self.buffer[2] != 2 or length > 256:
                    self.errors += 1
                    del self.buffer[0]
                    continue
                if len(self.buffer) < length + 12:
                    break
                data_frame = bytes(self.buffer[:length+12])
                if crc16(data_frame[:-2]) != struct.unpack_from('<H', data_frame, length+10)[0]:
                    self.errors += 1
                    del self.buffer[0]
                    continue
                result.append((data_frame[3], struct.unpack_from('<I', data_frame, 6)[0], data_frame[10:-2]))
                del self.buffer[:length+12]
        return result


def phases_for_focus(focal_point_m):
    focal = vector(focal_point_m, 3, "focal_point_m")
    if abs(focal[0]) > .06 or abs(focal[1]) > .06 or not .04 <= focal[2] <= .24:
        raise ValueError("Focus must be inside X/Y ±60 mm and Z 40–240 mm")
    array = AcousticPhasedArray(grid_rows=4, grid_cols=4, pitch_mm=16)
    return bytes(array.synthesize_focus(focal, integrate_force=False)['phases_8bit'])


class PicoClient:
    def __init__(self, stream, timeout=.015):
        self.stream, self.timeout = stream, timeout
        self.sequence = 0
        self.decoder = Decoder()
        self.lock = threading.RLock()
        self.connected = False
        self.armed = False
        self.nonce = secrets.token_bytes(4)
        self.info = {}

    @classmethod
    def open(cls, port, baudrate=921600):
        try:
            import serial
        except ImportError as error:
            raise RuntimeError("Install the hardware extra: pip install -e '.[hardware]'") from error
        stream = serial.Serial(port=None, baudrate=baudrate, timeout=.003, write_timeout=.01)
        stream.dtr = False
        stream.rts = False
        stream.port = port
        stream.open()
        client = cls(stream)
        try:
            client.connect()
            return client
        except Exception:
            stream.close()
            raise

    def request(self, kind, payload=b'', expected=0x80, timeout=None):
        with self.lock:
            self.sequence = (self.sequence + 1) & 0xffffffff
            sequence = self.sequence
            started = time.monotonic()
            deadline = started + (self.timeout if timeout is None else timeout)
            packet = frame(kind, sequence, payload)
            if self.stream.write(packet) != len(packet):
                self.close()
                raise OSError("Incomplete serial write")
            while time.monotonic() < deadline:
                chunk = self.stream.read(min(268, max(1, getattr(self.stream, 'in_waiting', 0))))
                for reply_kind, reply_seq, data in self.decoder.push(chunk):
                    if reply_seq != sequence:
                        continue
                    if reply_kind == 0x80 and (len(data) != 1 or data[0] != 0):
                        raise RuntimeError(f"Pico rejected command: status {data[0] if data else 'missing'}")
                    if reply_kind != expected:
                        continue
                    self.info['last_ack_ms'] = (time.monotonic()-started)*1000
                    return data
            self.close()
            raise TimeoutError("Pico acknowledgement timed out; session closed")

    def connect(self):
        ready = self.request(1, self.nonce, expected=0x82, timeout=1.0)
        if len(ready) != 9 or ready[:4] != self.nonce or ready[4:6] != b'\x10\x00' or ready[8] != 3:
            self.close()
            raise RuntimeError("Expected a KH v2, revision 3, 16-channel controller")
        self.connected = True
        self.info.update({'protocol': 2, 'channels': 16, 'capabilities': ready[6], 'fault': ready[7],
                          'mode': 'simulation' if getattr(self.stream, 'simulated', False) else 'serial',
                          'output_permission': bool(ready[6] & 2)})
        return self.status()

    def status(self):
        if self.connected:
            state = self.request(9, expected=0x84)
            if len(state) != 5:
                raise RuntimeError("Invalid Pico status frame")
            self.armed = bool(state[0])
            self.info.update({'armed': self.armed, 'fault': state[1], 'phases_staged': bool(state[2]), 'output_mask': state[4]})
        return dict(self.info, connected=self.connected)

    def stage_focus(self, focal_point_m):
        phases = phases_for_focus(focal_point_m)
        self.request(2, phases)
        return dict(self.status(), phases_8bit=list(phases), focus_m=focal_point_m)

    def arm(self, output='acoustics'):
        if not self.info.get('output_permission'):
            raise RuntimeError("Firmware was built with outputs disabled")
        if output not in ('acoustics', 'servos', 'both'):
            raise ValueError('Output must be acoustics, servos or both')
        self.request(4, self.nonce + bytes([{'acoustics': 1, 'servos': 2, 'both': 3}[output]]))
        self.armed = True
        self.info['output_mask'] = {'acoustics': 1, 'servos': 2, 'both': 3}[output]

    def heartbeat(self):
        self.request(5)

    def stop(self):
        try:
            if self.connected:
                self.request(3)
        finally:
            self.armed = False
            self.connected = False

    def close(self):
        self.armed = False
        self.connected = False
        self.stream.close()


class SimulatedPico:
    simulated = True

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.decoder = Decoder()
        self.output = bytearray()
        self.session = False
        self.closed = False
        self.phases = None
        self.sequence = 0

    @property
    def in_waiting(self):
        return len(self.output)

    def write(self, data):
        if self.closed:
            raise OSError("Simulator closed")
        for kind, seq, payload in self.decoder.push(data):
            reply, body = 0x80, b'\x00'
            if kind == 1 and len(payload) == 4:
                self.session = True
                self.phases = None
                self.sequence = seq
                reply, body = 0x82, payload + b'\x10\x00\x01\x00\x03'
            elif kind == 3 and not payload:
                self.session = False
            elif kind == 9:
                reply, body = 0x84, bytes([0, 0, self.phases is not None, 0, 0])
            elif not self.session:
                body = b'\x01'
            elif not 0 < ((seq-self.sequence) & 0xffffffff) < 0x80000000:
                body = b'\x02'
            else:
                self.sequence = seq
                if kind == 2 and len(payload) == 16:
                    self.phases = payload
                elif kind == 5 and not payload:
                    pass
                else:
                    body = b'\x03'
            self.output.extend(frame(reply, seq, body))
        return len(data)

    def read(self, size):
        data = bytes(self.output[:size])
        del self.output[:size]
        return data

    def close(self):
        self.closed = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', help='Explicit local serial device, e.g. COM4 or /dev/ttyACM0')
    parser.add_argument('--focus-mm', nargs=3, type=float, default=[0, 0, 140])
    args = parser.parse_args()
    client = PicoClient.open(args.port) if args.port else PicoClient(SimulatedPico())
    try:
        if not args.port:
            client.connect()
        print(json.dumps(client.stage_focus([x/1000 for x in args.focus_mm]), indent=2))
        client.stop()
    finally:
        client.close()


if __name__ == '__main__':
    main()
