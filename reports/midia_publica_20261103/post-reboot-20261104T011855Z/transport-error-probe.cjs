const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require('/Users/MBPaschoal/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const output=process.argv[2],report={utc:new Date().toISOString(),errors:[],attempts:[]},pending=[];fs.mkdirSync(output);
 const b=await chromium.launch({headless:true,channel:'chrome'}),p=await b.newPage();
 p.on('response',r=>{const u=new URL(r.url());if(r.status()>=400&&u.pathname.startsWith('/~/+/static/'))pending.push((async()=>{const row={utc:new Date().toISOString(),path:u.pathname,status:r.status(),type:r.headers()['content-type']};try{const bytes=await r.body();row.bytes=bytes.length;row.sha256=crypto.createHash('sha256').update(bytes).digest('hex');row.body_excerpt=bytes.toString('utf8').slice(0,4096);}catch(e){row.body_error=e.message;}report.errors.push(row);})());});
 try{await p.goto('https://pitwall-lab.streamlit.app/?tela=Metodologia&temporada=2026&gp=19&lang=pt',{waitUntil:'domcontentloaded',timeout:20000});for(let i=0;i<7;i++){await p.waitForTimeout(10000);if(report.errors.length)break;}}
 catch(e){report.attempts.push({error:e.message});}finally{await Promise.allSettled(pending);report.end_utc=new Date().toISOString();fs.writeFileSync(path.join(output,'response-bodies.json'),JSON.stringify(report,null,2));await b.close();console.log(JSON.stringify(report));}
})();
