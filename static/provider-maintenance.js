(function(){
  'use strict';
  const tokenNode=document.querySelector('meta[name="csrf-token"]');
  const csrf=tokenNode ? tokenNode.getAttribute('content') : '';
  document.querySelectorAll('[data-provider-test]').forEach(function(button){
    button.addEventListener('click', async function(){
      const key=button.getAttribute('data-provider-test')||'';
      const url=button.getAttribute('data-provider-url')||'';
      const out=document.querySelector('[data-provider-result="'+key+'"]');
      if(!url || !window.fetch) return;
      button.disabled=true;
      button.setAttribute('aria-busy','true');
      if(out) out.textContent='Comprobando conexión con una única llamada…';
      try{
        const response=await fetch(url,{
          method:'POST',
          headers:{'Accept':'application/json','X-CSRF-Token':csrf},
          cache:'no-store',
          credentials:'same-origin'
        });
        const data=await response.json().catch(function(){return {};});
        const parts=[];
        parts.push(data.connected ? 'Conexión verificada' : (data.status||'No verificada'));
        if(data.plan) parts.push('Plan: '+data.plan);
        if(data.plan_active===true) parts.push('Activo');
        if(data.plan_active===false) parts.push('Inactivo');
        if(data.quota && typeof data.quota==='object'){
          const q=Object.entries(data.quota).filter(function(entry){return entry[1]!=='' && entry[1]!==null && entry[1]!==undefined;});
          if(q.length) parts.push('Cuota: '+q.map(function(entry){return entry[0]+'='+entry[1];}).join(' · '));
        }
        parts.push('Llamadas: '+String(data.external_calls||0));
        if(out) out.textContent=parts.join(' · ');
      }catch(_error){
        if(out) out.textContent='No se pudo verificar la conexión. No se repetirá automáticamente.';
      }finally{
        button.disabled=false;
        button.removeAttribute('aria-busy');
      }
    });
  });
})();