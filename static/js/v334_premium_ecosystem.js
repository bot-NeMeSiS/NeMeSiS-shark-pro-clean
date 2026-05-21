// NeMeSiS SHARK PRO · V334
// Premium Ecosystem Polish: continuidad, limpieza cliente y app feel.

(function(){
  const key = 'nemesis_v334_session';

  function isClient(){
    return location.pathname.startsWith('/cliente') || location.pathname.startsWith('/clientes');
  }

  function markClientMode(){
    if(isClient()) document.body.classList.add('v334-client-mode');
  }

  function saveSession(){
    if(!isClient()) return;
    let data = {};
    try { data = JSON.parse(localStorage.getItem(key) || '{}'); } catch(e){}
    data.lastPath = location.pathname;
    data.lastVisit = new Date().toISOString();
    data.visits = (data.visits || 0) + 1;
    localStorage.setItem(key, JSON.stringify(data));
  }

  function hideClientTech(){
    if(!isClient()) return;
    const banned = ['debug','review','revisar','audit','moderación','moderation','qa interno','control técnico'];
    document.querySelectorAll('a,button,[role="button"],.btn').forEach(function(el){
      const txt = (el.textContent || '').toLowerCase();
      const href = (el.getAttribute('href') || '').toLowerCase();
      const cls = (el.getAttribute('class') || '').toLowerCase();
      const hay = txt + ' ' + href + ' ' + cls;
      const safe = href.includes('/logout') || href.includes('/perfil') || href.includes('/ayuda') || txt.trim()==='ayuda';
      if(!safe && banned.some(function(w){return hay.includes(w)})){
        el.style.display = 'none';
        el.setAttribute('data-v334-hidden','1');
      }
    });
  }

  function enhanceButtons(){
    document.querySelectorAll('a[href*="combi"],a[href*="live"],a[href*="shark"]').forEach(function(el){
      if(el.closest('.v334-premium-hero')) return;
      if(el.classList.contains('v334-btn')) return;
      el.classList.add('v334-soft-link');
    });
  }

  function sessionToast(){
    if(!isClient() || window.innerWidth > 780) return;
    let data = {};
    try { data = JSON.parse(localStorage.getItem(key) || '{}'); } catch(e){}
    if((data.visits || 0) < 2) return;
    if(document.querySelector('.v334-session-toast')) return;

    const toast = document.createElement('div');
    toast.className = 'v334-session-toast';
    toast.style.cssText = 'position:fixed;left:12px;right:12px;bottom:94px;z-index:9998;border:1px solid rgba(0,217,255,.18);background:rgba(4,10,20,.90);color:#f6faff;border-radius:18px;padding:12px 13px;box-shadow:0 16px 48px rgba(0,0,0,.35);font-family:Arial,sans-serif;font-size:13px;';
    toast.innerHTML = '<b>🦈 Sesión recuperada</b><br><span style="opacity:.75">Combi 1X2, Live y SHARK siguen a mano.</span>';
    document.body.appendChild(toast);
    setTimeout(function(){
      toast.style.opacity = '0';
      toast.style.transition = 'opacity .35s ease';
      setTimeout(function(){toast.remove();}, 420);
    }, 4200);
  }

  document.addEventListener('DOMContentLoaded', function(){
    markClientMode();
    saveSession();
    hideClientTech();
    enhanceButtons();
    sessionToast();
    setTimeout(hideClientTech, 700);
    setTimeout(hideClientTech, 2000);
  });
})();
