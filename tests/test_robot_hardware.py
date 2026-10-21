import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'python'))
from khora.robot import forward_poe, reference_arm, plan_move, HOME
from khora.hardware import crc16, frame, Decoder, PicoClient, SimulatedPico, phases_for_focus
from khora.servos import JointCalibration, sync_positions, ServoSupervisor, packet, read_feedback
from khora.mcp_server import handle_tool_call
from khora.tracking import TrackingFrame


class RobotTests(unittest.TestCase):
    def test_poe_matches_transform_chain(self):
        rng = random.Random(42)
        for _ in range(25):
            q = [rng.uniform(-1, 1) for _ in range(6)]
            a = forward_poe(q)
            b = reference_arm().forward_kinematics(q).matrix
            for row_a, row_b in zip(a, b):
                for x, y in zip(row_a, row_b):
                    self.assertAlmostEqual(x, y, places=12)

    def test_plan_endpoint_and_analytic_motion_bounds(self):
        plan = plan_move([.25, .15, .55])
        duration = plan['duration_s']
        start, end = plan['samples'][0]['joints_rad'], plan['samples'][-1]['joints_rad']
        self.assertLess(plan['position_error_mm'], .01)
        for a, b in zip(start, end):
            distance = abs(b-a)
            self.assertLessEqual(1.875*distance/duration, .8+1e-10)
            self.assertLessEqual(10/math.sqrt(3)*distance/duration**2, 1.5+1e-10)
            self.assertLessEqual(60*distance/duration**3, 8+1e-10)
        self.assertEqual(plan['execution'], 'simulation_only')

    def test_invalid_targets_and_nonfinite_tools(self):
        for target in [[9, 0, .5], [0, 0, float('nan')], [True, 0, .5], [0, 0]]:
            with self.assertRaises(ValueError):
                plan_move(target)
        with self.assertRaises(ValueError):
            handle_tool_call('khora_compute_haptic_focal_plane', {'focal_point': [0,0,.14], 'grid_size': 100000})
        with self.assertRaises(ValueError):
            handle_tool_call('khora_kinematic_solve_ik', {'target_pos': [float('nan'),0,.5]})

    def test_browser_plan_import_and_model_parity(self):
        script = "const R=require('./platform/robot-model.js');const input=JSON.parse(require('fs').readFileSync(0,'utf8'));R.validatePlan(input.plan);console.log(JSON.stringify(R.forward(input.q)));"
        root = Path(__file__).resolve().parents[1]
        output = subprocess.run(['node','-e',script], input=json.dumps({'q': HOME, 'plan': plan_move([.25,.15,.55])}), text=True, cwd=root, capture_output=True, check=True)
        position = json.loads(output.stdout)['position']
        expected = forward_poe(HOME)
        for i, value in enumerate(position):
            self.assertAlmostEqual(value, expected[i][3], places=12)


