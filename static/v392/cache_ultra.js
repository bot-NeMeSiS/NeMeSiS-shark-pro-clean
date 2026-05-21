
(async()=>{const box=document.querySelector('[data-v392-api]');if(!box)return;try{const r=await fetch('/api/v392/cache-ultra',{cache:'no-store'});const d=await r.json();box.textContent=JSON.stringify(d.totals,null,2)}catch(e){box.textContent='Cache Ultra preparado. Render puede tardar unos segundos en despertar.'}})();
