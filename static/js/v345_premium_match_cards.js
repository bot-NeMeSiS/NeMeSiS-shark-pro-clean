
(function(){
  function isClient(){
    return location.pathname.startsWith('/cliente') || location.pathname.startsWith('/clientes');
  }

  function animateCards(){
    if(!isClient()) return;
    document.querySelectorAll('.v345-match-card').forEach(function(card,idx){
      card.style.opacity='0';
      card.style.transform='translateY(10px)';
      setTimeout(function(){
        card.style.transition='opacity .35s ease, transform .35s ease, border-color .22s ease, background .22s ease';
        card.style.opacity='1';
        card.style.transform='';
      }, 80 + idx*90);
    });
  }

  function saveCardFocus(){
    if(!isClient()) return;
    try{
      localStorage.setItem('nemesis_v345_match_cards_seen', new Date().toISOString());
    }catch(e){}
  }

  document.addEventListener('DOMContentLoaded',function(){
    animateCards();
    saveCardFocus();
  });
})();
