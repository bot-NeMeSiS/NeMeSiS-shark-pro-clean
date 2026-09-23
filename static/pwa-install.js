(function(){
  'use strict';
  const panel=document.querySelector('[data-ns-pwa-install]');
  if(!panel) return;

  const primary=panel.querySelector('[data-ns-pwa-primary]');
  const dismiss=panel.querySelector('[data-ns-pwa-dismiss]');
  const help=panel.querySelector('[data-ns-pwa-help]');
  const status=panel.querySelector('[data-ns-pwa-status]');
  const DISMISS_KEY='nemesis-pwa-install-dismissed-v1';
  const DISMISS_MS=7*24*60*60*1000;
  let deferredPrompt=null;

  function standalone(){
    return window.matchMedia && window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone===true;
  }
  function ios(){
    return /iphone|ipad|ipod/i.test(window.navigator.userAgent||'');
  }
  function recentlyDismissed(){
    try{
      const raw=parseInt(localStorage.getItem(DISMISS_KEY)||'0',10);
      return raw && (Date.now()-raw)<DISMISS_MS;
    }catch(_error){ return false; }
  }
  function show(mode){
    if(standalone() || recentlyDismissed()) return;
    panel.hidden=false;
    panel.dataset.nsPwaMode=mode||'install';
    if(primary){
      primary.textContent=mode==='ios' ? 'Cómo añadir a inicio' : 'Instalar NeMeSiS';
    }
    if(status){
      status.textContent=mode==='ios'
        ? 'En iPhone/iPad se instala desde Compartir → Añadir a pantalla de inicio.'
        : 'Se abrirá el instalador del navegador. No se descarga ningún archivo externo.';
    }
  }
  function hide(){
    panel.hidden=true;
    if(help) help.hidden=true;
  }

  if(standalone()){
    hide();
    return;
  }

  window.addEventListener('beforeinstallprompt',function(event){
    event.preventDefault();
    deferredPrompt=event;
    show('native');
  });

  if(ios()){
    window.setTimeout(function(){ show('ios'); },900);
  }

  if(primary){
    primary.addEventListener('click',async function(){
      if(deferredPrompt){
        const prompt=deferredPrompt;
        deferredPrompt=null;
        try{
          await prompt.prompt();
          const choice=await prompt.userChoice;
          if(choice && choice.outcome==='accepted'){
            hide();
            try{ localStorage.removeItem(DISMISS_KEY); }catch(_error){}
          }else{
            show('native');
          }
        }catch(_error){
          if(status) status.textContent='Abre el menú del navegador y elige Instalar aplicación o Añadir a pantalla de inicio.';
        }
        return;
      }
      if(help){
        help.hidden=false;
        help.focus && help.focus();
      }
      if(status){
        status.textContent=ios()
          ? 'Pulsa Compartir y después “Añadir a pantalla de inicio”.'
          : 'Abre el menú del navegador y elige “Instalar aplicación” o “Añadir a pantalla de inicio”.';
      }
    });
  }

  if(dismiss){
    dismiss.addEventListener('click',function(){
      try{ localStorage.setItem(DISMISS_KEY,String(Date.now())); }catch(_error){}
      hide();
    });
  }

  window.addEventListener('appinstalled',function(){
    hide();
    try{ localStorage.removeItem(DISMISS_KEY); }catch(_error){}
  });
})();