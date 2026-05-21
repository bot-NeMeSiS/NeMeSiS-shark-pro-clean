
(function(){
  function txt(el){return (el&&el.innerText||'').toLowerCase().replace(/\s+/g,' ').trim();}
  function visible(el){if(!el) return false; const s=getComputedStyle(el); const r=el.getBoundingClientRect(); return s.display!=='none'&&s.visibility!=='hidden'&&r.width>20&&r.height>20;}
  function cleanupBottomNav(){
    if(!matchMedia('(max-width: 768px)').matches) return;
    const selectors=['.bottom-nav','.mobile-bottom-nav','.bottom-navigation','.tabbar','.mobile-tabbar','[data-mobile-nav="bottom"]','nav'];
    const nodes=[...new Set(selectors.flatMap(q=>Array.from(document.querySelectorAll(q))))]
      .filter(el=>visible(el))
      .filter(el=>{const r=el.getBoundingClientRect(); const t=txt(el); return r.bottom>innerHeight-140 && (getComputedStyle(el).position==='fixed'||getComputedStyle(el).position==='sticky'||t.includes('inicio')||t.includes('live')||t.includes('picks')||t.includes('combi')||t.includes('cuenta'));})
      .sort((a,b)=>b.getBoundingClientRect().bottom-a.getBoundingClientRect().bottom);
    if(nodes.length>1){nodes.slice(1).forEach(el=>el.classList.add('v377-hidden-duplicate')); nodes[0].setAttribute('data-v377-primary-bottom-nav','true');}
  }
  function cleanupAiButtons(){
    if(!matchMedia('(max-width: 768px)').matches) return;
    const nodes=[...document.querySelectorAll('.shark-ai-float,.ai-float,.shark-chat-fab,.floating-ai,.chat-fab,[data-ai-float="true"],button,a')]
      .filter(el=>visible(el))
      .filter(el=>{const t=txt(el); const r=el.getBoundingClientRect(); return (t.includes('shark')||t==='ai'||t.includes('ia')) && r.right>innerWidth-150 && r.bottom>innerHeight-220;})
      .sort((a,b)=>b.getBoundingClientRect().width*b.getBoundingClientRect().height-a.getBoundingClientRect().width*a.getBoundingClientRect().height);
    if(nodes.length>1){nodes.slice(1).forEach(el=>el.classList.add('v377-hidden-duplicate')); nodes[0].setAttribute('data-v377-primary-ai','true');}
  }
  function run(){cleanupBottomNav();cleanupAiButtons();}
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',run); else run();
  setTimeout(run,350); setTimeout(run,1200);
  new MutationObserver(()=>setTimeout(run,50)).observe(document.documentElement,{childList:true,subtree:true});
})();
