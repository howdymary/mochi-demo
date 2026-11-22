import fs from 'node:fs';
const mode=process.argv[2]||'training';
const host='http://127.0.0.1:9355';
const tab=await(await fetch(host+'/json/new?'+encodeURIComponent('http://127.0.0.1:4127/showcase-v27-export.html?mode='+mode),{method:'PUT'})).json();
const ws=new WebSocket(tab.webSocketDebuggerUrl);
await new Promise(r=>ws.addEventListener('open',r,{once:true}));
let id=0;const pending=new Map(),errors=[];
ws.addEventListener('message',event=>{const m=JSON.parse(event.data);if(m.id){const p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text)});
function call(method,params={}){return new Promise((resolve,reject)=>{const key=++id;pending.set(key,{resolve,reject});ws.send(JSON.stringify({id:key,method,params}))})}
async function run(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value}
await call('Runtime.enable');await call('Page.enable');
await call('Emulation.setDeviceMetricsOverride',{width:1280,height:760,deviceScaleFactor:1,mobile:false});
for(let i=0;i<300;i++){
 const state=await run('window.exportState');
 if(state?.status==='ready')break;
 if(errors.length)throw Error(errors.join('\n'));
 if(i===299)throw Error('Renderer initialization timeout');
 await new Promise(r=>setTimeout(r,500));
}
await run('window.paint('+ (mode==='training'?155:180) +')');
await new Promise(r=>setTimeout(r,500));
const shot=await call('Page.captureScreenshot',{format:'png',clip:{x:0,y:0,width:1280,height:720,scale:1}});
fs.writeFileSync('mochi/artifacts/showcase-final/'+mode+'-preview.png',Buffer.from(shot.data,'base64'));
await run(`window.startExport().catch(error=>{window.exportState.status='error';window.exportState.error=String(error)}); 'started'`);
let previous='';
while(true){
 const state=await run('window.exportState');
 const message=JSON.stringify(state);if(message!==previous){console.log(message);previous=message}
 if(state.status==='done'){fs.writeFileSync('mochi/artifacts/showcase-final/'+mode+'-export.json',JSON.stringify({...state,errors},null,2)+'\n');break}
 if(state.status==='error'||errors.length)throw Error(state.error||errors.join('\n'));
 await new Promise(r=>setTimeout(r,15000));
}
await call('Page.close');ws.close();
