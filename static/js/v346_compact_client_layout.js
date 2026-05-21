
(function(){
  function isClient(){
    return location.pathname.startsWith('/cliente') || location.pathname.startsWith('/clientes');
  }

  function initTabs(){
    document.querySelectorAll('[data-v346-tab]').forEach(function(btn){
      btn.addEventListener('click', function(){
        document.querySelectorAll('[data-v346-tab]').forEach(b=>b.classList.remove('active'));
        btn.classList.add('active');
        const target=btn.getAttribute('data-v346-tab');
        document.querySelectorAll('[data-v346-zone]').forEach(function(zone){
          zone.style.display = (target==='todo' || zone.getAttribute('data-v346-zone')===target) ? '' : 'none';
        });
      });
    });
  }

  function declutter(){
    if(!isClient()) return;
    document.body.classList.add('v346-client-declutter');
  }

  function rememberCompact(){
    if(!isClient()) return;
    try{localStorage.setItem('nemesis_v346_layout','compact')}catch(e){}
  }

  document.addEventListener('DOMContentLoaded',function(){
    declutter();
    initTabs();
    rememberCompact();
  });
})();
