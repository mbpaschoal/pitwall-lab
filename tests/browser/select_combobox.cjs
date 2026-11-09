/* Wait for smooth viewport movement before opening a React Aria listbox. */
async function selectComboboxOption(surface, input, name, {filter = false} = {}) {
 await input.scrollIntoViewIfNeeded();
 await input.evaluate(element=>new Promise((resolve,reject)=>{
  const started=performance.now();let previous='',stableSince=started;
  function sample(now){
   const box=element.getBoundingClientRect();
   const position=[box.x,box.y,box.width,box.height].join(',');
   if(position!==previous){previous=position;stableSince=now;}
   if(now-stableSince>=250)return resolve();
   if(now-started>10000)return reject(Error('Combobox viewport did not settle'));
   requestAnimationFrame(sample);
  }
  requestAnimationFrame(sample);
 }));
 if(await input.getAttribute('aria-expanded')!=='true')await input.click();
 if(filter)await input.fill(name);
 await surface.getByRole('option',{name,exact:true}).click();
}
module.exports={selectComboboxOption};
