import assert from 'node:assert/strict';
import fs from 'node:fs';
const url=process.argv[2]||'http://127.0.0.1:4127/showcase-v27.html';
const host='http://127.0.0.1:9355';
const tab=await(await fetch(host+'/json/new?'+encodeURIComponent(url),{method:'PUT'})).json();
const ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));
let serial=0;const pending=new Map(),errors=[];
ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text)});
function call(method,params={}){const id=++serial;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error(method+' timeout')),45000);pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}))})}
async function run(expression){const result=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);return result.result.value}
async function until(expression){for(let i=0;i<180;i++){if(await run(expression))return;await new Promise(r=>setTimeout(r,500))}throw Error('Readiness timeout: '+expression)}
await call('Runtime.enable');await call('Page.enable');
await call('Page.bringToFront');
await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1050,deviceScaleFactor:1,mobile:false});
await until(`document.querySelectorAll('video').length===3`);
await until(`[...document.querySelectorAll('video')].every(v=>v.readyState>=1&&v.duration>0)`);
const videos=await run(`[...document.querySelectorAll('video')].map(v=>({src:v.currentSrc,duration:v.duration,videoWidth:v.videoWidth,videoHeight:v.videoHeight,error:v.error?.message,hasControls:v.controls}))`);
assert.equal(videos.length,3);videos.forEach(v=>{assert(v.duration>0);assert(v.videoWidth>0);assert(!v.error);assert(v.hasControls)});
for(let i=0;i<3;i++){
 await run(`(async()=>{const v=document.querySelectorAll('video')[${i}];v.muted=true;v.currentTime=Math.min(3,v.duration/2);await v.play()})()`);
 await until(`(()=>{const v=document.querySelectorAll('video')[${i}];return v.currentTime>3.15&&!v.paused&&!v.seeking&&v.readyState>=2})()`);
 const state=await run(`(()=>{const v=document.querySelectorAll('video')[${i}];return {time:v.currentTime,paused:v.paused,error:v.error?.message,otherPlaying:[...document.querySelectorAll('video')].filter((v,j)=>j!==${i}&&!v.paused).length}})()`);
 assert(state.time>3);assert(!state.paused);assert(!state.error);assert.equal(state.otherPlaying,0);
}
await run(`document.querySelectorAll('video').forEach(v=>v.pause());document.querySelector('#latest').scrollIntoView();document.querySelector('#latest video').currentTime=120`);
await until(`(()=>{const v=document.querySelector('#latest video');return v.readyState>=2&&!v.seeking${url.startsWith('https:')?'&&Math.abs(v.currentTime-120)<.2':''}})()`);
await new Promise(r=>setTimeout(r,400));
let shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
fs.mkdirSync('mochi/evidence/showcase-v27',{recursive:true});
fs.writeFileSync('mochi/evidence/showcase-v27/desktop.png',Buffer.from(shot.data,'base64'));
await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
await run('window.scrollTo(0,0)');
await new Promise(r=>setTimeout(r,300));
assert(await run('document.documentElement.scrollWidth<=innerWidth'));
shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
fs.writeFileSync('mochi/evidence/showcase-v27/mobile.png',Buffer.from(shot.data,'base64'));
assert.equal(errors.length,0,errors.join('\n'));
const report={url,verified:true,videos,playback_verified:true,one_video_at_a_time:true,mobile_overflow:false,errors};
fs.writeFileSync('mochi/evidence/showcase-v27/browser-qa.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));await call('Page.close');ws.close();
