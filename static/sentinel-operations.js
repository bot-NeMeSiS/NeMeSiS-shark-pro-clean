/* Durable server jobs; localStorage is not the source of truth. */
(() => {
  const panel = document.querySelector('[data-sentinel-jobs]');
  if (!panel || panel.dataset.bound) return;
  panel.dataset.bound = 'true';
  const button = panel.querySelector('[data-request-review]');
  const list = panel.querySelector('[data-job-list]');
  const detail = panel.querySelector('[data-job-detail]');
  const message = panel.querySelector('[data-job-message]');
  const executor = panel.querySelector('[data-executor-state]');
  const labels = {QUEUED:'En cola', RUNNING:'En ejecución', COMPLETED:'Revisión terminada', FAILED:'Revisión fallida', INTERRUPTED:'Ejecución interrumpida'};
  const errors = {execution_interrupted:'Ejecución interrumpida; resultado no confirmado.', source_revision_changed:'La revisión local cambió; este resultado no se certifica.', executor_failed_or_timed_out:'El ejecutor falló o agotó su plazo.', executor_result_unavailable:'No se pudo verificar la evidencia.'};
  const madrid = value => value == null ? 'Pendiente' : new Intl.DateTimeFormat('es-ES', {timeZone:'Europe/Madrid', dateStyle:'short', timeStyle:'medium'}).format(new Date(value * 1000));
  const initialJob = new URL(location.href).searchParams.get('job');
  let selected = /^[a-f0-9]{32}$/.test(initialJob || '') ? initialJob : null;
  let sending = false, connected = false, requestKey = null, timer = null, generation = 0;
  function selectJob(id) {
    selected = id;
    const url = new URL(location.href);
    url.searchParams.set('job', id);
    history.replaceState(null, '', url);
  }
  function element(tag, text) { const node = document.createElement(tag); node.textContent = text; return node; }
  function field(title, value) { const row = element('div',''); row.append(element('dt',title),element('dd',value)); return row; }
  function show(job) {
    selectJob(job.id);
    const facts = element('dl','');
    facts.append(field('Trabajo',job.id),field('Estado',labels[job.state] || 'Estado desconocido'),field('Entorno',job.environment),field('Ámbito','Presencia de ocho plantillas cliente y decisión de publicación visible en SHARK'),field('Ejecutor','Product Experience Worker'),field('Intento',String(job.attempt)),field('Solicitado (Madrid)',madrid(job.created)),field('Inicio (Madrid)',madrid(job.started)),field('Fin (Madrid)',madrid(job.finished)),field('Revisión SHA-256',job.revision));
    const contents = [element('h3','Revisión de superficies cliente'),facts];
    const lifecycle = element('ol','');
    lifecycle.dataset.jobLifecycle = '';
    if (job.created != null) lifecycle.append(element('li',`En cola · ${madrid(job.created)}`));
    if (job.started != null) lifecycle.append(element('li',`En ejecución · ${madrid(job.started)}`));
    if (job.finished != null) lifecycle.append(element('li',`${labels[job.state] || 'Estado desconocido'} · ${madrid(job.finished)}`));
    contents.push(element('h4','Recorrido confirmado (Madrid)'),lifecycle);
    if (job.result) {
      const count = job.result.findings.length;
      contents.push(element('h4',`${count} hallazgos en el ámbito inspeccionado`));
      contents.push(element('p',`${job.result.metrics.client_surfaces_present} de 8 plantillas presentes. No se han probado sus recorridos con esta revisión.`));
      const evidence = element('ul','');
      job.result.scope.forEach(name => evidence.append(element('li',name)));
      contents.push(evidence);
      job.result.findings.forEach(f => contents.push(element('p',`${f.priority}: ${f.type}. ${f.evidence}`)));
      contents.push(element('p',count ? 'Siguiente acción: revisar los hallazgos; ninguna incidencia se ha cerrado.' : 'Siguiente acción: revisar navegación, datos y composición por separado.'));
    } else if (job.error) {
      contents.push(element('p',errors[job.error] || 'Resultado no confirmado. Revisión manual necesaria; sin reintento automático.'));
    } else {
      contents.push(element('p','Resultado pendiente. Puedes volver a esta pantalla sin cancelar el trabajo.'));
    }
    detail.replaceChildren(...contents);
  }
  async function request(url, options = {}) {
    const controller = new AbortController();
    const deadline = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(url, {...options, signal:controller.signal, credentials:'same-origin', cache:'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } finally { clearTimeout(deadline); }
  }
  async function refresh() {
    clearTimeout(timer);
    const current = ++generation;
    try {
      const data = await request('/api/admin/sentinel/jobs');
      if (current !== generation) return;
      connected = data.executor_connected;
      executor.textContent = connected ? 'Product Experience Worker conectado · LOCAL ONLY' : 'Ejecutor no conectado';
      const ids = new Set(data.jobs.map(job => job.id));
      for (const node of [...list.children]) if (!ids.has(node.dataset.jobId)) node.remove();
      data.jobs.forEach(job => {
        let entry = [...list.children].find(node => node.dataset.jobId === job.id);
        if (!entry) { entry=element('button',''); entry.type='button'; entry.dataset.jobId=job.id; entry.addEventListener('click',() => { selectJob(job.id); refresh(); }); list.append(entry); }
        entry.textContent = `${labels[job.state] || job.state} · ${madrid(job.created)}`;
        entry.setAttribute('aria-pressed',String(job.id === (selected || data.jobs[0]?.id)));
      });
      let job = selected ? data.jobs.find(item => item.id === selected) : data.jobs[0];
      if (selected && !job) {
        try {
          job = (await request(`/api/admin/sentinel/jobs/${encodeURIComponent(selected)}`)).job;
        } catch (_) {
          if (current === generation) detail.replaceChildren(element('p','Trabajo seleccionado no disponible para esta sesión. No se ha sustituido por otro.'));
          return;
        }
      }
      if (current !== generation) return;
      if (job) show(job); else detail.replaceChildren(element('p','Todavía no has solicitado revisiones.'));
    } catch (_) {
      if (current !== generation) return;
      connected = false;
      executor.textContent = 'Ejecutor no conectado o consulta no disponible. El estado del trabajo no se ha cambiado.';
    } finally {
      if (current === generation) { button.disabled = sending || !connected; timer=setTimeout(refresh, 3000); }
    }
  }
  button.addEventListener('click',async () => {
    if (sending || !connected) return;
    sending=true; button.disabled=true;
    ++generation;
    clearTimeout(timer);
    requestKey ||= crypto.randomUUID();
    message.textContent='Registrando solicitud';
    try {
      const data=await request('/api/admin/sentinel/jobs',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':panel.dataset.csrf},body:JSON.stringify({action:'product_surface_review',parameters:{scope:'client_templates'},request_key:requestKey})});
      show(data.job);
      message.textContent=data.reused ? 'Trabajo existente recuperado para el mismo ámbito y revisión.' : 'Solicitud registrada. Pendiente de ejecución.';
      requestKey=null;
    } catch (_) { message.textContent='Respuesta no confirmada. Consulta los trabajos antes de repetir; un timeout no cancela la ejecución.'; }
    finally { sending=false; await refresh(); }
  });
  window.addEventListener('pagehide',() => clearTimeout(timer));
  window.addEventListener('pageshow',refresh);
})();

/* This is a read-only view of CODEX_QUEUE, not a second queue or executor. */
(() => {
  const panel = document.querySelector('[data-project-control]');
  const search = panel?.querySelector('[data-project-search]');
  if (!search) return;
  const filter = panel.querySelector('[data-project-filter]');
  const rows = [...panel.querySelectorAll('[data-project-row]')];
  function applyFilter() {
    const query = search.value.trim().toLocaleLowerCase('es');
    let count = 0;
    rows.forEach(row => {
      const mode = filter.value;
      const matches = mode === 'all' || row.dataset.state === mode ||
        (mode === 'active' && ['READY','IN_PROGRESS','QA','PRODUCTION_VALIDATION'].includes(row.dataset.state)) ||
        (mode === 'unassigned' && row.dataset.owner === 'UNASSIGNED') ||
        (mode === 'publication' && row.dataset.publication === 'yes');
      row.hidden = !matches || !row.textContent.toLocaleLowerCase('es').includes(query);
      if (!row.hidden) count++;
    });
    panel.querySelector('[data-project-count]').textContent = `${count} trabajos visibles`;
  }
  search.addEventListener('input',applyFilter);
  filter.addEventListener('change',applyFilter);
  let sourceRequest = 0;
  panel.querySelectorAll('[data-control-source]').forEach(button => button.addEventListener('click',async () => {
    const current = ++sourceRequest;
    const viewer = panel.querySelector('[data-control-evidence]');
    const path = viewer.querySelector('[data-control-source-path]');
    const text = viewer.querySelector('[data-control-source-text]');
    viewer.hidden = false;
    path.textContent = 'Consultando fuente'; text.textContent = '';
    try {
      const response = await fetch(`/api/admin/sentinel/project-control/sources/${encodeURIComponent(button.dataset.controlSource)}`,{credentials:'same-origin',cache:'no-store'});
      if (!response.ok) throw new Error('unavailable');
      const data = await response.json();
      if (current !== sourceRequest) return;
      path.textContent = data.path; text.textContent = data.content;
    } catch (_) {
      if (current !== sourceRequest) return;
      path.textContent = 'Fuente no disponible. Ningún estado ha sido modificado.';
    }
    if (current === sourceRequest) viewer.querySelector('h3').focus();
  }));
})();
