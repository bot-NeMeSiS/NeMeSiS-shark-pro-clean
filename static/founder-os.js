(function(){'use strict';var root=document.querySelector('[data-founder-os]');if(!root)return;var csrf=(document.querySelector('meta[name="csrf-token"]')||{}).content||'';var publicKey=root.getAttribute('data-vapid-public-key')||'';var statusEl=document.querySelector('[data-founder-push-status]');var deferredInstall=null;function setStatus(t){if(statusEl)statusEl.textContent=t;}function b64(v){var p='='.repeat((4-v.length%4)%4);var raw=atob((v+p).replace(/-/g,'+').replace(/_/g,'/'));var out=new Uint8Array(raw.length);for(var i=0;i<raw.length;i++)out[i]=raw.charCodeAt(i);return out;}function post(u,p){return fetch(u,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'Accept':'application/json'},body:JSON.stringify(p||{})}).then(function(r){return r.json().then(function(b){return{ok:r.ok,body:b};});});}window.addEventListener('beforeinstallprompt',function(e){e.preventDefault();deferredInstall=e;});var install=document.querySelector('[data-founder-install]');if(install)install.addEventListener('click',function(){if(deferredInstall){deferredInstall.prompt();deferredInstall.userChoice.finally(function(){deferredInstall=null;});return;}alert('En iPhone: Compartir → Añadir a pantalla de inicio. En Android/Chrome: menú → Instalar aplicación.');});var enable=document.querySelector('[data-founder-push-enable]');if(enable)enable.addEventListener('click',function(){if(!('serviceWorker'in navigator)||!('PushManager'in window)||!('Notification'in window)){setStatus('Este navegador no soporta Web Push.');return;}if(!publicKey){setStatus('Falta VAPID_PUBLIC_KEY.');return;}enable.disabled=true;setStatus('Solicitando permiso...');Notification.requestPermission().then(function(p){if(p!=='granted')throw new Error('Permiso no concedido');return navigator.serviceWorker.ready;}).then(function(reg){return reg.pushManager.getSubscription().then(function(s){return s||reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:b64(publicKey)});});}).then(function(sub){return post('/api/admin/founder-os/push/subscribe',sub.toJSON());}).then(function(r){if(!r.ok||!r.body.ok)throw new Error(r.body.error||'No se pudo registrar');setStatus('Push móvil activo en este dispositivo.');var t=document.querySelector('[data-founder-push-test]');if(t)t.disabled=false;}).catch(function(e){setStatus(e.message||'No se pudo activar push.');}).finally(function(){enable.disabled=false;});});var test=document.querySelector('[data-founder-push-test]');if(test)test.addEventListener('click',function(){test.disabled=true;setStatus('Enviando prueba...');post('/api/admin/founder-os/push/test',{}).then(function(r){setStatus(r.body&&r.body.sent?'Prueba enviada.':(r.body.status||'Sin entrega push.'));}).catch(function(){setStatus('No se pudo enviar la prueba.');}).finally(function(){test.disabled=false;});});
// A single editor supports explicit create/edit/cancel modes; GET links remain usable without JS.
(function obligationEditor() {
  var form=root.querySelector('[data-obligation-form]');
  if(!form)return;
  var fields=['id','provider_key','label','plan','amount','currency','cadence','due_date','payment_status','notes'];
  var defaults={id:'',provider_key:'render',label:'',plan:'',amount:'',currency:'EUR',cadence:'monthly',due_date:'',payment_status:'PENDING',notes:'',auto_renew:false};
  var details=form.closest('details');
  var title=root.querySelector('[data-obligation-editor-title]');
  var modeStatus=root.querySelector('[data-obligation-mode-status]');
  var cancel=root.querySelector('[data-obligation-reset]');
  var submit=form.querySelector('[data-obligation-submit]');
  function plainClick(event){return !event.defaultPrevented&&!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey&&event.button===0;}
  function show(values,editing,href){
    fields.forEach(function(name){
      var field=form.elements.namedItem(name);
      if(field)field.value=values[name]==null?'':values[name];
    });
    if(form.elements.auto_renew)form.elements.auto_renew.checked=values.auto_renew===true;
    form.dataset.obligationMode=editing?'edit':'new';
    if(title)title.textContent=editing?'Editar obligación':'Añadir obligación';
    if(modeStatus)modeStatus.textContent=editing?'Estás editando una obligación existente.':'Nueva obligación: se creará un registro independiente.';
    if(submit)submit.textContent=editing?'Guardar cambios':'Guardar obligación';
    if(cancel)cancel.hidden=!editing;
    root.querySelectorAll('[data-obligation-error]').forEach(function(error){error.hidden=true;});
    form.setAttribute('aria-describedby','founder-obligation-mode');
    if(details)details.open=true;
    // The address remains a real, read-only GET for reload and no-script recovery.
    try{window.history.replaceState(null,'',href);}catch(_){}
    var label=form.elements.namedItem('label');
    if(label){label.focus({preventScroll:true});label.scrollIntoView({block:'center'});}
  }
  root.querySelectorAll('[data-edit-obligation]').forEach(function(link){
    link.addEventListener('click',function(event){
      if(!plainClick(event))return;
      var item;
      try{item=JSON.parse(link.getAttribute('data-edit-obligation')||'{}');}catch(_){return;}
      if(!item||typeof item.id!=='string'||!item.id)return;
      event.preventDefault();show(item,true,link.href);
    });
  });
  root.querySelectorAll('[data-new-obligation],[data-obligation-reset]').forEach(function(link){
    link.addEventListener('click',function(event){
      if(!plainClick(event))return;
      event.preventDefault();show(defaults,false,link.href);
    });
  });
  var error=root.querySelector('[data-obligation-error]');
  function focusError(){
    if(!error||error.hidden)return;
    var active=document.activeElement;
    if(active&&active.matches('input,textarea,select,button,a'))return;
    error.focus({preventScroll:true});error.scrollIntoView({block:'center'});
  }
  // Initial fragment navigation runs after deferred scripts and can reset focus.
  if(document.readyState==='complete')focusError();
  else window.addEventListener('load',focusError,{once:true});
})();
})();
