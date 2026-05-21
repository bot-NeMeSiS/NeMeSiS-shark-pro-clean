
(function(){
function isClient(){return location.pathname.startsWith('/cliente')}
function toast(){
 if(!isClient()) return;
 if(sessionStorage.getItem('v360_alert_shown')) return;
 sessionStorage.setItem('v360_alert_shown','1');
 const el=document.createElement('div');
 el.style.cssText='position:fixed;right:14px;bottom:96px;z-index:9999;background:rgba(5,10,20,.96);border:1px solid rgba(255,77,109,.24);padding:14px 16px;border-radius:18px;color:#f6faff;box-shadow:0 16px 48px rgba(0,0,0,.35);max-width:300px;font-size:13px;';
 el.innerHTML='<b>🚨 SHARK Alertas listas</b><br><span style="opacity:.75">Partidos HOT, combis en riesgo y avisos Telegram preparados.</span>';
 document.body.appendChild(el);
 setTimeout(()=>{el.style.transition='opacity .4s ease';el.style.opacity='0';setTimeout(()=>el.remove(),420)},4500);
}
function save(){
 try{localStorage.setItem('nemesis_v360_alerts_ready',new Date().toISOString())}catch(e){}
}
document.addEventListener('DOMContentLoaded',()=>{toast();save();});
})();
