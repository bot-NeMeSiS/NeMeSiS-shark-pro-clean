(function(){
  'use strict';
  const panel=document.querySelector('[data-ns-pwa-install]');
  if(!panel) return;

  const primary=panel.querySelector('[data-ns-pwa-primary]');
  const actionButtons=[].slice.call(document.querySelectorAll('[data-ns-pwa-install-action],[data-ns-pwa-page-primary]'));
  const dismiss=panel.querySelector('[data-ns-pwa-dismiss]');
  const help=panel.querySelector('[data-ns-pwa-help]');
  const status=panel.querySelector('[data-ns-pwa-status]');
  const pageStatus=[].slice.call(document.querySelectorAll('[data-ns-pwa-page-status]'));
  const iconVersion=panel.getAttribute('data-icon-version')||'current';
  const DISMISS_KEY='nemesis-pwa-install-dismissed-'+iconVersion;
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
  function setStatus(value){
    if(status) status.textContent=value;
    pageStatus.forEach(function(node){node.textContent=value;});
  }
  function show(mode){
    if(standalone() || recentlyDismissed()) return;
    panel.hidden=false;
    panel.dataset.nsPwaMode=mode||'install';
    if(primary){
      primary.textContent=mode==='ios' ? 'Cómo añadir a inicio' : 'Instalar NeMeSiS';
    }
    setStatus(mode==='ios'
      ? 'En iPhone/iPad se instala desde Compartir → Añadir a pantalla de inicio.'
      : 'Se abrirá el instalador del navegador. No se descarga ningún archivo externo.');
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

  async function runInstall(){
    if(deferredPrompt){
      const promptEvent=deferredPrompt;
      deferredPrompt=null;
      try{
        await promptEvent.prompt();
        const choice=await promptEvent.userChoice;
        if(choice && choice.outcome==='accepted'){
          hide();
          setStatus('Instalación aceptada.');
          try{ localStorage.removeItem(DISMISS_KEY); }catch(_error){}
        }else{
          show('native');
          setStatus('Instalación cancelada; puedes intentarlo cuando quieras.');
        }
      }catch(_error){
        setStatus('Abre el menú del navegador y elige Instalar aplicación o Añadir a pantalla de inicio.');
      }
      return;
    }
    if(help){
      help.hidden=false;
      help.focus && help.focus();
    }
    setStatus(ios()
      ? 'Pulsa Compartir y después “Añadir a pantalla de inicio”.'
      : 'Abre el menú del navegador y elige “Instalar aplicación” o “Añadir a pantalla de inicio”.');
  }
  actionButtons.forEach(function(button){button.addEventListener('click',runInstall);});

  if(dismiss){
    dismiss.addEventListener('click',function(){
      try{ localStorage.setItem(DISMISS_KEY,String(Date.now())); }catch(_error){}
      hide();
    });
  }

  window.addEventListener('appinstalled',function(){
    hide();
    setStatus('NeMeSiS instalada correctamente.');
    try{ localStorage.removeItem(DISMISS_KEY); }catch(_error){}
  });
})();