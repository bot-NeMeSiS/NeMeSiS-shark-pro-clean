
(function(){
  function isClient(){
    return location.pathname.startsWith('/cliente') || location.pathname.startsWith('/clientes');
  }

  function rotateEmotion(){
    if(!isClient()) return;
    const lines=[
      '🔥 Hay movimiento: revisa Live antes de añadir a Combi.',
      '🦈 SHARK recomienda no forzar selecciones con baja confianza.',
      '⚡ Si dudas entre 1/X/2, espera más contexto o baja riesgo.',
      '🎯 Stake pequeño, decisión clara y combinada sin relleno.'
    ];
    document.querySelectorAll('[data-v343-emotion-line]').forEach(function(el){
      el.textContent=lines[Math.floor(Math.random()*lines.length)];
    });
  }

  function tactileFeedback(){
    document.querySelectorAll('.v343-action,.v343-live-chip,.v343-alert').forEach(function(el){
      el.addEventListener('click',function(){
        el.style.transform='scale(.985)';
        setTimeout(function(){el.style.transform=''},140);
      });
    });
  }

  function saveFeeling(){
    if(!isClient()) return;
    try{
      localStorage.setItem('nemesis_v343_last_emotion', JSON.stringify({
        at:new Date().toISOString(),
        focus:'emotional_live'
      }));
    }catch(e){}
  }

  document.addEventListener('DOMContentLoaded',function(){
    rotateEmotion();
    tactileFeedback();
    saveFeeling();
  });
})();
