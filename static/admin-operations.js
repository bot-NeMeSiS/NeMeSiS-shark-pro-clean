/* Local filters/briefs plus guarded existing diagnostic actions. No background polling. */
(() => {
  'use strict';
  const root = document.querySelector('.operations-center-v1');
  if (!root) return;
  const fold = (s) => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const bench = root.querySelector('[data-admin-workbench]');
  const invalidateWorkbench = () => {
    if (!bench) return;
    bench.dataset.readingState = 'stale';
    const notice = bench.querySelector('[data-workbench-stale]');
    if (notice) notice.hidden = false;
    bench.querySelectorAll('[data-action="admin-copy-brief"], textarea').forEach(el => { el.disabled = true; });
    bench.querySelectorAll('[data-copy-result]').forEach(el => { el.textContent = 'Lectura anterior. Actualiza la bandeja antes de preparar una tarea.'; });
  };
  if (bench) {
    const items = [...bench.querySelectorAll('[data-admin-task]')];
    const search = bench.querySelector('[data-task-search]');
    const category = bench.querySelector('[data-task-category]');
    const priority = bench.querySelector('[data-task-priority]');
    const filter = () => {
      let visible = 0;
      items.forEach((item) => {
        const urgent = ['critical','high'].includes(item.dataset.priority);
        item.hidden = !fold(item.dataset.searchText).includes(fold(search.value)) ||
          (category.value !== 'all' && category.value !== item.dataset.category) ||
          (priority.value === 'urgent' && !urgent) || (priority.value === 'other' && urgent);
        if (!item.hidden) visible++;
      });
      bench.querySelector('[data-admin-task-count]').textContent = `${visible} de ${items.length} tareas visibles de esta lectura.`;
      bench.querySelector('[data-admin-task-empty]').hidden = visible !== 0 || items.length === 0;
    };
    bench.querySelector('[data-admin-task-filters]').hidden = false;
    [search,category,priority].forEach((el) => el.addEventListener('input',filter));
    bench.querySelector('[data-action="admin-reset-filters"]').addEventListener('click',() => {
      search.value='';category.value='all';priority.value='all';filter();search.focus();
    });
    bench.querySelector('[data-admin-tool-filter]').hidden=false;
    bench.querySelector('[data-tool-search]').addEventListener('input',(e) => {
      let count=0;
      bench.querySelectorAll('[data-admin-tool]').forEach((link)=>{
        link.hidden=!fold(link.textContent).includes(fold(e.target.value));if(!link.hidden) count++;
      });
      bench.querySelector('[data-admin-tool-empty]').hidden=count!==0;
    });
    bench.querySelectorAll('[data-action="admin-copy-brief"]').forEach((button)=>{
      button.hidden=false;
      button.addEventListener('click',async()=>{
        if (button.disabled || bench.dataset.readingState === 'stale') return;
        const box=button.closest('details'), field=box.querySelector('textarea'), status=box.querySelector('[data-copy-result]');
        try {
          if(!navigator.clipboard) throw new Error('clipboard_unavailable');
          await navigator.clipboard.writeText(field.value);
          status.textContent='Tarea copiada. La incidencia sigue pendiente y no se ha ejecutado ninguna acción.';
        } catch (_) {
          field.focus();field.select();status.textContent='No se pudo copiar automáticamente. Copia el texto seleccionado con el menú del dispositivo.';
        }
      });
    });
  }
  // Opening a link to a collapsed diagnostic must reveal its actual destination.
  const reveal = () => {
    const hash=window.location.hash.slice(1);if(!hash)return;
    const target=document.getElementById(hash);if(!target)return;
    for(let node=target;node && node!==root;node=node.parentElement) if(node.tagName==='DETAILS')node.open=true;
  };
  root.querySelectorAll('a[href^="#"]').forEach(link=>link.addEventListener('click',()=>setTimeout(reveal,0)));
  window.addEventListener('hashchange',reveal);reveal();
  let pending=false, invalidated=false;
  const buttons=[...root.querySelectorAll('[data-v938-action][data-action="admin-operation"]')];
  const initial=new Map(buttons.map(b=>[b,b.disabled]));
  const output=root.querySelector('[data-v938-output]');
  const refresh=root.querySelector('[data-admin-refresh]');
  root.querySelectorAll('[data-admin-refresh], [data-workbench-stale] a').forEach(link => {
    link.addEventListener('click', event => {
      const target = new URL(link.href, window.location.href);
      if (target.pathname === window.location.pathname && target.search === window.location.search) {
        event.preventDefault();
        window.location.hash = target.hash;
        window.location.reload();
      }
    });
  });
  buttons.forEach(button=>button.addEventListener('click',async()=>{
    if(pending || invalidated || button.disabled)return;
    const kind=button.dataset.v938Action;
    if(!['scan','prompt'].includes(kind))return;
    const expected=root.dataset.operationsNextIssue || '';
    if(kind==='prompt'&&!expected)return;
    if(typeof window.nemesisJsonHeaders!=='function'){
      invalidateWorkbench();
      output.textContent='La sesión no permite preparar la solicitud. Recarga la página.';refresh.hidden=false;return;
    }
    pending=true;buttons.forEach(b=>{b.disabled=true;b.setAttribute('aria-busy','true');});
    if (kind === 'scan') invalidateWorkbench();
    output.textContent='Comprobando la lectura local. No se ejecutan operaciones externas.';
    const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),20000);
    try {
      const response=await fetch('/api/admin/operations-center/'+(kind==='prompt'?'generate-prompt':'run-safe-scan'),{
        method:'POST',headers:window.nemesisJsonHeaders(),cache:'no-store',credentials:'same-origin',
        body:JSON.stringify(kind==='prompt'?{issue_id:expected}:{}),signal:controller.signal});
      if(response.redirected || !response.ok || !(response.headers.get('Content-Type')||'').includes('application/json')) throw new Error('unverified_response');
      const payload=await response.json();
      if(payload.ok!==true)throw new Error('unverified_response');
      if(kind==='prompt'){
        if(!payload.issue || payload.issue.issue_id!==expected || typeof payload.prompt!=='string' || !payload.prompt.trim())throw new Error('changed_issue');
        output.textContent=payload.prompt;
      } else {
        if(!payload.snapshot || !Array.isArray(payload.snapshot.incidents))throw new Error('unverified_response');
        invalidated=true;
        output.textContent=`Diagnóstico guardado: ${payload.snapshot.incidents.length} hallazgos en esa lectura. Actualiza la bandeja para trabajar con ellos; la lista visible aún corresponde a la lectura anterior.`;
        refresh.hidden=false;
      }
    } catch (_) {
      invalidated=true;
      invalidateWorkbench();
      output.textContent='No se pudo confirmar el resultado. La operación podría haberse recibido. No se reintentó automáticamente: actualiza la bandeja y revisa antes de repetir.';
      refresh.hidden=false;
    } finally {
      clearTimeout(timer);pending=false;
      buttons.forEach(b=>{b.disabled=invalidated||initial.get(b);b.removeAttribute('aria-busy');});
    }
  }));
})();
