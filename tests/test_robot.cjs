const {test}=require('node:test');
const assert=require('node:assert/strict');
const R=require('../platform/robot-model.js');
global.KhoraSerial=require('../platform/serial-bridge.js');
global.KhoraAcoustics=require('../platform/acoustic-field.js');
const P=require('../platform/pico-device.js');

test('reference IK reaches a target within 0.01 mm',()=>{
  const target=[.25,.15,.55],q=R.inverse(target),position=R.forward(q).position;
  assert.ok(Math.hypot(...position.map((x,i)=>x-target[i]))<1e-5);
  q.forEach((x,i)=>assert.ok(x>=R.limits[i][0]&&x<=R.limits[i][1]));
  assert.throws(()=>R.inverse([9,0,.5]));
  assert.throws(()=>R.forward([NaN,0,0,0,0,0]));
});
test('imported plans reject modified timing and out-of-range joints',()=>{
  const plan=R.plan([.25,.15,.55]);
  assert.equal(R.validatePlan(plan),plan);
  const fast=JSON.parse(JSON.stringify(plan));fast.duration_s=.001;
  assert.throws(()=>R.validatePlan(fast));
  const invalid=JSON.parse(JSON.stringify(plan));invalid.samples[50].joints_rad[0]=10;
  assert.throws(()=>R.validatePlan(invalid));
  const nan=JSON.parse(JSON.stringify(plan));nan.samples[50].time_s=NaN;
  assert.throws(()=>R.validatePlan(nan));
});
test('KH v2 codec handles fragmentation, corrupt CRC and bounded state',()=>{
  const decoder=new P.Decoder(),encoded=P.encode(2,0xffffffff,new Uint8Array(16).fill(128));
  const messages=[];for(const byte of encoded)messages.push(...decoder.push([byte]));
  assert.equal(messages[0].sequence,0xffffffff);assert.equal(messages[0].payload.length,16);
  const bad=encoded.slice();bad[11]^=1;
  assert.equal(decoder.push(Uint8Array.from([...bad,...P.encode(3,0)])).length,1);
  decoder.push(new Uint8Array(100000).fill(255));assert.ok(decoder.buffer.length<268);
});
test('16-channel profile is symmetric, bounded and cannot arm the simulator',async()=>{
  const phase=P.phasesAt([0,0,.14]);
  assert.equal(phase.length,16);assert.ok(phase.every((q,i)=>q===phase[15-i]));
  assert.throws(()=>P.phasesAt([0,0,.001]));
  const device=new P.PicoDevice();await device.simulate();await device.stage(phase);
  assert.equal(device.info.phasesStaged,true);assert.equal(device.armed,false);
  await assert.rejects(device.arm());await device.close();assert.equal(device.connected,false);
});
