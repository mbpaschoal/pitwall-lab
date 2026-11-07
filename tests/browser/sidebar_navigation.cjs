/* Shared actions for the current sidebar; assertions live in each domain suite. */
async function openMenu(app){
 const menu=app.locator('.st-key-pw-sidebar-menu details');
 await menu.waitFor({state:'attached'});
 await app.waitForFunction(()=>document.querySelector('.st-key-pw-sidebar-menu details')?.dataset.pwReady==='true');
 // Streamlit can replace styles and expander descendants between renders.
 // Hidden for one frame does not mean this is a desktop-only disclosure.
 await app.waitForFunction(()=>{
  const menu=document.querySelector('.st-key-pw-sidebar-menu details'),summary=menu?.querySelector('summary');
  return menu?.open||summary&&summary.getClientRects().length>0&&getComputedStyle(summary).visibility!=='hidden';
 });
 if(!await menu.evaluate(e=>e.open)){
  await menu.locator('summary').click();
 }
 return menu;
}
async function choose(app,id){
 await closeCards(app);
 await openMenu(app);
 const button=app.locator('.st-key-pw_nav_'+id+' button');
 if(await button.count())await button.click();
 else await app.locator('.pw-nav-fallback[data-pw-route="'+id+'"]').click();
}
async function reveal(app,lang){
 await app.getByRole('button',{name:lang==='pt'?'Ver as cartas deste GP':'See the cards for this GP',exact:true}).click();
 await app.getByRole('dialog').locator('.pw-sealed-deck').waitFor();
 for(const card of await app.locator('.pw-sealed-card').all()){
  const back=card.locator('[data-tarot-reveal]');if(await back.isVisible())await back.click();
 }
 await app.waitForFunction(()=>document.querySelectorAll('.pw-revealed-face:not([hidden]) [data-tarot-hide]').length===3);
 await app.waitForFunction(()=>[...document.querySelectorAll('.pw-revealed-face')].every(e=>e.getAnimations().every(a=>a.playState==='finished')));
 await app.locator('.pw-revealed-face img').evaluateAll(images=>Promise.all(images.map(image=>image.decode())));
 await app.locator('.st-key-forecast-details').waitFor({state:'visible'});
}
async function closeCards(app){
 const dialog=app.getByRole('dialog').filter({has:app.locator('.pw-tarot-reading')});
 if(await dialog.isVisible()){
  await dialog.locator('.st-key-close_tarot button').click();
  await dialog.waitFor({state:'hidden'});
  await app.waitForFunction(()=>!new URL(location.href).searchParams.has('cartas')&&document.querySelector('.stApp')?.dataset.testScriptState==='notRunning');
 }
}
module.exports={choose,reveal,closeCards,openMenu};
