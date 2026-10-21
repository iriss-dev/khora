"""Feetech STS3215 packets through the Pico's guarded half-duplex UART."""
from dataclasses import dataclass
import math
import struct
import threading
import time
from .robot import vector


def packet(servo_id, instruction, parameters=b''):
    if not isinstance(servo_id, int) or not 1 <= servo_id <= 254 or len(parameters) > 250:
        raise ValueError("Invalid servo packet")
    data = bytes([servo_id, len(parameters)+2, instruction]) + parameters
    return b'\xff\xff' + data + bytes([(~sum(data)) & 255])


@dataclass(frozen=True)
class JointCalibration:
    servo_id: int
    zero_tick: int
    direction: int
    min_tick: int
    max_tick: int

    def encode(self, angle):
        if isinstance(angle, bool) or not math.isfinite(angle) or self.direction not in (-1, 1):
            raise ValueError("Invalid angle or calibration")
        if not 1 <= self.servo_id <= 6 or not 500 <= self.min_tick < self.max_tick <= 3500:
            raise ValueError("Calibration exceeds firmware envelope")
        tick = round(self.zero_tick + self.direction*angle*4096/(2*math.pi))
        if not self.min_tick <= tick <= self.max_tick:
            raise ValueError(f"Servo {self.servo_id} would exceed calibrated limits")
        return tick


def sync_positions(calibrations, joints_rad, speed_raw=400):
    q = vector(joints_rad, len(calibrations), 'joints_rad')
    if not 1 <= len(q) <= 6 or not isinstance(speed_raw, int) or not 1 <= speed_raw <= 800:
        raise ValueError("Expected 1–6 joints and a speed of 1–800 raw speed units")
    ids = [joint.servo_id for joint in calibrations]
    if len(set(ids)) != len(ids):
        raise ValueError("Servo IDs must be unique")
    payload = bytearray([42, 6])
    for joint, angle in zip(calibrations, q):
        payload.extend(struct.pack('<BHHH', joint.servo_id, joint.encode(angle), 0, speed_raw))
    return packet(254, 0x83, bytes(payload))


def signed_magnitude(value, sign_bit):
    return -(value & ~(1 << sign_bit)) if value & (1 << sign_bit) else value


def read_feedback(client, servo_id):
    if not 1 <= servo_id <= 6:
        raise ValueError('Servo ID must be between 1 and 6')
    data = client.request(8, bytes([servo_id]), expected=0x83)
    if len(data) != 14 or data[0] != servo_id:
        raise RuntimeError('Malformed servo telemetry')
    position, speed, load = struct.unpack_from('<HHH', data, 2)
    result = {'servo_id': servo_id, 'error_bits': data[1] | data[11], 'position_tick': signed_magnitude(position, 15),
              'speed_raw': signed_magnitude(speed, 15), 'load_raw': signed_magnitude(load, 10),
              'voltage_v': data[8]/10, 'temperature_c': data[9], 'moving': bool(data[12]),
              'load_units': 'raw servo register, not calibrated torque or force'}
    if result['error_bits']:
        raise RuntimeError(f'Servo {servo_id} reports error bits {data[1]}')
    return result


class ServoSupervisor:
    def __init__(self, client, calibrations, clock=time.monotonic):
        if not calibrations:
            raise ValueError('Explicit mechanical calibration is required')
        self.client, self.calibrations, self.clock = client, calibrations, clock
        self.last_intent = None
        self.fault = None
        self._shutdown = threading.Event()
        self._worker = None
        self._lock = threading.RLock()

    def start_monitor(self):
        if self._worker:
            raise RuntimeError('Monitor already running')
        def monitor():
            while not self._shutdown.wait(.005):
                try:
                    self.check_deadline()
                except Exception as error:
                    self.fault = str(error)
                    self.client.close()
                    return
        self._worker = threading.Thread(target=monitor, name='khora-servo-deadline', daemon=True)
        self._worker.start()

    def enable_torque(self):
        if not self.client.armed or not self.client.info.get('output_mask', 0) & 2:
            raise RuntimeError('The servo output group must be physically armed first')
        for joint in self.calibrations:
            joint.encode(0.0)
            self.client.request(6, packet(joint.servo_id, 3, bytes([40, 1])))
            self.client.heartbeat()
        self.last_intent = self.clock()

    def sample_feedback(self, servo_id, max_temperature_c=65, max_load_raw=850):
        try:
            feedback = read_feedback(self.client, servo_id)
            if feedback['temperature_c'] >= max_temperature_c or abs(feedback['load_raw']) >= max_load_raw:
                raise RuntimeError('Configured servo temperature/load threshold exceeded')
            return feedback
        except Exception:
            self.fault = 'Servo telemetry failed or exceeded configured limits'
            self.client.stop()
            raise

    def submit(self, joints_rad, speed_raw=400):
        with self._lock:
            if self.fault:
                raise RuntimeError(self.fault)
            self.check_deadline()
            if not self.client.armed:
                raise RuntimeError('Pico must be explicitly armed with the physical interlock closed')
            command = sync_positions(self.calibrations, joints_rad, speed_raw)
            try:
                self.client.request(6, command)
                self.client.heartbeat()
            except Exception:
                self.fault = 'Servo command or heartbeat failed'
                self.client.close()
                raise
            self.last_intent = self.clock()

    def check_deadline(self):
        with self._lock:
            if self.last_intent is not None and self.clock()-self.last_intent >= .05:
                self.fault = '50 ms host command lease expired'
                self.client.stop()
                raise TimeoutError(self.fault)

    def close(self):
        self._shutdown.set()
        if self._worker and self._worker is not threading.current_thread():
            self._worker.join(timeout=.1)
        try:
            self.client.stop()
        finally:
            self.client.close()
