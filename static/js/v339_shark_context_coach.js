// NeMeSiS SHARK PRO · V339
// SHARK Context Coach + Decision 1X2

(function(){
  function isClient(){
    return location.pathname.startsWith('/cliente') || location.pathname.startsWith('/clientes');
  }

  function rotateCoachTip(){
    if(!isClient()) return;
    const tips = [
      'Para combinadas largas, evita meter partidos solo por completar número.',
      'Si dudas entre 1 y X, baja riesgo o espera confirmación live.',
      'Una cuota alta no siempre es value: revisa confianza, datos y contexto.',
      'La mejor combinada es la que no fuerza selecciones malas.'
    ];
    document.querySelectorAll('[data-v339-coach-tip]').forEach(function(el){
      el.textContent = tips[Math.floor(Math.random() * tips.length)];
    });
  }

  function saveDecisionFocus(){
    if(!isClient()) return;
    try{
      localStorage.setItem('nemesis_v339_decision_focus', JSON.stringify({
        focus:'1X2',
        updatedAt:new Date().toISOString()
      }));
    }catch(e){}
  }

  document.addEventListener('DOMContentLoaded', function(){
    rotateCoachTip();
    saveDecisionFocus();
  });
})();
