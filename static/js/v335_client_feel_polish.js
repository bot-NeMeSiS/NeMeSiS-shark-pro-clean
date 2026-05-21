
(function(){
  function injectSharkHints(){
    if(document.querySelector('.v335-shark-hint')) return;
    const hints=[
      '⚡ Partido entrando en fase caliente',
      '🦈 SHARK detecta movimiento interesante',
      '🔥 Mucho ritmo en este partido',
      '📈 Combinada activa preparada'
    ];
    const el=document.createElement('div');
    el.className='v335-shark-hint';
    el.style.cssText='position:fixed;right:14px;bottom:110px;z-index:9998;background:rgba(4,10,20,.92);color:#fff;border:1px solid rgba(0,217,255,.18);padding:12px 14px;border-radius:18px;font-size:13px;max-width:260px;';
    el.innerHTML='<strong>SHARK Live</strong><br>'+hints[Math.floor(Math.random()*hints.length)];
    document.body.appendChild(el);
    setTimeout(()=>el.remove(),4500);
  }
  document.addEventListener('DOMContentLoaded',()=>{
    if(window.location.pathname.startsWith('/cliente')){
      setTimeout(injectSharkHints,1800);
    }
  });
})();
