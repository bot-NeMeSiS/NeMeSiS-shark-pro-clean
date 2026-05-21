
(async()=>{const nodes=document.querySelectorAll('[data-v389-api]');for(const n of nodes){try{const r=await fetch(n.dataset.v389Api,{cache:'no-store'});const d=await r.json();n.textContent=JSON.stringify(d.readiness||d,null,2)}catch(e){n.textContent='SHARK Admin God Mode: datos preparados, recarga si Render tarda en despertar.'}}})();
