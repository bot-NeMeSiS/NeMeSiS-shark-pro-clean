
(function(){
  const key='nemesis_v344_session_memory';

  function isClient(){
    return location.pathname.startsWith('/cliente') || location.pathname.startsWith('/clientes');
  }

  function read(){
    try{return JSON.parse(localStorage.getItem(key)||'{}')}catch(e){return {}}
  }

  function write(data){
    try{localStorage.setItem(key,JSON.stringify(data))}catch(e){}
  }

  function detectZone(){
    const p=location.pathname;
    if(p.includes('combi')) return 'Combi 1X2';
    if(p.includes('live')) return 'Live';
    if(p.includes('shark')) return 'SHARK';
    if(p.includes('perfil')) return 'Perfil';
    return 'Home';
  }

  function save(){
    if(!isClient()) return;
    const data=read();
    data.lastPath=location.pathname;
    data.lastZone=detectZone();
    data.lastVisit=new Date().toISOString();
    data.visits=(data.visits||0)+1;
    write(data);
  }

  function hydrate(){
    if(!isClient()) return;
    const data=read();
    document.querySelectorAll('[data-v344-last-zone]').forEach(el=>el.textContent=data.lastZone||'Home');
    document.querySelectorAll('[data-v344-visits]').forEach(el=>el.textContent=data.visits||1);
    document.querySelectorAll('[data-v344-last-path]').forEach(el=>el.setAttribute('href',data.lastPath||'/cliente'));
  }

  function toast(){
    if(!isClient() || window.innerWidth>860) return;
    const data=read();
    if((data.visits||0)<2) return;
    if(sessionStorage.getItem('v344_toast')) return;
    sessionStorage.setItem('v344_toast','1');
    const el=document.createElement('div');
    el.style.cssText='position:fixed;left:12px;right:12px;bottom:94px;z-index:9998;background:rgba(4,10,20,.92);border:1px solid rgba(0,217,255,.18);color:#f6faff;border-radius:18px;padding:12px 14px;font-size:13px;box-shadow:0 16px 48px rgba(0,0,0,.35);';
    el.innerHTML='<b>🦈 Continuidad SHARK</b><br><span style="opacity:.75">Última zona: '+(data.lastZone||'Home')+'</span>';
    document.body.appendChild(el);
    setTimeout(()=>{el.style.opacity='0';el.style.transition='opacity .35s ease';setTimeout(()=>el.remove(),420)},4200);
  }

  document.addEventListener('DOMContentLoaded',function(){
    save();
    hydrate();
    toast();
  });
})();
