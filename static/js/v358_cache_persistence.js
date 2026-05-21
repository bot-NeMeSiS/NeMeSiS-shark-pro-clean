
(function(){
const key='nemesis_v358_cache_state';
function update(){
 if(!location.pathname.startsWith('/cliente')) return;
 let state={};
 try{state=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){}
 state.hits=(state.hits||0)+1;
 state.lastSync=new Date().toISOString();
 state.mode='smart-cache';
 localStorage.setItem(key,JSON.stringify(state));
 document.querySelectorAll('[data-v358-cache-hits]').forEach(e=>e.textContent=state.hits);
 document.querySelectorAll('[data-v358-last-sync]').forEach(e=>e.textContent='Ahora');
}
document.addEventListener('DOMContentLoaded',update);
})();
