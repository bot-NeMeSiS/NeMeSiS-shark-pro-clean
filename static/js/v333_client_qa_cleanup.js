// NeMeSiS SHARK PRO · V333
// QA cleanup for client area. No toca app.py ni rutas críticas.

(function(){
  const bannedWords = [
    'revisar','review','debug','audit','moderation','moderación',
    'inspeccionar','qa interno','dev only','admin only','control técnico'
  ];

  function isClientArea(){
    return location.pathname.startsWith('/cliente') || location.pathname.startsWith('/clientes');
  }

  function isSafeAction(el){
    const text = (el.textContent || '').trim().toLowerCase();
    const href = (el.getAttribute('href') || '').toLowerCase();
    return href.includes('/logout') || href.includes('/ayuda') || href.includes('/perfil') ||
           text === 'cerrar sesión' || text === 'ayuda' || text === 'mi cuenta';
  }

  function cleanup(){
    if(!isClientArea()) return;
    document.querySelectorAll('a,button,[role="button"],.btn,.card').forEach(function(el){
      if(isSafeAction(el)) return;
      const text = (el.textContent || '').toLowerCase();
      const href = (el.getAttribute('href') || '').toLowerCase();
      const cls = (el.getAttribute('class') || '').toLowerCase();
      const haystack = text + ' ' + href + ' ' + cls;
      const shouldHide = bannedWords.some(function(word){ return haystack.includes(word); });
      if(shouldHide){
        el.style.display = 'none';
        el.setAttribute('data-v333-hidden-client-internal','1');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function(){
    cleanup();
    setTimeout(cleanup, 500);
    setTimeout(cleanup, 1600);
  });
})();
