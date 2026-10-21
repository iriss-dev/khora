(function (root) {
  'use strict';
  const crc16 = KhoraSerial.crc16;
  function encode(type, sequence, payload = new Uint8Array()) {
    if (!(payload instanceof Uint8Array) || payload.length > 256)
      throw new Error('Invalid payload');
    const data = new Uint8Array(payload.length + 12),
      view = new DataView(data.buffer);
    data.set([75, 72, 2, type]);
    view.setUint16(4, payload.length, true);
    view.setUint32(6, sequence, true);
    data.set(payload, 10);
    view.setUint16(data.length - 2, crc16(data.subarray(0, -2)), true);
    return data;
  }
  class Decoder {
    constructor() {
      this.buffer = [];
    }
    push(chunk) {
      const frames = [];
      for (const byte of chunk) {
        this.buffer.push(byte);
        while (this.buffer.length >= 2) {
          if (this.buffer[0] !== 75 || this.buffer[1] !== 72) {
            this.buffer.shift();
            continue;
          }
          if (this.buffer.length < 10) break;
          const n = this.buffer[4] | (this.buffer[5] << 8);
          if (this.buffer[2] !== 2 || n > 256) {
            this.buffer.shift();
            continue;
          }
          if (this.buffer.length < n + 12) break;
          const data = Uint8Array.from(this.buffer.slice(0, n + 12)),
            view = new DataView(data.buffer);
          if (crc16(data.subarray(0, -2)) !== view.getUint16(n + 10, true)) {
            this.buffer.shift();
            continue;
          }
          frames.push({
            type: data[3],
            sequence: view.getUint32(6, true),
            payload: data.slice(10, -2),
          });
          this.buffer.splice(0, n + 12);
        }
      }
      return frames;
    }
  }
  function phasesAt(focus) {
    if (
      !Array.isArray(focus) ||
      focus.length !== 3 ||
      !focus.every(Number.isFinite) ||
      Math.abs(focus[0]) > 0.06 ||
      Math.abs(focus[1]) > 0.06 ||
      focus[2] < 0.04 ||
      focus[2] > 0.24
    )
      throw new Error('Focus outside 16-channel workspace');
    return Uint8Array.from({ length: 16 }, (_, i) => {
      const distance = Math.hypot(
        focus[0] - ((i % 4) - 1.5) * 0.016,
        focus[1] - (Math.floor(i / 4) - 1.5) * 0.016,
        focus[2],
      );
      return (
        Math.round(
          (((((-KhoraAcoustics.K * distance) % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)) /
            (2 * Math.PI)) *
            256,
        ) % 256
      );
    });
  }
  class PicoDevice {
    constructor(onChange = () => {}) {
      this.onChange = onChange;
      this.sequence = 0;
      this.connected = false;
      this.armed = false;
      this.pending = null;
      this.decoder = new Decoder();
      this.info = { mode: 'disconnected', channels: 16 };
    }
    notify() {
      this.onChange({ ...this.info, connected: this.connected, armed: this.armed });
    }
    async simulate() {
      this.simulated = true;
      this.connected = true;
      this.info = { mode: 'simulation', channels: 16, outputPermission: false, fault: 0 };
      this.notify();
    }
    async connect() {
      if (this.connected || this.port) throw new Error('Session already open');
      if (!navigator.serial) throw new Error('Web Serial requires Chrome or Edge');
      this.port = await navigator.serial.requestPort();
      try {
        await this.port.open({ baudRate: 921600, bufferSize: 4096 });
        this.reader = this.port.readable.getReader();
        this.writer = this.port.writable.getWriter();
        this.readTask = this.readLoop();
        this.nonce = crypto.getRandomValues(new Uint8Array(4));
        const ready = await this.request(1, this.nonce, 0x82, 1000);
        if (
          ready.length !== 9 ||
          !this.nonce.every((x, i) => ready[i] === x) ||
          ready[4] !== 16 ||
          ready[5] !== 0 ||
          ready[8] !== 3
        )
          throw new Error('Expected KH v2 revision 3 / 16 channels');
        this.info = {
          mode: 'serial',
          channels: 16,
          outputPermission: Boolean(ready[6] & 2),
          fault: ready[7],
        };
        this.connected = true;
        this.notify();
      } catch (error) {
        await this.close();
        throw error;
      }
    }
    async request(type, payload = new Uint8Array(), expected = 0x80, timeout = 100) {
      if (this.pending) throw new Error('Device busy');
      const sequence = (this.sequence = (this.sequence + 1) >>> 0);
      let resolve, reject;
      const result = new Promise((yes, no) => {
        resolve = yes;
        reject = no;
      });
      const timer = setTimeout(() => {
        if (this.pending?.sequence === sequence) {
          this.pending = null;
          reject(new Error('Pico acknowledgement timeout'));
        }
      }, timeout);
      this.pending = { sequence, expected, resolve, reject, timer };
      try {
        const [, data] = await Promise.all([
          this.writer.write(encode(type, sequence, payload)),
          result,
        ]);
        return data;
      } catch (error) {
        if (this.pending?.sequence === sequence) {
          clearTimeout(timer);
          this.pending = null;
          reject(error);
        }
        throw error;
      }
    }
    async readLoop() {
      try {
        while (this.reader) {
          const { value, done } = await this.reader.read();
          if (done) break;
          for (const msg of this.decoder.push(value)) {
            const pending = this.pending;
            if (!pending || msg.sequence !== pending.sequence) continue;
            if (msg.type === 0x80 && (msg.payload.length !== 1 || msg.payload[0] !== 0)) {
              clearTimeout(pending.timer);
              this.pending = null;
              pending.reject(new Error(`Pico rejected command (${msg.payload[0]})`));
            } else if (msg.type === pending.expected) {
              clearTimeout(pending.timer);
              this.pending = null;
              pending.resolve(msg.payload);
            }
          }
        }
      } catch (error) {
        if (!this.closing) {
          this.info.fault = error.message;
          this.notify();
        }
      }
      if (!this.closing) queueMicrotask(() => this.close());
    }
    async stage(phases) {
      if (!this.connected || !(phases instanceof Uint8Array) || phases.length !== 16)
        throw new Error('A connected 16-channel controller is required');
      if (!this.simulated) await this.request(2, phases);
      this.info.phasesStaged = true;
      this.notify();
    }
    async arm() {
      if (
        !this.connected ||
        !this.info.outputPermission ||
        this.info.fault ||
        !this.info.phasesStaged
      )
        throw new Error('Outputs unavailable or phases not staged');
      await this.request(4, Uint8Array.from([...this.nonce, 1]));
      this.armed = true;
      this.notify();
      this.heartbeat = setInterval(async () => {
        if (this.pending || !this.armed) return;
        try {
          await this.request(5, new Uint8Array(), 0x80, 30);
        } catch (error) {
          this.info.fault = error.message;
          await this.close();
        }
      }, 20);
    }
    async stop() {
      clearInterval(this.heartbeat);
      this.armed = false;
      if (this.connected && !this.simulated && !this.pending) {
        try {
          await this.request(3);
        } catch {}
      }
      await this.close();
    }
    async close() {
      if (this.closing) return this.closing;
      this.closing = (async () => {
        clearInterval(this.heartbeat);
        this.armed = false;
        this.connected = false;
        if (this.pending) {
          clearTimeout(this.pending.timer);
          this.pending.reject(new Error('Session closed'));
          this.pending = null;
        }
        try {
          await this.reader?.cancel();
        } catch {}
        await this.readTask;
        this.reader?.releaseLock();
        this.reader = null;
        try {
          await this.writer?.abort();
        } catch {}
        this.writer?.releaseLock();
        this.writer = null;
        try {
          await this.port?.close();
        } catch {}
        this.port = null;
        this.readTask = null;
        this.simulated = false;
        this.info.mode = 'disconnected';
        this.info.phasesStaged = false;
        this.notify();
      })();
      try {
        await this.closing;
      } finally {
        this.closing = null;
      }
    }
  }
  const api = { encode, Decoder, phasesAt, PicoDevice };
  if (typeof module !== 'undefined') module.exports = api;
  else root.KhoraPico = api;
})(globalThis);
