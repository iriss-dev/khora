"""Rigid sensor registration and latest-frame freshness checks."""
import math
import time
from .robot import vector


class TrackingFrame:
    def __init__(self, sensor_to_array, clock=time.monotonic):
        if not isinstance(sensor_to_array, list) or len(sensor_to_array) != 4:
            raise ValueError('Expected a 4x4 sensor-to-array transform')
        self.transform = [vector(row, 4, 'transform row') for row in sensor_to_array]
        if self.transform[3] != [0, 0, 0, 1]:
            raise ValueError('Expected a rigid homogeneous transform')
        r = self.transform
        for i in range(3):
            for j in range(3):
                dot = sum(r[k][i]*r[k][j] for k in range(3))
                if abs(dot-(1 if i == j else 0)) > 1e-5:
                    raise ValueError('Rotation must be orthonormal')
        determinant = (r[0][0]*(r[1][1]*r[2][2]-r[1][2]*r[2][1])
                       - r[0][1]*(r[1][0]*r[2][2]-r[1][2]*r[2][0])
                       + r[0][2]*(r[1][0]*r[2][1]-r[1][1]*r[2][0]))
        if abs(determinant-1) > 1e-5:
            raise ValueError('Rotation must preserve handedness')
        self.clock, self.last_id, self.latest = clock, None, None

    def update_mm(self, point_mm, frame_id, sensor_time_us=None):
        point = vector(point_mm, 3, 'sensor position')
        if type(frame_id) is not int or frame_id < 0 or (self.last_id is not None and frame_id <= self.last_id):
            return False
        position = [sum(self.transform[i][j]*point[j]/1000 for j in range(3))+self.transform[i][3] for i in range(3)]
        self.last_id = frame_id
        self.latest = {'frame_id': frame_id, 'position_m': position, 'received_at': self.clock(), 'sensor_time_us': sensor_time_us}
        return True

    def current(self, max_age_s=.05):
        if self.latest is None or self.clock()-self.latest['received_at'] >= max_age_s:
            return None
        return dict(self.latest)
