
(function(){
  function isClient(){return location.pathname.startsWith('/cliente')}
  function saveFlow(){
    if(!isClient()) return;
    try{
      localStorage.setItem('nemesis_v349_flow', JSON.stringify({
        step:'match_to_combi_to_shark_to_roi',
        at:new Date().toISOString()
      }));
    }catch(e){}
  }
  document.addEventListener('DOMContentLoaded',saveFlow);
})();
