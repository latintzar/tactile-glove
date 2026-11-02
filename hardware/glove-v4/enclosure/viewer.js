import * as THREE from '../../../static/glove-viewer/three.module.js';
import {OrbitControls} from '../../../static/glove-viewer/OrbitControls.js';
const stage=document.getElementById('view'),select=document.getElementById('part');
const scene=new THREE.Scene();scene.background=new THREE.Color('#f1f0e8');
const camera=new THREE.PerspectiveCamera(35,1,.1,1500);camera.up.set(0,0,1);camera.position.set(235,-190,210);
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputColorSpace=THREE.SRGBColorSpace;stage.prepend(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(65,37,18);controls.enableDamping=true;controls.maxDistance=600;controls.minDistance=70;
scene.add(new THREE.HemisphereLight(0xffffff,0x5d7263,1.8));
const key=new THREE.DirectionalLight(0xffffff,2.2);key.position.set(-70,-60,230);key.castShadow=true;key.shadow.mapSize.set(2048,2048);Object.assign(key.shadow.camera,{left:-180,right:180,top:180,bottom:-180,near:1,far:600});key.target.position.set(50,40,20);scene.add(key,key.target);
const fill=new THREE.DirectionalLight(0xffe6cb,.8);fill.position.set(200,120,130);scene.add(fill);
const floor=new THREE.Mesh(new THREE.PlaneGeometry(1600,1600),new THREE.ShadowMaterial({opacity:.13}));floor.position.set(50,40,-18);floor.receiveShadow=true;scene.add(floor);
const solids=new Map(),electronics=new THREE.Group();scene.add(electronics);let mode='assembled',assemblyDescription='',renderQueued=false;
function requestRender(){if(renderQueued)return;renderQueued=true;requestAnimationFrame(()=>{renderQueued=false;controls.update();renderer.render(scene,camera)});}
controls.addEventListener('change',requestRender);
const color=name=>name.includes('camera-window')?'#d5e6e2':name.includes('lightpipe')?'#e8c681':name.includes('battery')?'#859199':name.includes('pcb')?'#254d3a':name.includes('camera-flex')?'#c79b57':name.includes('camera-module')?'#272d2b':name.includes('tpu')||name.includes('grommet')||name.includes('boot')||name.includes('gasket')?'#dd8c55':name.includes('lid')?'#dedfce':name.includes('base')?'#385b45':'#7f9277';
// Fit the actual visible engineering parts; retain the reader's viewing direction.
function fitAssembly(){
 const width=stage.clientWidth,height=stage.clientHeight;
 if(!width||!height||!solids.size)return;
 const box=new THREE.Box3();
 for(const mesh of solids.values())if(mesh.visible)box.expandByObject(mesh);
 if(electronics.visible)box.expandByObject(electronics);
 if(box.isEmpty())return;
 const sphere=box.getBoundingSphere(new THREE.Sphere());
 const vertical=THREE.MathUtils.degToRad(camera.fov/2);
 const tanY=Math.tan(vertical),tanX=tanY*width/height;
 const direction=camera.position.clone().sub(controls.target).normalize();
 const right=new THREE.Vector3().crossVectors(camera.up,direction).normalize();
 const up=new THREE.Vector3().crossVectors(direction,right).normalize();
 let distance=70;
 for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z]){
  const corner=new THREE.Vector3(x,y,z).sub(sphere.center);
  distance=Math.max(distance,corner.dot(direction)+1.12*Math.max(Math.abs(corner.dot(right))/tanX,Math.abs(corner.dot(up))/tanY));
 }
 controls.target.copy(sphere.center);
 camera.position.copy(sphere.center).addScaledVector(direction,distance);
 controls.maxDistance=Math.max(600,distance*2);
 camera.far=Math.max(1500,distance+sphere.radius*4);
 camera.updateProjectionMatrix();
}
function setMode(value){mode=value;for(const [name,m]of solids){m.position.set(0,0,0);const reference=m.userData.reference;let show=(!reference||document.getElementById('references').checked)&&!name.includes('blanking-plug');if(value==='open'&&(/rigid-lid|button-|rgb-lightpipe|lid-perimeter/.test(name)))show=false;if(value==='exploded'){if(name.includes('rigid-lid'))m.position.z=65;else if(/button-|rgb-lightpipe|lid-perimeter/.test(name))m.position.z=55;else if(name.includes('battery'))m.position.z=-32;else if(/rigid-base|saddle|flat-tpu-textile-carrier/.test(name))m.position.z=-45;}m.visible=show;}electronics.visible=document.getElementById('references').checked;floor.position.z=value==='exploded'?-65:-18;for(const b of document.querySelectorAll('[data-mode]'))b.setAttribute('aria-pressed',String(b.dataset.mode===value));fitAssembly();requestRender();}
try{const [parts,manifest,report,envelopes]=await Promise.all(['scene.json','print-manifest.json','clearance-report.json','component-envelopes.json'].map(async url=>{const r=await fetch(url);if(!r.ok)throw Error(url+' '+r.status);return r.json()}));
 const references=new Set(manifest.inspection_solids||[]);
 for(const p of parts){const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(p.positions.flat(),3));geometry.setIndex(p.triangles.flat());geometry.computeVertexNormals();const transparent=p.name.includes('camera-window')||p.name.includes('lightpipe');const material=new THREE.MeshStandardMaterial({color:color(p.name),flatShading:true,roughness:transparent?.22:.53,metalness:p.name.includes('battery')?.12:0,transparent,opacity:transparent?.48:1});const mesh=new THREE.Mesh(geometry,material);mesh.castShadow=true;mesh.receiveShadow=true;mesh.userData.reference=references.has(p.name);scene.add(mesh);solids.set(p.name,mesh);select.add(new Option(p.name.replace('.stl','').replaceAll('-',' '),p.name));}
 for(const group of ['main_board','hand_tile'])for(const p of envelopes[group].parts){
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(p.positions.flat(),3));geometry.setIndex(p.triangles.flat());geometry.computeVertexNormals();
  const m=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:p.ref.startsWith('J')?'#ddd9ca':'#343a36',roughness:.58}));m.castShadow=true;electronics.add(m);
 }
 const d=manifest.case_dimensions_mm,mass=manifest.mass_budget.estimated_cuff_total_g;
 assemblyDescription='Body: '+[d.width,d.length,d.height].join(' × ')+' mm. Cuff estimate: '+mass.map(Math.round).join('–')+' g, before glove and external wiring.';
 document.getElementById('status').textContent=report.geometry_pass?(manifest.first_article_fabrication_ready===true?'Nominal CAD checks passed. Ready for first-article fabrication and physical acceptance.':'Nominal CAD checks passed. Print tolerances and assembly processes are under review.'):'CAD checks in progress: '+report.failed_groups.join(', ')+'.';
 document.getElementById('partInfo').textContent=assemblyDescription;
 window.artisanAssembly={loaded:true,parts:parts.length,components:envelopes.main_board.parts.length,handComponents:envelopes.hand_tile.parts.length,geometryPass:report.geometry_pass,reportStatus:report.status};setMode(mode);
}catch(e){document.getElementById('status').textContent='Engineering files could not be loaded: '+e.message;window.artisanAssembly={loaded:false,error:e.message};}
select.onchange=()=>{for(const[name,m]of solids){m.material.emissive.set(name===select.value?'#394533':'#000000');m.material.emissiveIntensity=name===select.value?.45:0;}const m=solids.get(select.value);if(m){const b=new THREE.Box3().setFromObject(m),s=b.getSize(new THREE.Vector3());document.getElementById('partInfo').textContent=select.selectedOptions[0].textContent+' · '+[s.x,s.y,s.z].map(v=>v.toFixed(1)).join(' × ')+' mm';}else document.getElementById('partInfo').textContent=assemblyDescription;requestRender();};
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.mode));document.getElementById('references').onchange=()=>setMode(mode);
new ResizeObserver(()=>{const w=stage.clientWidth,h=stage.clientHeight;if(!w||!h)return;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();fitAssembly();requestRender();}).observe(stage);
