
(async()=>{for(const n of document.querySelectorAll('[data-v390-api]')){try{const r=await fetch(n.dataset.v390Api,{cache:'no-store'});const d=await r.json();n.textContent=JSON.stringify(d.totals||d,null,2)}catch(e){n.textContent='Analytics históricos preparados. Render puede tardar unos segundos en despertar.'}}})();
