
(function(){
function notify(){
 if(!location.pathname.startsWith('/cliente')) return;
 if(sessionStorage.getItem('v354_alert')) return;
 sessionStorage.setItem('v354_alert','1');

 const el=document.createElement('div');
 el.style.cssText='position:fixed;right:14px;bottom:96px;z-index:9999;background:rgba(5,10,20,.96);border:1px solid rgba(255,77,109,.24);padding:14px 16px;border-radius:18px;color:#f6faff;box-shadow:0 16px 48px rgba(0,0,0,.35);max-width:280px;font-size:13px;';
 el.innerHTML='<b>🔥 Momentum SHARK</b><br><span style="opacity:.75">Partido HOT detectado en Live.</span>';
 document.body.appendChild(el);

 setTimeout(function(){
   el.style.transition='opacity .4s ease';
   el.style.opacity='0';
   setTimeout(()=>el.remove(),420);
 },4200);
}
document.addEventListener('DOMContentLoaded',notify);
})();
