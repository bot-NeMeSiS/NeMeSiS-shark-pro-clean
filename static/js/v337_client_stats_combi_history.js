// NeMeSiS SHARK PRO · V337
// Client Stats + Combi History Feel
// No toca APIs críticas. Usa localStorage visual hasta conectar histórico real.

(function(){
  const key = 'nemesis_v337_client_stats';

  function isClient(){
    return location.pathname.startsWith('/cliente') || location.pathname.startsWith('/clientes');
  }

  function getStats(){
    let data = {};
    try { data = JSON.parse(localStorage.getItem(key) || '{}'); } catch(e){}
    if(!data.ready){
      data = {
        ready:true,
        visits:0,
        combisViewed:0,
        lastMode:'Balanceado',
        lastStake:'0,10€',
        focus:'1X2'
      };
    }
    data.visits = (data.visits || 0) + 1;
    localStorage.setItem(key, JSON.stringify(data));
    return data;
  }

  function hydrateStats(){
    if(!isClient()) return;
    const data = getStats();

    document.querySelectorAll('[data-v337-stat="visits"]').forEach(el => el.textContent = data.visits);
    document.querySelectorAll('[data-v337-stat="mode"]').forEach(el => el.textContent = data.lastMode || 'Balanceado');
    document.querySelectorAll('[data-v337-stat="stake"]').forEach(el => el.textContent = data.lastStake || '0,10€');
    document.querySelectorAll('[data-v337-stat="focus"]').forEach(el => el.textContent = data.focus || '1X2');
  }

  function markCombiClicks(){
    if(!isClient()) return;
    document.querySelectorAll('a[href*="combi"]').forEach(function(a){
      a.addEventListener('click', function(){
        let data = getStats();
        data.combisViewed = (data.combisViewed || 0) + 1;
        localStorage.setItem(key, JSON.stringify(data));
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function(){
    hydrateStats();
    markCombiClicks();
  });
})();
