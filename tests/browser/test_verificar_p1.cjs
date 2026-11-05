const {test}=require('node:test'),assert=require('node:assert/strict');
const {checkPlot}=require('./verificar_p1.cjs');
const expected=Array.from({length:22},(_,i)=>({id:'driver-'+i,name:'Driver '+i,probability:(i+1)/100}));
const trace=()=>({type:'bar',orientation:'h',y:expected.map(r=>r.name),x:expected.map(r=>100*r.probability)});
test('all displayed probabilities match exact source rows, including reordered charts',()=>{
 const t=trace();t.x.reverse();t.y.reverse();assert.equal(checkPlot([t],expected),22);
});
test('foreign driver, missing row, altered value and ambiguous chart are rejected',()=>{
 for(const alter of [t=>t.y[0]='Foreign driver',t=>t.y.pop(),t=>t.x[8]+=0.01,t=>t.y[0]=t.y[1]]){
  const t=trace();alter(t);assert.throws(()=>checkPlot([t],expected));
 }
 assert.throws(()=>checkPlot([trace(),trace()],expected));
});
