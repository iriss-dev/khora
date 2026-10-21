/* KHORA v1 binary staging protocol. Connecting never arms the output stage. */
(function(root){
  'use strict';
  const TYPE={HELLO:1, PHASES:2, STOP:3, ACK:128, TRACK:129, READY:130};
  function crc16(bytes) {
    let crc=0xffff;
    for(const b of bytes){crc^=b<<8;for(let i=0;i<8;i++)crc=((crc&0x8000)?(crc<<1)^0x1021:crc<<1)&0xffff;}
    return crc;
  }
  function frame(type,sequence,payload=new Uint8Array()){
    if(!(payload instanceof Uint8Array)||payload.length>256)throw new RangeError('Payload exceeds 256 bytes');
    const out=new Uint8Array(12+payload.length), v=new DataView(out.buffer);
    out.set([0x4b,0x48,1,type]);v.setUint16(4,payload.length,true);v.setUint32(6,sequence,true);
    out.set(payload,10);v.setUint16(out.length-2,crc16(out.subarray(0,-2)),true);return out;
  }
  class Decoder{
    constructor(){this.buffer=[];this.errors=0;}
    push(chunk){
      const frames=[];
      // Process bytewise: retained buffer is bounded even for a large input chunk.
      for(const byte of chunk){
        this.buffer.push(byte);
        while(this.buffer.length>=2){
          if(this.buffer[0]!==0x4b||this.buffer[1]!==0x48){this.buffer.shift();continue;}
          if(this.buffer.length<10)break;
          const len=this.buffer[4]|this.buffer[5]<<8;
          if(this.buffer[2]!==1||len>256){this.errors++;this.buffer.shift();continue;}
          if(this.buffer.length<len+12)break;
          const data=Uint8Array.from(this.buffer.slice(0,len+12));
          const view=new DataView(data.buffer);
          if(crc16(data.subarray(0,-2))!==view.getUint16(data.length-2,true)){
            this.errors++;this.buffer.shift();continue;
          }
          frames.push({type:data[3],sequence:view.getUint32(6,true),payload:data.slice(10,-2)});
          this.buffer.splice(0,len+12);
        }
      }
      return frames;
    }
  }
  class SerialBridge{
    constructor(onChange=()=>{},onTrack=()=>{}){
      this.onChange=onChange;this.onTrack=onTrack;this.state='disconnected';
      this.sequence=0;this.pending=null;this.port=null;this.rtt=[];this.decoder=new Decoder();
      this.lastTrackSequence=null;
    }
    status(state,message){this.state=state;this.onChange({state,message,rtt:this.rtt.slice(),crcErrors:this.decoder.errors});}
    async connect(){
      if(this.state!=='disconnected')throw new Error('Serial session already active');
      if(!globalThis.isSecureContext||!navigator.serial)throw new Error('WebSerial requires Chrome/Edge on localhost or HTTPS');
      this.status('connecting','Select a KHORA v1 staging device');
      try{
        this.port=await navigator.serial.requestPort();
        await this.port.open({baudRate:1000000,bufferSize:4096,flowControl:'none'});
        this.writer=this.port.writable.getWriter();this.reader=this.port.readable.getReader();
        this.decoder=new Decoder();this.rtt=[];this.lastTrackSequence=null;this.readTask=this.readLoop();
        const nonce=crypto.getRandomValues(new Uint8Array(4));
        const ready=await this.request(TYPE.HELLO,nonce,TYPE.READY,1000);
        if(ready.payload.length!==7||!nonce.every((b,i)=>ready.payload[i]===b)
          ||new DataView(ready.payload.buffer,ready.payload.byteOffset).getUint16(4,true)!==256
          ||ready.payload[6]!==1)throw new Error('Unsupported device: dry staging capability required');
        this.status('ready','Connected / output disabled / phase staging only');
      }catch(error){await this.disconnect();throw error;}
    }
    async request(type,payload,reply=TYPE.ACK,timeout=100){
      if(this.pending)throw new Error('Device busy; no command queue is retained');
      if(!this.writer)throw new Error('Serial writer unavailable');
      const sequence=this.sequence=(this.sequence+1)>>>0;
      const start=performance.now();
      let resolve,reject;
      const response=new Promise((yes,no)=>{resolve=yes;reject=no;});
      const timer=setTimeout(()=>{
        if(this.pending?.sequence===sequence){this.pending=null;reject(new Error('Device acknowledgement timed out'));}
      },timeout);
      this.pending={sequence,reply,resolve,reject,timer,start};
      // Observe write and reply together: neither timeout nor write rejection is unhandled.
      try{const [,result]=await Promise.all([this.writer.write(frame(type,sequence,payload)),response]);return result;}
      catch(error){if(this.pending?.sequence===sequence){clearTimeout(timer);this.pending=null;reject(error);}throw error;}
    }
    async stage(phases){
      if(this.state!=='ready'||!(phases instanceof Uint8Array)||phases.length!==256)
        throw new Error('A ready device and exactly 256 phase bytes are required');
      try{
        const ack=await this.request(TYPE.PHASES,phases);
        if(ack.payload.length!==1||ack.payload[0]!==0)throw new Error('Device rejected phase staging');
        this.status('ready','256 phases acknowledged / output disabled');
      }catch(error){this.status('fault',error.message);await this.disconnect();throw error;}
    }
    async readLoop(){
      try{
        while(this.reader){
          const {value,done}=await this.reader.read();if(done)break;
          for(const msg of this.decoder.push(value)){
            const pending=this.pending;
            if(pending&&msg.sequence===pending.sequence&&msg.type===pending.reply){
              clearTimeout(pending.timer);this.pending=null;
              this.rtt.push(performance.now()-pending.start);if(this.rtt.length>128)this.rtt.shift();
              pending.resolve(msg);
            }else if(msg.type===TYPE.TRACK&&msg.payload.length===17){
              const v=new DataView(msg.payload.buffer,msg.payload.byteOffset);
              const xyz=[v.getFloat32(4,true),v.getFloat32(8,true),v.getFloat32(12,true)];
              const advance=this.lastTrackSequence===null?1:(msg.sequence-this.lastTrackSequence)>>>0;
              if(xyz.every(Number.isFinite)&&msg.payload[16]<=100&&advance>0&&advance<0x80000000){
                this.lastTrackSequence=msg.sequence;
                this.onTrack({sequence:msg.sequence,deviceTimeUs:v.getUint32(0,true),xyz,
                  confidence:msg.payload[16]/100,receivedAt:performance.now()});
              }
            }
          }
        }
        if(this.state!=='closing')throw new Error('Device disconnected');
      }catch(error){
        if(this.state!=='closing'){
          this.status('fault',error.message);
          if(this.pending){clearTimeout(this.pending.timer);this.pending.reject(error);this.pending=null;}
          // Defer cleanup so it does not await its own read task.
          queueMicrotask(()=>this.disconnect());
        }
      }
    }
    async disconnect(){
      if(this.closeTask)return this.closeTask;
      this.closeTask=this.close();
      try{await this.closeTask;}finally{this.closeTask=null;}
    }
    async close(){
      this.status('closing','Closing serial session');
      if(this.pending){clearTimeout(this.pending.timer);this.pending.reject(new Error('Session closed'));this.pending=null;}
      try{await this.reader?.cancel();}catch{}
      await this.readTask;
      this.reader?.releaseLock();this.reader=null;this.readTask=null;
      // Abort pending writes; the board owns timeout shutdown, independent of JS scheduling.
      try{await this.writer?.abort();}catch{}
      this.writer?.releaseLock();this.writer=null;
      try{await this.port?.close();}catch{}
      this.port=null;this.status('disconnected','Disconnected / output unverified');
    }
  }
  const api={TYPE,crc16,frame,Decoder,SerialBridge};
  if(typeof module!=='undefined')module.exports=api;else root.KhoraSerial=api;
})(globalThis);
