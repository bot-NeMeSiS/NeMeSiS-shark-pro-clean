// NeMeSiS SHARK PRO · V338
// Live Match Center Feel + Smart Home Continuity

(function(){
  function isClient(){
    return location.pathname.startsWith('/cliente') || location.pathname.startsWith('/clientes');
  }

  function rotateSharkText(){
    if(!isClient()) return;
    const tips=[
      'Elige menos partidos si la confianza baja. Mejor control que rellenar por rellenar.',
      'Antes de hacer una Combi 1X2, revisa Live Focus y evita partidos con baja información.',
      'Si un partido entra en HOT, revisa contexto antes de apostar: no todo movimiento es value.',
      'SHARK prioriza claridad: stake pequeño, riesgo visible y decisión simple.'
    ];
    document.querySelectorAll('[data-v338-shark-tip]').forEach(function(el){
      el.textContent=tips[Math.floor(Math.random()*tips.length)];
    });
  }

  function rememberMatchFlow(){
    if(!isClient()) return;
    try{
      localStorage.setItem('nemesis_v338_last_flow', JSON.stringify({
        path:location.pathname,
        at:new Date().toISOString(),
        focus:'live_match_center'
      }));
    }catch(e){}
  }

  function addSubtleReadyState(){
    if(!isClient()) return;
    document.body.setAttribute('data-v338-live-ready','1');
  }

  document.addEventListener('DOMContentLoaded',function(){
    rememberMatchFlow();
    rotateSharkText();
    addSubtleReadyState();
  });
})();
