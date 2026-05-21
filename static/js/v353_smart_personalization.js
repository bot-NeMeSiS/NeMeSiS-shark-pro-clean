
(function(){
const key='nemesis_v353_profile';
function read(){try{return JSON.parse(localStorage.getItem(key)||'{}')}catch(e){return {}}}
function write(d){try{localStorage.setItem(key,JSON.stringify(d))}catch(e){}}
function zone(){
 const p=location.pathname;
 if(p.includes('combi')) return 'Combi';
 if(p.includes('live')) return 'Live';
 if(p.includes('shark')) return 'SHARK';
 if(p.includes('perfil')) return 'Perfil';
 return 'Home';
}
function update(){
 if(!location.pathname.startsWith('/cliente')) return;
 const d=read();
 d.visits=(d.visits||0)+1;
 d.lastZone=zone();
 d.preferredStake=d.preferredStake||'0,10€';
 d.preferredMode=d.preferredMode||'Balanceado';
 d.favoriteMarket=d.favoriteMarket||'1X2';
 write(d);
 document.querySelectorAll('[data-v353-visits]').forEach(e=>e.textContent=d.visits);
 document.querySelectorAll('[data-v353-zone]').forEach(e=>e.textContent=d.lastZone);
 document.querySelectorAll('[data-v353-stake]').forEach(e=>e.textContent=d.preferredStake);
 document.querySelectorAll('[data-v353-mode]').forEach(e=>e.textContent=d.preferredMode);
 document.querySelectorAll('[data-v353-market]').forEach(e=>e.textContent=d.favoriteMarket);
}
document.addEventListener('DOMContentLoaded',update);
})();
