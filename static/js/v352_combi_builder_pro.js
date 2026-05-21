
(function(){
function q(s){return document.querySelector(s)}
function qa(s){return Array.from(document.querySelectorAll(s))}
function calc(){
 const matches=parseInt((q('[data-v352-matches]')||{}).value||'9',10);
 const stake=parseFloat((q('[data-v352-stake]')||{}).value||'0.10');
 const mode=((q('[data-v352-mode]')||{}).value||'balanceado');
 let base=72;if(mode==='conservador')base=84;if(mode==='agresivo')base=58;
 const penalty=Math.max(0,(matches-8)*4);
 const score=Math.max(18,base-penalty);
 let risk='Medio';if(score>=76)risk='Controlado';if(score<55)risk='Alto';
 let oddBase=mode==='conservador'?1.23:mode==='agresivo'?1.52:1.34;
 const odd=Math.pow(oddBase,matches), ret=stake*odd;
 qa('[data-v352-score]').forEach(e=>e.textContent=score);
 qa('[data-v352-risk]').forEach(e=>e.textContent=risk);
 qa('[data-v352-odd]').forEach(e=>e.textContent=odd.toFixed(2));
 qa('[data-v352-return]').forEach(e=>e.textContent=ret.toFixed(2)+'€');
 qa('[data-v352-fill]').forEach(e=>e.style.width=score+'%');
}
document.addEventListener('DOMContentLoaded',function(){
 ['[data-v352-matches]','[data-v352-stake]','[data-v352-mode]'].forEach(sel=>qa(sel).forEach(el=>{el.addEventListener('input',calc);el.addEventListener('change',calc)}));
 calc();
});
})();
