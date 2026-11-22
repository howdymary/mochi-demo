import {createCurriculumStage} from './navigation-v23-renderer.js';
import {stepCountAt,taskStatesAt} from './efficient-evidence.mjs';

const params=new URLSearchParams(location.search),mode=params.get('mode')||'training';
const canvas=document.querySelector('#output'),ctx=canvas.getContext('2d',{alpha:false});
const W=1280,H=720,FPS=24,SPEED=2;
window.exportState={status:'loading',mode,frame:0};
async function read(url){const response=await fetch(url);if(!response.ok)throw Error(url+' '+response.status);return JSON.parse(await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).text())}
const files=mode==='training'?['efficient-v15/held-out-parent-93001-0.json.gz','efficient-v15/held-out-selected-93001-16.json.gz']:['showcase-v27/final.json.gz'];
const episodes=await Promise.all(files.map(read));
const stages=episodes.map(e=>{const div=document.createElement('div');div.className='stage';document.querySelector('#stages').append(div);return createCurriculumStage(div,{scene:e.scene,fullBody:true,cameraOffset:mode==='training'?[.29,-.46,.26]:[.33,-.52,.30]})});
await Promise.all(stages.map(s=>s.ready));
stages.forEach((s,i)=>{s.setEpisode(episodes[i]);s.showReference(false);s.showFootfalls(false)});
const duration=Math.max(...episodes.map(e=>e.duration));
function text(label,x,y,size=18,color='#e4e9e2',weight=400){ctx.fillStyle=color;ctx.font=`${weight} ${size}px Arial`;ctx.fillText(label,x,y)}
function paint(t){
 ctx.fillStyle='#101512';ctx.fillRect(0,0,W,H);
 text('MOCHI',24,29,14,'#b0c6b0',700);
 text(mode==='training'?'Post-training: 804 to 470 steps':'Clock. Drawer. Laptop. Globe.',24,64,27,'#f0f1e9',600);
 text('RECORDED MUJOCO SIMULATION  |  2x PLAYBACK',900,31,12,'#b5bfb4');
 text(mode==='training'?'Same scenario, seed and physical time':'Corner-desk sequence  |  no cuts or resets',900,57,12,'#b5bfb4');
 episodes.forEach((e,i)=>{
  const width=W/episodes.length,x=i*width,et=Math.min(t,e.duration);
  stages[i].frame(et);
  ctx.drawImage(stages[i].renderer.domElement,x,85,width,560);
  ctx.fillStyle='rgba(16,21,18,.80)';ctx.fillRect(x+12,97,width-24,37);
  text(mode==='training'?(i===0?'STARTING CHECKPOINT':'POST-TRAINED CHECKPOINT +16'):'LATEST VERIFIED CORNER-DESK RUN',x+25,122,15,'#f2f1e9',600);
  const count=stepCountAt(e,et),finished=t>=e.duration;
  text(`${finished?'FINISHED  |  ':''}${count} steps  |  ${et.toFixed(1)} s simulated`,x+24,674,18,'#e7eee4',600);
  let sx=x+24;
  for(const task of taskStatesAt(e,et)){const pass=task.status==='passed';text(`${pass?'✓ ':''}${({alarm:'Clock',drawer:'Drawer',laptop:'Laptop',globe:'Globe'})[task.task]}`,sx,701,14,pass?'#a7d4ac':'#879384');sx+=width/4-10}
 });
 if(episodes.length===2){ctx.fillStyle='#101512';ctx.fillRect(638,85,4,560)}
 return {t,steps:episodes.map(e=>stepCountAt(e,Math.min(t,e.duration)))};
}
window.paint=paint;
window.episodes=episodes;
paint(0);
window.exportState={status:'ready',mode,duration,frame:0,frames:Math.ceil((duration+2)/SPEED*FPS)};
window.startExport=async function(){
 const config={codec:'avc1.4d0028',width:W,height:H,bitrate:6_000_000,framerate:FPS,avc:{format:'annexb'},hardwareAcceleration:'prefer-hardware'};
 const support=await VideoEncoder.isConfigSupported(config);if(!support.supported)throw Error('H.264 WebCodecs encoder unavailable');
 const chunks=[];let error=null;
 const encoder=new VideoEncoder({output(chunk){const data=new Uint8Array(chunk.byteLength);chunk.copyTo(data);chunks.push(data)},error(e){error=e}});
 encoder.configure(config);
 const total=window.exportState.frames;window.exportState.status='rendering';
 for(let f=0;f<total;f++){
  if(error)throw error;
  paint(Math.min(duration,f/FPS*SPEED));
  const frame=new VideoFrame(canvas,{timestamp:Math.round(f/FPS*1_000_000),duration:Math.round(1_000_000/FPS)});
  encoder.encode(frame,{keyFrame:f%(FPS*2)===0});frame.close();
  window.exportState.frame=f+1;
  if(f%12===0||encoder.encodeQueueSize>12)await new Promise(r=>setTimeout(r,0));
  while(encoder.encodeQueueSize>12)await new Promise(r=>setTimeout(r,10));
 }
 await encoder.flush();encoder.close();if(error)throw error;
 const blob=new Blob(chunks,{type:'video/h264'}),name=mode==='training'?'02-training.h264':'03-final.h264';
 const response=await fetch('/export/'+name,{method:'POST',body:blob});if(!response.ok)throw Error('Upload failed');
 window.exportState={...window.exportState,status:'done',bytes:blob.size,fps:FPS,playback_speed:SPEED};
 return window.exportState;
};
