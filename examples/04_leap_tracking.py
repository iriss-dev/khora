"""Read an index fingertip through the official Ultraleap Python bindings."""
import argparse
import json
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from khora.tracking import TrackingFrame
from khora.hardware import PicoClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--calibration', required=True, help='JSON with measured sensor_to_array 4x4 transform, in metres')
    parser.add_argument('--port', help='Optional Pico port for disabled-output phase staging')
    args = parser.parse_args()
    try:
        import leap
    except ImportError:
        parser.error('Install Gemini/Hyperion-compatible official Ultraleap leapc-python-bindings; see docs/TRACKING.md')
    calibration = json.loads(Path(args.calibration).read_text(encoding='utf-8'))
    tracking = TrackingFrame(calibration['sensor_to_array'])
    lock = threading.Lock()

    class Listener(leap.Listener):
        def on_tracking_event(self, event):
            if not event.hands:
                return
            tip = event.hands[0].digits[1].distal.next_joint
            with lock:
                tracking.update_mm([tip.x, tip.y, tip.z], event.tracking_frame_id)

    connection = leap.Connection()
    connection.add_listener(Listener())
    client = PicoClient.open(args.port) if args.port else None
    last_id, last_seen = None, None
    try:
        with connection.open():
            connection.set_tracking_mode(leap.TrackingMode.Desktop)
            while True:
                with lock:
                    sample = tracking.current()
                if sample and sample['frame_id'] != last_id:
                    last_id, last_seen = sample['frame_id'], time.monotonic()
                    if client:
                        client.stage_focus(sample['position_m'])
                    print(json.dumps(sample), flush=True)
                elif last_seen is not None and time.monotonic()-last_seen >= .1:
                    if client:
                        client.stop()
                    print(json.dumps({'tracking': 'stale', 'phase_staging': 'stopped'}), flush=True)
                    break
                time.sleep(.02)
    except KeyboardInterrupt:
        pass
    finally:
        if client:
            try:
                client.stop()
            finally:
                client.close()


if __name__ == '__main__':
    main()
