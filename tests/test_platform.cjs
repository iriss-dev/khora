const {test}=require('node:test');
const assert=require('node:assert/strict');
const A=require('../platform/acoustic-field.js');
const config=require('../platform/field-config.js');
const {TYPE,crc16,frame,Decoder,SerialBridge}=require('../platform/serial-bridge.js');

test('shared configurations reject invalid numbers and constrain coordinates',()=>{
  assert.deepEqual(config.parse('#x=900&y=-900&z=NaN&plane=3&quantity=Infinity&taper=1'),
    {x:60,y:-60,z:140,plane:2,quantity:0,taper:1});
  const state={x:13,y:-9,z:180,plane:1,quantity:1,taper:1};
  assert.deepEqual(config.parse(config.encode(state)),state);
});

test('phase exports preserve focus, channel order and modulation limitations',()=>{
  const state={x:13,y:-9,z:180,plane:1,quantity:0,taper:1};
  const drive=A.synthesize([.013,-.009,.18],true);
  const output=config.phaseExport(state,drive);
  assert.deepEqual(output.focus_m,[.013,-.009,.18]);
  assert.deepEqual(output.phase_u8,Array.from(drive.phases));
  assert.deepEqual(output.amplitude_u8,Array.from(drive.weights));
  assert.equal(output.phase_u8.length,256);
  assert.equal(output.phase_only_serial_compatible,false);
});

test('CRC-CCITT-FALSE published check vector',()=>{
  assert.equal(crc16(Buffer.from('123456789')),0x29b1);
});
test('fragmented frames, coalescence, CRC corruption and resynchronization',()=>{
  const d=new Decoder(), payload=Uint8Array.from({length:256},(_,i)=>i);
  const encoded=frame(TYPE.PHASES,0xfffffffe,payload);
  let decoded=[];
  for(const byte of encoded)decoded.push(...d.push([byte]));
  assert.equal(decoded.length,1);assert.deepEqual(decoded[0].payload,payload);
  assert.equal(decoded[0].sequence,0xfffffffe);
  const bad=encoded.slice();bad[19]^=1;
  decoded=d.push(Uint8Array.from([...bad,...frame(TYPE.STOP,0),...frame(TYPE.STOP,1)]));
  assert.equal(decoded.length,2);assert.ok(d.errors>0);
  d.push(new Uint8Array(100000).fill(255));assert.ok(d.buffer.length<268);
});
test('oversized payloads and malformed headers are rejected',()=>{
  assert.throws(()=>frame(1,1,new Uint8Array(257)),RangeError);
  const d=new Decoder();
  const bad=frame(1,1);bad[4]=255;bad[5]=255;
  assert.equal(d.push(Uint8Array.from([...bad,...frame(3,2)])).length,1);
});
test('phase wrap has a half-step error bound and mirror symmetry',()=>{
  const focus=[.013,-.009,.14], drive=A.synthesize(focus);
  A.elements.forEach((e,i)=>{
    const phase=-A.K*Math.hypot(...focus.map((v,j)=>v-e[j]));
    const residual=Math.atan2(Math.sin(drive.phases[i]*2*Math.PI/256-phase),Math.cos(drive.phases[i]*2*Math.PI/256-phase));
    assert.ok(Math.abs(residual)<=Math.PI/256+1e-10);
  });
  const centered=A.synthesize([0,0,.14]);
  assert.ok(centered.phases.every((p,i)=>p===centered.phases[255-i]));
});
test('piston null and force scale follow physics',()=>{
  assert.ok(Math.abs(A.directivity(3.8317059702))<1e-10);
  const drive=A.synthesize([0,0,.14]);
  const f=A.patchForce([0,0,.14],drive);
  assert.ok(f>0);assert.equal(A.patchForce([0,0,.14],drive,2),4*f);
  assert.ok(A.pressure([0,0,.14],A.synthesize([0,0,.14],true)).rms<A.pressure([0,0,.14],drive).rms);
});
test('single outstanding transaction; ACK match and timeout',async()=>{
  const bridge=new SerialBridge();
  bridge.writer={write:async()=>{}};
  const first=bridge.request(TYPE.STOP,new Uint8Array(),TYPE.ACK,15);
  await assert.rejects(bridge.request(TYPE.STOP,new Uint8Array()),/busy/);
  await assert.rejects(first,/timed out/);
  assert.equal(bridge.pending,null);
});
test('write rejection clears transaction without unhandled timeout',async()=>{
  const bridge=new SerialBridge();bridge.writer={write:async()=>{throw new Error('USB failure');}};
  await assert.rejects(bridge.request(TYPE.STOP,new Uint8Array()),/USB failure/);
  assert.equal(bridge.pending,null);
});

test('mock serial handshake, exact phase payload, matched ACK, telemetry replay and cleanup',async()=>{
  const original=Object.getOwnPropertyDescriptor(globalThis,'navigator');
  const secure=Object.getOwnPropertyDescriptor(globalThis,'isSecureContext');
  let incoming,closed=false,staged=null;
  const messages=[];
  const deviceDecoder=new Decoder();
  const port={
    open:async()=>{},close:async()=>{closed=true;},
    readable:new ReadableStream({start(controller){incoming=controller;}}),
    writable:new WritableStream({write(bytes){
      for(const msg of deviceDecoder.push(bytes)){
        if(msg.type===TYPE.HELLO){
          const payload=Uint8Array.from([...msg.payload,0,1,1]);
          incoming.enqueue(frame(TYPE.READY,msg.sequence,payload));
        }else if(msg.type===TYPE.PHASES){
          staged=msg.payload;
          incoming.enqueue(frame(TYPE.ACK,msg.sequence+1,Uint8Array.of(1))); // wrong seq ignored
          incoming.enqueue(frame(TYPE.ACK,msg.sequence,Uint8Array.of(0)));
        }
      }
    }})
  };
  Object.defineProperty(globalThis,'navigator',{configurable:true,value:{serial:{requestPort:async()=>port}}});
  Object.defineProperty(globalThis,'isSecureContext',{configurable:true,value:true});
  const bridge=new SerialBridge(()=>{},m=>messages.push(m));
  try{
    await bridge.connect();assert.equal(bridge.state,'ready');
    const phases=A.synthesize([0,0,.14]).phases;await bridge.stage(phases);
    assert.deepEqual(staged,phases);assert.equal(bridge.rtt.length,2);
    const track=new Uint8Array(17),view=new DataView(track.buffer);
    view.setUint32(0,1000,true);view.setFloat32(12,.14,true);track[16]=90;
    incoming.enqueue(frame(TYPE.TRACK,0xffffffff,track));
    incoming.enqueue(frame(TYPE.TRACK,0,track));
    incoming.enqueue(frame(TYPE.TRACK,0,track)); // replay
    incoming.enqueue(frame(TYPE.TRACK,0xfffffffe,track)); // stale
    await new Promise(resolve=>setTimeout(resolve,0));
    assert.equal(messages.length,2);assert.equal(messages[1].sequence,0);
    await bridge.disconnect();assert.equal(bridge.state,'disconnected');assert.ok(closed);
    assert.equal(port.readable.locked,false);assert.equal(port.writable.locked,false);
  }finally{
    await bridge.disconnect();
    if(original)Object.defineProperty(globalThis,'navigator',original);else delete globalThis.navigator;
    if(secure)Object.defineProperty(globalThis,'isSecureContext',secure);else delete globalThis.isSecureContext;
  }
});
