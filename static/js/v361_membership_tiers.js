
(function(){
function saveTierFocus(){
 if(!location.pathname.startsWith('/cliente')) return;
 try{localStorage.setItem('nemesis_v361_tier_viewed',new Date().toISOString())}catch(e){}
}
document.addEventListener('DOMContentLoaded',saveTierFocus);
})();
