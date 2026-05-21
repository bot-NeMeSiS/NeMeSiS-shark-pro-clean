// V340 Smart Bet Slip + Combi Planner
(function(){
function q(s){return document.querySelector(s)} function qa(s){return Array.from(document.querySelectorAll(s))}
function calc(){
 const stake=parseFloat((q('[data-v340-stake]')||{}).value||'0.10')||0.10;
 const matches=parseInt((q('[data-v340-matches]')||{}).value||'6',10)||6;
 const mode=((q('[data-v340-risk]')||{}).value||'balanceado');
 let avgOdd=1.34; if(mode==='conservador') avgOdd=1.24; if(mode==='agresivo') avgOdd=1.48;
 const totalOdd=Math.pow(avgOdd,matches), retorno=stake*totalOdd;
 qa('[data-v340-total-odd]').forEach(el=>el.textContent=totalOdd.toFixed(2));
 qa('[data-v340-return]').forEach(el=>el.textContent=retorno.toFixed(2)+'€');
 qa('[data-v340-risk-label]').forEach(el=>el.textContent=mode.charAt(0).toUpperCase()+mode.slice(1));
 const copy=['SHARK COMBI 1X2','Partidos: '+matches,'Riesgo: '+mode,'Stake: '+stake.toFixed(2)+'€','Cuota estimada: '+totalOdd.toFixed(2),'Retorno posible: '+retorno.toFixed(2)+'€','','Selecciones sugeridas:','1) Local fuerte — 1','2) Partido equilibrado — X si hay value','3) Visitante con contexto — 2','','Nota: revisar siempre cuotas reales en la casa antes de apostar.'].join('\\n');
 qa('[data-v340-copy-text]').forEach(el=>el.textContent=copy);
}
function bind(){
 ['[data-v340-stake]','[data-v340-matches]','[data-v340-risk]'].forEach(sel=>{qa(sel).forEach(el=>el.addEventListener('input',calc));qa(sel).forEach(el=>el.addEventListener('change',calc));});
 qa('[data-v340-copy-btn]').forEach(btn=>btn.addEventListener('click',async function(){const text=(q('[data-v340-copy-text]')||{}).textContent||'';try{await navigator.clipboard.writeText(text);btn.textContent='Copiado ✅';setTimeout(()=>btn.textContent='Copiar combinada',1600)}catch(e){btn.textContent='Selecciona el texto';setTimeout(()=>btn.textContent='Copiar combinada',1600)}}));
}
document.addEventListener('DOMContentLoaded',function(){calc();bind()});
})();
