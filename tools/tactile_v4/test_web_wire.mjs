import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {PacketDecoder,decodePacket,crc16,crc32,decodeJpeg,spectrum} from '../../hardware/glove-v4/software-preview/wire.js';
const root=new URL('../../',import.meta.url);
const bytes=readFileSync(new URL('firmware/tactile_v4/artifacts/native-actual-core.bin.piezo',root));
const stream=new PacketDecoder();let frames=[];for(let i=0;i<bytes.length;i+=17)frames.push(...stream.feed(bytes.subarray(i,i+17)));
const expected=readFileSync(new URL('hardware/glove-v3/verification/signal-chain/piezo-to-firmware.csv',root),'utf8').trim().split('\n');const columns=expected.shift().split(','),column=columns.indexOf('dynamic_code'),codes=expected.map(l=>Number(l.split(',')[column]));
const scans=frames.filter(f=>f.kind===1),features=frames.filter(f=>f.kind===4);assert.equal(scans.length,520);assert.equal(features.length,6);assert.equal(stream.errors,0);
assert.deepEqual(scans.map(f=>new DataView(f.payload.buffer,f.payload.byteOffset,f.payload.byteLength).getInt16(54,true)),codes);
for(let i=0;i<6;i++){const a=codes.slice(i*80,(i+1)*80);assert.equal(features[i].rms[0],Math.floor(Math.sqrt(Math.floor(a.reduce((s,v)=>s+v*v,0)/80))));assert.equal(features[i].peak[0],Math.max(...a.map(Math.abs)));assert.equal(features[i].timestampUs,i*20000)}
const bad=new PacketDecoder();bad.feed(new Uint8Array(100000).fill(1));assert.equal(bad.bytes.length,0);assert.equal(bad.errors,1);bad.feed(Uint8Array.of(0));assert.equal(bad.feed(bytes).length,frames.length);
assert.throws(()=>decodePacket(Uint8Array.of(5,1,2)));
assert.equal(crc16(new TextEncoder().encode('123456789')),0x29b1);assert.equal(crc32(new TextEncoder().encode('123456789')),0xcbf43926);
const tone=Array.from({length:512},(_,i)=>100*Math.sin(2*Math.PI*500*i/4000));const s=spectrum(tone);assert.equal(s.indexOf(Math.max(...s)),64);assert.ok(Math.abs(s[64]-100)<.01);
const jpeg=Uint8Array.of(255,216,1,2,255,217),record=new Uint8Array(jpeg.length+32),v=new DataView(record.buffer);record.set(new TextEncoder().encode('GV4J'));v.setUint32(4,9,true);v.setBigUint64(8,123456n,true);v.setUint32(16,jpeg.length,true);v.setUint32(20,crc32(jpeg),true);v.setUint16(24,640,true);v.setUint16(26,480,true);v.setUint16(28,1,true);v.setUint16(30,crc16(record.subarray(0,30)),true);record.set(jpeg,32);assert.equal(decodeJpeg(record).timestampUs,123456);record[34]^=1;assert.throws(()=>decodeJpeg(record));
const dualDecoder=new PacketDecoder(),dual=dualDecoder.feed(readFileSync(new URL('firmware/tactile_v4/artifacts/native-actual-core.bin.dual-mode',root)));
assert.equal(dualDecoder.errors,0);assert.equal(dual.filter(f=>f.kind===3).length,100);assert.equal(dual.filter(f=>f.kind===4).length,51);
for (const frame of dual.filter(f=>f.kind===3)){assert.equal(frame.periodUs,250);assert.equal(frame.channel,20)}
const lossDecoder=new PacketDecoder(),loss=lossDecoder.feed(readFileSync(new URL('firmware/tactile_v4/artifacts/native-actual-core.bin.browser-status',root)));
assert.equal(lossDecoder.errors,0);assert.equal(loss.length,1);assert.equal(loss[0].browserDrops,7);assert.equal(loss[0].browserVideoDrops,1);
console.log(JSON.stringify({status:'pass',actualFirmwareScans:scans.length,actualFeatureWindows:features.length,fragmentedBytes:bytes.length,overflowRecovery:true,crcKnownVectors:true,spectrumPeakHz:500,jpegCrc:true,simultaneousRawFrames:100,simultaneousFeatureFrames:51,browserLossCounters:{sensor:7,video:1}}));
