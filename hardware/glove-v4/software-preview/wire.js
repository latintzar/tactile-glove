// V4 wire validation shared by the device UI and independent Node fixture tests.
export function crc16(bytes){let c=65535;for(const b of bytes){c^=b<<8;for(let i=0;i<8;i++)c=((c<<1)^((c&32768)?0x1021:0))&65535}return c}
const crcTable=Uint32Array.from({length:256},(_,n)=>{let c=n;for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xedb88320:0);return c>>>0});
export function crc32(bytes){let c=0xffffffff;for(const b of bytes)c=(c>>>8)^crcTable[(c^b)&255];return(c^0xffffffff)>>>0}
export function decodePacket(encoded){
 const raw=[];for(let i=0;i<encoded.length;){const code=encoded[i++];if(!code||i+code-1>encoded.length)throw Error('COBS');for(let n=1;n<code;n++)raw.push(encoded[i++]);if(code!==255&&i<encoded.length)raw.push(0)}
 const bytes=Uint8Array.from(raw),v=new DataView(bytes.buffer);if(bytes.length<20||bytes[0]!==71||bytes[1]!==51||bytes[3]!==2)throw Error('Header');
 const n=v.getUint16(16,true);if(bytes.length!==20+n||crc16(bytes.subarray(0,-2))!==v.getUint16(bytes.length-2,true))throw Error('CRC/length');
 const p=new DataView(bytes.buffer,18,n),kind=bytes[2],f={kind,seq:v.getUint32(4,true),timestampUs:Number(v.getBigUint64(8,true)),payload:bytes.slice(18,-2)};
 const array=(offset,count,signed=true)=>Array.from({length:count},(_,i)=>signed?p.getInt16(offset+i*2,true):p.getUint16(offset+i*2,true));
 if(kind===4){if(n!==128||p.getUint16(6,true)!==80)throw Error('Features');Object.assign(f,{index:p.getUint32(0,true),flags:p.getUint16(4,true),pressure:array(8,20),rms:array(48,20,false),peak:array(88,20,false)})}
 if(kind===3){if(n!==92||p.getUint16(8,true)!==40||p.getUint16(4,true)>=40||p.getUint16(10,true)!==250)throw Error('Raw');Object.assign(f,{index:p.getUint32(0,true),channel:p.getUint16(4,true),flags:p.getUint16(6,true),periodUs:p.getUint16(10,true),samples:array(12,40)})}
 if(kind===2){if(n!==42||p.getUint16(36,true)!==3000||p.getUint16(38,true)!==1250||p.getUint16(40,true)!==2500)throw Error('Configuration');Object.assign(f,{batteryMv:p.getUint16(32,true),uiFlags:p.getUint16(34,true),adcErrors:p.getUint32(4,true),lateScans:p.getUint32(0,true),captureDrops:p.getUint32(28,true)})}
 if(kind===7){if(n!==32)throw Error('Status');const names=['bootId','cameraFrames','cameraDrops','imuOverruns','imuOdr','captureDrops','sdDrops','statusFlags'];names.forEach((name,i)=>f[name]=p.getUint32(i*4,true))}
 if(kind===9){if(n!==8)throw Error('Browser loss');Object.assign(f,{browserDrops:p.getUint32(0,true),browserVideoDrops:p.getUint32(4,true)})}
 if(kind===8){if(n!==13)throw Error('Label');const z=f.payload.indexOf(0);if(z<0||f.payload.subarray(z).some(x=>x!==0))throw Error('Label');f.label=String.fromCharCode(...f.payload.subarray(0,z));if(!/^[A-Z0-9 /-]{0,12}$/.test(f.label))throw Error('Label')}
 if(kind===6){if(n<24||p.getUint8(18)>28||n!==24+7*p.getUint8(18)||p.getUint8(19)>1)throw Error('IMU');Object.assign(f,{source:p.getUint8(19),imuFlags:p.getUint16(16,true),count:p.getUint8(18),odr:p.getUint16(20,true)})}
 return f;
}
export class PacketDecoder{
 constructor(){this.bytes=[];this.discard=false;this.errors=0}
 feed(chunk){const result=[];for(const b of chunk){if(b){if(this.discard)continue;if(this.bytes.length>=256){this.bytes=[];this.discard=true;this.errors++}else this.bytes.push(b)}else{if(!this.discard&&this.bytes.length){try{result.push(decodePacket(this.bytes))}catch{this.errors++}}this.bytes=[];this.discard=false}}return result}
}
export function decodeJpeg(bytes){
 if(bytes.length<32)throw Error('JPEG header');const v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
 if(String.fromCharCode(...bytes.subarray(0,4))!=='GV4J'||crc16(bytes.subarray(0,30))!==v.getUint16(30,true))throw Error('JPEG header CRC');
 const n=v.getUint32(16,true),width=v.getUint16(24,true),height=v.getUint16(26,true);
 if(n>512*1024||n<4||bytes.length!==n+32||width!==640||height!==480||v.getUint16(28,true)!==1)throw Error('JPEG bounds');
 const data=bytes.slice(32);if(crc32(data)!==v.getUint32(20,true))throw Error('JPEG CRC');
 return{seq:v.getUint32(4,true),timestampUs:Number(v.getBigUint64(8,true)),width,height,data};
}
// Hann-window amplitude spectrum, in the same units as the input samples.
export function spectrum(samples){
 const n=512;if(samples.length<n)return[];const r=new Float64Array(n),im=new Float64Array(n),a=samples.slice(-n),mean=a.reduce((s,x)=>s+x,0)/n;let sumWindow=0;
 for(let i=0;i<n;i++){const w=.5-.5*Math.cos(2*Math.PI*i/(n-1));r[i]=(a[i]-mean)*w;sumWindow+=w}
 for(let i=1,j=0;i<n;i++){let b=n>>1;for(;j&b;b>>=1)j^=b;j^=b;if(i<j){[r[i],r[j]]=[r[j],r[i]]}}
 for(let size=2;size<=n;size*=2){const half=size/2;for(let base=0;base<n;base+=size)for(let j=0;j<half;j++){const phase=-2*Math.PI*j/size,c=Math.cos(phase),s=Math.sin(phase),a=base+j,b=a+half,tr=r[b]*c-im[b]*s,ti=r[b]*s+im[b]*c;r[b]=r[a]-tr;im[b]=im[a]-ti;r[a]+=tr;im[a]+=ti}}
 return Array.from({length:n/2+1},(_,i)=>Math.hypot(r[i],im[i])*(i===0||i===n/2?1:2)/sumWindow);
}