class HardwareTests(unittest.TestCase):
    def test_tracking_registration_replay_and_expiry(self):
        now=[0.0]
        tracking=TrackingFrame([[1,0,0,.01],[0,0,-1,.02],[0,1,0,0],[0,0,0,1]],clock=lambda:now[0])
        self.assertTrue(tracking.update_mm([10,140,20],1))
        self.assertEqual(tracking.current()['position_m'],[.02,0.0,.14])
        self.assertFalse(tracking.update_mm([0,0,0],1))
        now[0]=.05
        self.assertIsNone(tracking.current())
        with self.assertRaises(ValueError):
            TrackingFrame([[1,0,0,0],[0,1,0,0],[0,0,-1,0],[0,0,0,1]])

    def test_feedback_raw_units_and_error_flags(self):
        import struct
        class Client:
            def request(self,*args,**kwargs):
                return bytes([1,0])+struct.pack('<HHH',2048,0x8001,0x0405)+bytes([120,31,0,0,1,0])
        result=read_feedback(Client(),1)
        self.assertEqual(result['speed_raw'],-1)
        self.assertEqual(result['load_raw'],-5)
        self.assertEqual(result['voltage_v'],12.0)
        self.assertEqual(result['temperature_c'],31)
        self.assertTrue(result['moving'])

    def test_crc_fragmentation_corruption_and_bounds(self):
        self.assertEqual(crc16(b'123456789'), 0x29b1)
        decoder = Decoder()
        data = frame(2, 0xffffffff, bytes(range(16)))
        result = []
        for byte in data:
            result.extend(decoder.push(bytes([byte])))
        self.assertEqual(result, [(2, 0xffffffff, bytes(range(16)))])
        bad = bytearray(data); bad[11] ^= 1
        self.assertEqual(decoder.push(bytes(bad)+frame(3, 0)), [(3,0,b'')])
        decoder.push(b'\xff'*10000)
        self.assertLess(len(decoder.buffer), 268)

    def test_simulated_connection_stages_exactly_16_channels(self):
        stream = SimulatedPico(); client = PicoClient(stream)
        self.assertEqual(client.connect()['mode'], 'simulation')
        result = client.stage_focus([.01,-.01,.14])
        self.assertEqual(stream.phases, phases_for_focus([.01,-.01,.14]))
        self.assertEqual(len(result['phases_8bit']), 16)
        self.assertFalse(result['armed'])
        with self.assertRaises(RuntimeError):
            client.arm()
        client.stop(); client.close()

    def test_native_firmware_protocol_interoperability(self):
        executable = os.environ.get('KHORA_PICO_HOST')
        if not executable:
            self.skipTest('C++ host executable not configured on this host')
        nonce=b'abcd'; phases=phases_for_focus([0,0,.14])
        output=subprocess.run([executable], input=frame(1,1,nonce)+frame(2,2,phases)+frame(9,3)+frame(4,4,nonce+b'\x01')+frame(3,5), capture_output=True, check=True)
        replies=Decoder().push(output.stdout)
        self.assertEqual(replies[0], (0x82,1,nonce+b'\x10\x00\x01\x00\x03'))
        self.assertEqual(replies[1], (0x80,2,b'\x00'))
        self.assertEqual(replies[2], (0x84,3,b'\x00\x00\x01\x00\x00'))
        self.assertEqual(replies[3], (0x80,4,b'\x03'))
        self.assertEqual(replies[4], (0x80,5,b'\x00'))

    def test_servo_packets_calibration_and_signs(self):
        calibration=[JointCalibration(1,2048,1,1000,3000)]
        data=sync_positions(calibration,[0],400)
        self.assertEqual(data[:7], b'\xff\xff\xfe\x0b\x83\x2a\x06')
        self.assertEqual(sum(data[2:]) & 255, 255)
        self.assertEqual(packet(254,3,b'\x28\x00'), b'\xff\xff\xfe\x04\x03\x28\x00\xd2')
        with self.assertRaises(ValueError):
            sync_positions(calibration,[math.pi])
        with self.assertRaises(ValueError):
            sync_positions(calibration,[0],0)

    def test_host_deadline_latches_and_rejects_late_resume(self):
        class Client:
            armed=True
            info={'output_mask':2}
            def __init__(self): self.stopped=False
            def request(self,*args,**kwargs): return b'\0'
            def heartbeat(self): pass
            def stop(self): self.stopped=True; self.armed=False
            def close(self): pass
        now=[0.0]; client=Client()
        supervisor=ServoSupervisor(client,[JointCalibration(1,2048,1,1000,3000)],clock=lambda:now[0])
        supervisor.submit([0])
        now[0]=.049999; supervisor.check_deadline()
        now[0]=.05
        with self.assertRaises(TimeoutError): supervisor.check_deadline()
        self.assertTrue(client.stopped)
        with self.assertRaises(RuntimeError): supervisor.submit([0])

    def test_reply_timeout_closes_transport(self):
        class Silent:
            closed=False
            def write(self,data): return len(data)
            def read(self,size): return b''
            def close(self): self.closed=True
        stream=Silent(); client=PicoClient(stream,timeout=.001)
        with self.assertRaises(TimeoutError): client.request(9)
        self.assertTrue(stream.closed)


class MCPStdioTests(unittest.TestCase):
    def test_lifecycle_notifications_tool_errors_and_simulated_hardware(self):
        requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},
                  {'jsonrpc':'2.0','method':'notifications/initialized'},
                  {'jsonrpc':'2.0','id':2,'method':'tools/list'},
                  {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'khora_robot_plan_move','arguments':{'target_m':[.25,.15,.55]}}},
                  {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'khora_hardware_stage_focus','arguments':{'focal_point_m':[0,0,.14]}}},
                  {'jsonrpc':'2.0','id':5,'method':'tools/call','params':{'name':'khora_robot_plan_move','arguments':{'target_m':[9,0,.5]}}}]
        run=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'tools/run_mcp.py'),'--simulate-device'],input='\n'.join(map(json.dumps,requests))+'\n',capture_output=True,text=True,check=True)
        responses=[json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual([r['id'] for r in responses],[1,2,3,4,5])
        self.assertEqual(responses[0]['result']['protocolVersion'],'2025-06-18')
        self.assertTrue(responses[-1]['result']['isError'])
        self.assertFalse(responses[-2]['result']['isError'])
        tools=[tool['name'] for tool in responses[1]['result']['tools']]
        self.assertNotIn('khora_hardware_arm',tools)
        self.assertEqual(json.loads(responses[-2]['result']['content'][0]['text'])['channels'],16)


if __name__ == '__main__':
    unittest.main()
