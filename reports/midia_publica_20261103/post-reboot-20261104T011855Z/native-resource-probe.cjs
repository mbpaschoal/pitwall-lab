const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {request}=require('/Users/MBPaschoal/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{const output=process.argv[2],c=await request.newContext(),rows=[];
for(const name of ['index.Cnpi3o3E.js','index.FFOzOWzC.js']){
 for(const suffix of ['', '?pitwall_probe=20261104T0124']){
 const url='https://pitwall-lab.streamlit.app/~/+/static/js/'+name+suffix,row={url,utc:new Date().toISOString()};
 try{const r=await c.get(url,{timeout:15000});const b=await r.body();row.status=r.status();row.final_path=new URL(r.url()).pathname;row.type=r.headers()['content-type'];row.bytes=b.length;row.sha256=crypto.createHash('sha256').update(b).digest('hex');if(row.status!==200||!String(row.type).includes('javascript'))row.body_excerpt=b.toString('utf8').slice(0,1400);}
 catch(e){row.error=e.message;}rows.push(row);}
}await c.dispose();fs.writeFileSync(path.join(output,'native-resource-probe.json'),JSON.stringify(rows,null,2));console.log(JSON.stringify(rows));})();
