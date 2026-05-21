// V331 · Client Experience Cleanup
// Quita botones internos visibles por accidente en pantallas cliente. No afecta admin.
(function(){
  const clientPath = location.pathname.startsWith('/cliente') || location.pathname.startsWith('/clientes');
  if(!clientPath) return;
  const badExact = ['revisar','review','debug','admin','moderation','auditar'];
  const badContains = ['admin only','solo admin','modo debug','debug mode','internal review','developer','endpoint'];
  function clean(){
    document.querySelectorAll('a,button').forEach(function(el){
      const txt=(el.textContent||'').trim().toLowerCase();
      const href=(el.getAttribute('href')||'').toLowerCase();
      const cls=(el.className||'').toString().toLowerCase();
      const isAdminHref = href.includes('/admin') || href.includes('debug') || href.includes('audit');
      const isInternalClass = cls.includes('admin') || cls.includes('debug') || cls.includes('review-only') || cls.includes('dev-only');
      const isBadExact = badExact.includes(txt);
      const isBadContains = badContains.some(function(w){return txt.includes(w)});
      if(isAdminHref || isInternalClass || isBadExact || isBadContains){ el.style.display='none'; el.setAttribute('aria-hidden','true'); }
    });
  }
  document.addEventListener('DOMContentLoaded', clean);
  setTimeout(clean, 800);
})();
