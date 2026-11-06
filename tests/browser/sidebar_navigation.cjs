/* Shared actions for the current sidebar; assertions live in each domain suite. */
async function choose(app,id){
 const menu=app.locator('.st-key-pw-sidebar-menu details');
 await menu.waitFor({state:'attached'});
 await app.waitForFunction(()=>document.querySelector('.st-key-pw-sidebar-menu details')?.dataset.pwReady==='true');
 if(!await menu.evaluate(e=>e.open)){
  if(await menu.locator('summary').isVisible())await menu.locator('summary').click();
  else await app.waitForFunction(()=>document.querySelector('.st-key-pw-sidebar-menu details')?.open===true);
 }
 const button=app.locator('.st-key-pw_nav_'+id+' button');
 if(await button.count())await button.click();
 else await app.locator('.pw-nav-fallback[data-pw-route="'+id+'"]').click();
}
async function reveal(app,lang){
 await app.getByRole('button',{name:lang==='pt'?'Ver as cartas deste GP':'See the cards for this GP',exact:true}).click();
 await app.locator('.pw-sealed-deck').waitFor();
 for(const card of await app.locator('.pw-sealed-card').all()){
  const back=card.locator('[data-tarot-reveal]');if(await back.isVisible())await back.click();
 }
 await app.waitForFunction(()=>document.querySelectorAll('.pw-revealed-face:not([hidden]) [data-tarot-hide]').length===3);
 await app.locator('.st-key-forecast-details').waitFor({state:'visible'});
}
module.exports={choose,reveal};
