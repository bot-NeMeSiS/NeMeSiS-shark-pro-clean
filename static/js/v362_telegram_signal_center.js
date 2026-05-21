
(function(){
function save(){
 if(!location.pathname.startsWith('/cliente')) return;
 try{localStorage.setItem('nemesis_v362_telegram_signal_center','ready')}catch(e){}
}
document.addEventListener('DOMContentLoaded',save);
})();
