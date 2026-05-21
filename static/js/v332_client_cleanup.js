// NeMeSiS SHARK PRO · V332
// Limpieza cliente: oculta botones internos/revisar/debug/admin en vistas cliente.
// Seguro: no toca login/admin/Telegram/webhooks.

(function(){
  const banned = [
    'revisar','review','debug','admin','audit','moderación','moderation',
    'inspeccionar','test interno','dev','qa','control técnico'
  ];

  function isClientArea(){
    return window.location.pathname.startsWith('/cliente') ||
           window.location.pathname.startsWith('/clientes');
  }

  function cleanClientButtons(){
    if(!isClientArea()) return;
    document.body.classList.add('v332-clean-client');

    document.querySelectorAll('a,button,[role="button"]').forEach(function(el){
      const text = (el.textContent || '').trim().toLowerCase();
      const href = (el.getAttribute('href') || '').toLowerCase();
      const data = Array.from(el.attributes || []).map(a => (a.name + '=' + a.value).toLowerCase()).join(' ');
      const haystack = text + ' ' + href + ' ' + data;

      const shouldHide = banned.some(function(word){ return haystack.includes(word); });

      // No ocultar enlaces normales de ayuda o logout.
      const safe = href.includes('/ayuda') || href.includes('/logout') || text === 'ayuda' || text === 'cerrar sesión';

      if(shouldHide && !safe){
        el.style.display = 'none';
        el.setAttribute('data-v332-hidden-client-internal','1');
      }
    });
  }

  function addMobileSticky(){
    if(!isClientArea()) return;
    if(document.querySelector('.v332-mobile-sticky')) return;

    const sticky = document.createElement('div');
    sticky.className = 'v332-mobile-sticky';
    sticky.innerHTML = '<a href="/cliente/combi-inteligente">Combi 1X2</a><a href="/cliente/live">Live</a>';
    document.body.appendChild(sticky);
  }

  document.addEventListener('DOMContentLoaded', function(){
    cleanClientButtons();
    addMobileSticky();
    setTimeout(cleanClientButtons, 800);
    setTimeout(cleanClientButtons, 2000);
  });
})();
