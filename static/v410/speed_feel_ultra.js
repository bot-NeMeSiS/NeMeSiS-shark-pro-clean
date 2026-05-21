(function(){
  const root=document.documentElement;
  root.dataset.nemesisSpeedFeel='v410';
  document.querySelectorAll('details').forEach(d=>d.addEventListener('toggle',()=>{ if(d.open){ d.scrollIntoView({block:'nearest',behavior:'smooth'}); }}));
})();
