/* SI coordinates: array in XY, sound propagates toward +Z. No external runtime. */
(function (root) {
  'use strict';
  const TAU = 2 * Math.PI;
  const C = 331.3 * Math.sqrt(1 + 20 / 273.15);
  const K = TAU * 40000 / C;
  const elements = Array.from({length: 256}, (_, i) => [
    ((i % 16) - 7.5) * 0.01, (Math.floor(i / 16) - 7.5) * 0.01, 0
  ]);
  function directivity(x) {
    let term = 1, sum = 1;
    for (let m = 1; m < 16; m++) { term *= -x*x / (4*m*(m+1)); sum += term; }
    return sum;
  }
  function synthesize(focus, taper = false) {
    if (focus.length !== 3 || !focus.every(Number.isFinite) || focus[2] < 0.02)
      throw new RangeError('Focus requires finite XYZ coordinates above 20 mm');
    const phases = new Uint8Array(256), weights = new Uint8Array(256);
    elements.forEach((e, i) => {
      const d = Math.hypot(...focus.map((v, j) => v - e[j]));
      const phi = ((-K*d) % TAU + TAU) % TAU;
      phases[i] = Math.floor(phi / TAU * 256 + 0.5) % 256;
      const hann = (n) => 0.5 - 0.5 * Math.cos(TAU * n / 15);
      weights[i] = taper ? Math.round(255 * hann(i % 16) * hann(Math.floor(i / 16))) : 255;
    });
    return {phases, weights};
  }
  function pressure(point, drive, source = 1) {
    if (point.length !== 3 || !point.every(Number.isFinite) || point[2] < 0.02 || !Number.isFinite(source) || source < 0)
      throw new RangeError('Invalid field sample');
    let re = 0, im = 0;
    elements.forEach((e, i) => {
      const dx = point[0]-e[0], dy = point[1]-e[1], dz = point[2];
      const d = Math.hypot(dx,dy,dz);
      const amp = source * drive.weights[i]/255 * directivity(K*0.005*Math.hypot(dx,dy)/d)/d;
      const phase = K*d + TAU*drive.phases[i]/256;
      re += amp*Math.cos(phase); im += amp*Math.sin(phase);
    });
    const rms = Math.hypot(re,im)/Math.SQRT2;
    return {rms, radiation: 2*rms*rms/(1.204*C*C)};
  }
  function patchForce(center, drive, source = 1, samples = 12) {
    let sum = 0;
    const step = 0.01 / samples;
    for (let y=0; y<samples; y++) for (let x=0; x<samples; x++)
      sum += pressure([center[0]+(x+0.5-samples/2)*step,
        center[1]+(y+0.5-samples/2)*step,center[2]],drive,source).radiation;
    return sum*step*step*1000;
  }
  const vertexShader = `varying vec2 vUv;
    void main(){vUv=uv; gl_Position=vec4(position.xy,0.0,1.0);}`;
  // Far-field of EACH disk, spherical paths across the whole aperture. No Gaussian glow.
  const fragmentShader = `precision highp float;
    varying vec2 vUv;
    uniform sampler2D driveMap;
    uniform float k, source, referencePressure, sliceOffset, forceScale;
    uniform int sliceMode, quantity;
    const float PI=3.141592653589793;
    float piston(float x){
      float term=1.0; float sum=1.0;
      for(int m=1;m<16;m++){float n=float(m);term*=-x*x/(4.0*n*(n+1.0));sum+=term;}
      return sum;
    }
    vec3 palette(float t){
      vec3 a=vec3(0.02,0.024,0.031), b=vec3(0.05,0.31,0.36);
      vec3 c=vec3(1.0,0.342,0.133), d=vec3(1.0,0.94,0.77);
      if(t<0.42)return mix(a,b,t/0.42);
      if(t<0.78)return mix(b,c,(t-0.42)/0.36);
      return mix(c,d,(t-0.78)/0.22);
    }
    void main(){
      float lateral=(vUv.x-0.5)*0.32;
      vec3 p=vec3(lateral,sliceOffset,0.02+vUv.y*0.24);
      if(sliceMode==1)p=vec3(sliceOffset,lateral,p.z);
      if(sliceMode==2)p=vec3(lateral,(vUv.y-0.5)*0.32,sliceOffset);
      vec2 sum=vec2(0.0);
      for(int row=0;row<16;row++)for(int col=0;col<16;col++){
        vec2 ij=vec2(float(col),float(row));
        vec4 drive=texture2D(driveMap,(ij+0.5)/16.0);
        vec3 delta=p-vec3((ij-7.5)*0.01,0.0);
        float distance=length(delta);
        float amplitude=source*drive.g*piston(k*0.005*length(delta.xy)/distance)/distance;
        float phase=k*distance+(drive.r*255.0/256.0)*2.0*PI;
        sum+=amplitude*vec2(cos(phase),sin(phase));
      }
      float rms=length(sum)*0.7071067811865476;
      float db=20.0*log(max(rms,1e-8)/max(referencePressure,1e-8))/log(10.0);
      float scalar=clamp((db+40.0)/40.0,0.0,1.0);
      if(quantity==1)scalar=clamp(rms*rms/(1.204*${C.toPrecision(16)}*${C.toPrecision(16)})*2.0*0.001/forceScale,0.0,1.0);
      vec3 color=palette(scalar);
      // A 20 mm coordinate grid; a small contribution preserves field contrast.
      vec2 axes=vec2(lateral,sliceMode==2?p.y:p.z);
      vec2 grid=abs(fract(axes/0.02+0.5)-0.5);
      float line=1.0-smoothstep(0.006,0.02,min(grid.x,grid.y));
      color=mix(color,vec3(0.45),line*0.16);
      gl_FragColor=vec4(color,1.0);
    }`;
  const api = {C,K,elements,directivity,synthesize,pressure,patchForce,vertexShader,fragmentShader};
  if (typeof module !== 'undefined') module.exports=api;
  else root.KhoraAcoustics=api;
})(globalThis);
