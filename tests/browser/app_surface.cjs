/* Cloud assigns iframe.src before its browsing context finishes navigation. */
async function surface(page,base){
 const expected=new URL(base);
 if(!expected.hostname.endsWith('.streamlit.app'))return page;
 const deadline=Date.now()+60000;
 while(Date.now()<deadline){
  const app=page.frames().find(frame=>{
   try{const url=new URL(frame.url());return url.origin===expected.origin&&url.pathname.startsWith('/~/+/');}
   catch{return false;}
  });
  if(app)return app;
  await page.waitForTimeout(100);
 }
 throw Error('Public application frame did not finish navigation');
}
module.exports={surface};
