// NeMeSiS SHARK PRO · V336
// Client Delight + Live Mobile Polish

(function(){
  function isClient(){
    return location.pathname.startsWith('/cliente') || location.pathname.startsWith('/clientes');
  }

  function safeCleanup(){
    if(!isClient()) return;
    document.body.classList.add('v336-safe-client');
    const banned = ['debug','review','revisar','audit','moderación','moderation','qa interno','control técnico','admin only'];
    document.querySelectorAll('a,button,[role="button"],.btn').forEach(function(el){
      const text=(el.textContent||'').toLowerCase();
      const href=(el.getAttribute('href')||'').toLowerCase();
      const cls=(el.getAttribute('class')||'').toLowerCase();
      const safe=href.includes('/logout')||href.includes('/perfil')||href.includes('/ayuda')||text.trim()==='ayuda';
      if(!safe && banned.some(function(w){return (text+' '+href+' '+cls).includes(w)})){
        el.style.display='none';
        el.setAttribute('data-v336-hidden','1');
      }
    });
  }

  function addFloatingActions(){
    if(!isClient() || document.querySelector('.v336-floating-actions')) return;
    const nav=document.createElement('nav');
    nav.className='v336-floating-actions';
    nav.innerHTML='<a href="/cliente/live">Live</a><a class="primary" href="/cliente/combi-inteligente">Combi</a><a href="/cliente/shark-copilot">SHARK</a>';
    document.body.appendChild(nav);
  }

  function microToast(){
    if(!isClient() || window.innerWidth>780) return;
    if(sessionStorage.getItem('v336_toast_shown')) return;
    sessionStorage.setItem('v336_toast_shown','1');
    const el=document.createElement('div');
    el.style.cssText='position:fixed;left:12px;right:12px;bottom:92px;z-index:9998;background:rgba(4,10,20,.92);border:1px solid rgba(0,217,255,.18);color:#f6faff;border-radius:18px;padding:12px 14px;font-size:13px;box-shadow:0 16px 48px rgba(0,0,0,.35);';
    el.innerHTML='<b>🦈 SHARK listo</b><br><span style="opacity:.75">Live, Combi 1X2 y SHARK quedan siempre a mano.</span>';
    document.body.appendChild(el);
    setTimeout(function(){el.style.opacity='0';el.style.transition='opacity .35s ease';setTimeout(function(){el.remove()},420)},4200);
  }

  document.addEventListener('DOMContentLoaded',function(){
    safeCleanup();
    addFloatingActions();
    microToast();
    setTimeout(safeCleanup,800);
    setTimeout(safeCleanup,2000);
  });
})();
