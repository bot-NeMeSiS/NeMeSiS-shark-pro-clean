/* All mutations require a server proposal and a separate human approval. */
(() => {
  'use strict';
  // Same local-only filtering in the existing user and pick directories.
  document.querySelectorAll('[data-admin-filter-list]').forEach((directory) => {
    const controls = directory.querySelector('[data-admin-filter-controls]');
    if (!controls) return;
    const search = controls.querySelector('[data-admin-list-search]');
    const select = controls.querySelector('[data-admin-list-select]');
    const items = [...directory.querySelectorAll('[data-admin-filter-item]')];
    const normalize = (value) => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    function filter() {
      let visible = 0; const query = normalize(search.value);
      items.forEach((item) => {
        const matches = normalize(item.dataset.searchText || '').includes(query) && (select.value === 'all' || item.dataset.filterValue === select.value);
        item.hidden = !matches; if (matches) visible += 1;
      });
      controls.querySelector('[data-admin-list-count]').textContent = `${visible} de ${items.length} registros visibles en esta lectura.`;
    }
    controls.hidden = false;
    search.addEventListener('input', filter); select.addEventListener('change', filter);
    controls.querySelector('[data-admin-list-reset]').addEventListener('click', () => { search.value = ''; select.value = 'all'; filter(); });
    filter();
  });
  const root = document.querySelector('[data-admin-master-control]');
  if (!root) return;
  const $ = (selector) => root.querySelector(selector);
  const $$ = (selector) => [...root.querySelectorAll(selector)];
  const apiBase = '/api/admin/master-control';
  const state = { snapshot: {}, proposal: null, busy: false, chatBusy: false, executing: false, cancelling: false };
  const proposalDialog = $('#master-proposal-dialog');
  const commandDialog = $('#master-command-dialog');
  const screens = [
    ['Centro de mando', '/admin/dashboard'], ['Partidos', '/admin/matches'],
    ['Directo', '/admin/realtime-center'], ['Picks', '/admin/picks'],
    ['Telegram', '/admin/telegram/command-center'], ['Usuarios', '/admin/users'],
    ['Membresías', '/admin/memberships'], ['Pagos', '/admin/payments'],
    ['SHARK AI', '/admin/shark-center'], ['Datos y APIs', '/admin/data-center'],
    ['Automatizaciones', '/admin/automation-center'], ['Sentinel / Calidad', '/admin/sentinel-issues'],
    ['Apariencia y contenido', '/admin/highlights-center'], ['Sistema', '/admin/system'],
    ['Release / Producción', '/admin/final-release'], ['Auditoría', '/admin/dashboard#master-audit-title'],
    ['Founder Control', '/admin/founder-os'], ['Company OS', '/admin/company-os'],
    ['AutoPilot', '/admin/sentinel-autopilot'], ['Jornada operativa', '/admin/operations-center'],
    ['Vista móvil PRO', '/admin/client-preview?page=home&plan=PRO&viewport=390'],
    ['Vista cliente PC', '/admin/client-preview?page=home&plan=FREE&viewport=1440'],
  ];
  const text = (value) => {
    if (value === undefined || value === null || value === '') return 'Sin datos';
    if (typeof value === 'boolean') return value ? 'Sí' : 'No';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };
  const node = (tag, content, className) => {
    const el = document.createElement(tag);
    if (content !== undefined) el.textContent = text(content);
    if (className) el.className = className;
    return el;
  };
  const own = (object, key) => Object.prototype.hasOwnProperty.call(object || {}, key);
  const stamp = (value) => {
    if (value === undefined || value === null || value === '') return 'Hora no disponible';
    if (typeof value === 'number' && Number.isFinite(value)) value = new Date(value * 1000).toISOString();
    // A timezone-free timestamp cannot be safely interpreted as Madrid time.
    if (!/(Z|[+-]\d\d:\d\d)$/i.test(String(value))) return `${value} · zona sin confirmar`;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? 'Hora no verificable' : new Intl.DateTimeFormat('es-ES', { timeZone: 'Europe/Madrid', dateStyle: 'short', timeStyle: 'medium' }).format(date) + ' · Madrid';
  };
  const safeAdminHref = (href) => {
    if (typeof href !== 'string' || !href.startsWith('/admin/') || /[\\\x00-\x20]/.test(href)) return null;
    const url = new URL(href, location.origin);
    if (url.origin !== location.origin || !url.pathname.startsWith('/admin/')) return null;
    return url.pathname + url.search + url.hash;
  };
  const actionId = (action) => action.action_id || action.id;
  const actionList = () => Array.isArray(state.snapshot.actions) ? state.snapshot.actions : [];
  const describe = (message) => { $('[data-master-feedback]').textContent = message; $('[data-master-feedback]').hidden = false; };
  const errorMessage = (error) => {
    if (error.status === 401 || error.status === 403) return 'No se pudo autorizar la operación. Comprueba tu sesión Admin y vuelve a cargar la página.';
    if (error.status === 409) return 'El estado ha cambiado o la propuesta ya no está vigente. Actualiza la lectura y prepara una propuesta nueva.';
    if (error.status === 429) return 'Se ha alcanzado el límite temporal de consultas. Espera antes de volver a intentarlo.';
    if (error.status === 400 || error.status === 422) return 'La solicitud no cumple las reglas de esta acción. Revisa los parámetros antes de preparar otra propuesta.';
    return 'No se pudo confirmar el resultado. Revisa la actividad antes de repetir cualquier cambio.';
  };
  async function request(path, payload) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 45000);
    try {
      const headers = { Accept: 'application/json' };
      if (payload !== undefined) {
        headers['Content-Type'] = 'application/json';
        headers['X-CSRF-Token'] = document.querySelector('meta[name="csrf-token"]')?.content || '';
      }
      const response = await fetch(apiBase + path, { method: payload === undefined ? 'GET' : 'POST', headers, credentials: 'same-origin', cache: 'no-store', signal: controller.signal, ...(payload === undefined ? {} : { body: JSON.stringify(payload) }) });
      if (response.redirected || !(response.headers.get('content-type') || '').includes('application/json')) { const error = new Error('AUTH_OR_FORMAT'); error.status = response.redirected ? 401 : response.status; throw error; }
      const data = await response.json();
      if (!response.ok || !data || data.ok === false) { const error = new Error('REQUEST_FAILED'); error.status = response.status; throw error; }
      return data;
    } finally { clearTimeout(timer); }
  }
  function recommendations(target, items) {
    target.replaceChildren();
    if (!Array.isArray(items) || !items.length) { target.append(node('p', 'Esta lectura no aporta recomendaciones. No certifica ausencia de incidencias.', 'master-empty')); return; }
    items.slice(0, 8).forEach((item) => {
      const article = node('article'); article.append(node('strong', item.title), node('p', item.evidence || item.detail || 'Evidencia no disponible.'));
      const href = safeAdminHref(item.href);
      if (href) { const link = node('a', 'Revisar →'); link.href = href; article.append(link); }
      target.append(article);
    });
  }
  function currentSetting() {
    const key = $('#master-setting-key').value;
    const settings = state.snapshot.settings || {};
    const raw = settings[key];
    const value = raw && typeof raw === 'object' && own(raw, 'value') ? raw.value : raw;
    $('[data-setting-current]').textContent = typeof value === 'boolean' ? (value ? 'Activo' : 'Desactivado') : text(value);
    $('[data-setting-bool]').hidden = key === 'banner_text';
    $('[data-setting-text]').hidden = key !== 'banner_text';
    if (key === 'banner_text') $('[name="text_value"]').value = value === undefined || value === null ? '' : String(value);
    else $('[name="boolean_value"]').value = value === true ? 'false' : 'true';
  }
  function renderSnapshot(snapshot) {
    if (!snapshot || typeof snapshot !== 'object' || Array.isArray(snapshot)) return;
    state.snapshot = snapshot;
    $('[data-master-timestamp]').textContent = stamp(snapshot.generated_at || snapshot.generated_at_madrid);
    $('[data-master-version]').textContent = snapshot.version || 'Versión no disponible';
    const facts = $('[data-master-facts]'); facts.replaceChildren();
    (Array.isArray(snapshot.facts) ? snapshot.facts : []).forEach((fact) => { const card = node('article'); card.append(node('span', fact.label), node('strong', fact.value)); facts.append(card); });
    if (!facts.childElementCount) facts.append(node('p', 'Sin métricas verificables en esta lectura.', 'master-empty'));
    const areas = $('[data-master-areas]'); areas.replaceChildren();
    (Array.isArray(snapshot.areas) ? snapshot.areas : []).forEach((area) => {
      const tr = node('tr'), label = node('th', area.label), statusCell = node('td'), detail = node('td', area.detail || 'No hay evidencia suficiente.'), linkCell = node('td');
      label.scope = 'row'; const chip = node('span', area.state || 'SIN DATOS', 'master-chip'); chip.dataset.state = area.state || 'SIN DATOS'; statusCell.append(chip);
      const href = safeAdminHref(area.href); if (href) { const link = node('a', 'Abrir →'); link.href = href; link.setAttribute('aria-label', `Abrir ${area.label}`); linkCell.append(link); }
      tr.append(label, statusCell, detail, linkCell); areas.append(tr);
    });
    if (!areas.childElementCount) { const tr = node('tr'), cell = node('td', 'No se pudo leer el estado de las áreas.'); cell.colSpan = 4; tr.append(cell); areas.append(tr); }
    recommendations($('[data-master-recommendations]'), snapshot.recommendations);
    const ai = snapshot.ai || {};
    $('[data-master-ai-state]').textContent = ai.configured ? 'IA avanzada configurada' : 'Diagnóstico del sistema';
    $('[data-master-ai-note]').textContent = ai.configured ? 'Configuración detectada. La disponibilidad se comprueba al consultar.' : 'IA avanzada no configurada. Diagnóstico del sistema disponible.';
    const runtime = $('[data-master-runtime]'); runtime.replaceChildren();
    Object.entries(snapshot.runtime || {}).forEach(([key, value]) => { const row = node('div'); row.append(node('dt', key.replaceAll('_', ' ')), node('dd', value)); runtime.append(row); });
    if (!runtime.childElementCount) { const row = node('div'); row.append(node('dt', 'Runtime'), node('dd', 'No disponible')); runtime.append(row); }
    renderAudit(snapshot.audit); currentSetting();
    $$('[data-master-propose]').forEach((button) => { button.disabled = !actionList().some((action) => actionId(action) === button.dataset.masterPropose); });
    $('#master-settings-form button[type="submit"]').disabled = !actionList().some((action) => actionId(action) === 'settings.update');
  }
  function renderAudit(events) {
    const target = $('[data-master-audit]'); target.replaceChildren();
    (Array.isArray(events) ? events : []).slice(0, 30).forEach((event) => {
      const tr = node('tr'), date = node('td', stamp(event.timestamp || event.created_at)), admin = node('td', event.admin || event.admin_id || event.actor || 'No disponible'), action = node('td', event.label || event.action_id), result = node('td', event.status || event.result || 'Sin resultado'), detail = node('td');
      admin.append(node('small', event.origin || event.source || 'Sin origen'));
      result.append(node('small', `Verificación: ${text(event.verification || event.verified)}`));
      const details = node('details'); details.append(node('summary', 'Ver evidencia'));
      const content = { audit_id: event.audit_id || event.id, action_id: event.action_id, parameters: event.parameters, before: event.before, after: event.after, result: event.result, verification: event.verification, origin: event.origin || event.source };
      details.append(node('pre', content)); detail.append(details);
      if (event.reversible === true && (event.audit_id || event.id)) { const rollback = node('button', 'Preparar reversión'); rollback.type = 'button'; rollback.dataset.masterRollback = String(event.audit_id || event.id); detail.append(rollback); }
      tr.append(date, admin, action, result, detail); target.append(tr);
    });
    if (!target.childElementCount) { const tr = node('tr'), cell = node('td', 'No hay cambios registrados en esta lectura.'); cell.colSpan = 5; tr.append(cell); target.append(tr); }
  }
  async function refresh(silent = false) {
    if (state.busy) return;
    state.busy = true; $$('[data-master-refresh]').forEach((button) => { button.disabled = true; });
    try { const data = await request(''); const snapshot = data.snapshot || data; renderSnapshot(snapshot); if (!silent) describe('Lectura local actualizada. No se han consultado proveedores externos.'); }
    catch (error) { describe(errorMessage(error)); }
    finally { state.busy = false; $$('[data-master-refresh]').forEach((button) => { button.disabled = false; }); }
  }
  function addMessage(kind, message, isUser = false) {
    const target = $('[data-master-conversation]'), article = node('article', undefined, 'master-message' + (isUser ? ' is-user' : ''));
    const kinds = { INFORMATION: 'INFORMACIÓN', INFO: 'INFORMACIÓN', RECOMMENDATION: 'RECOMENDACIÓN', PROPOSAL: 'PROPUESTA DE ACCIÓN', ACTION_PROPOSAL: 'PROPUESTA DE ACCIÓN', RESULT: 'RESULTADO', DIAGNOSIS: 'DIAGNÓSTICO', INSUFFICIENT_DATA: 'DATOS INSUFICIENTES', HYPOTHESIS: 'HIPÓTESIS', FACT: 'HECHO' };
    article.append(node('span', isUser ? 'ADMIN' : kinds[String(kind).toUpperCase()] || String(kind || 'INFORMACIÓN').toUpperCase()), node('p', message || 'No hay datos suficientes para responder.'));
    target.append(article); while (target.childElementCount > 30) target.firstElementChild.remove(); target.scrollTop = target.scrollHeight; return article;
  }
  async function chat(message) {
    if (state.chatBusy || !message.trim()) return;
    state.chatBusy = true; $('#master-chat-form button[type="submit"]').disabled = true;
    addMessage('ADMIN', message, true); $('#master-message').value = '';
    const pending = addMessage('INFORMACIÓN', 'Revisando la información disponible…');
    try {
      const data = await request('/chat', { message: message.trim().slice(0, 1200) }); pending.remove();
      const answer = addMessage(data.kind, data.message);
      if (Array.isArray(data.facts) && data.facts.length) { const list = node('ul'); data.facts.slice(0, 15).forEach((fact) => list.append(node('li', typeof fact === 'string' ? fact : `${fact.label || fact.type || 'HECHO'}: ${text(fact.value ?? fact.detail ?? fact.evidence)}`))); answer.append(list); }
      if (Array.isArray(data.recommendations) && data.recommendations.length) { const list = node('div', undefined, 'master-recommendations'); recommendations(list, data.recommendations); answer.append(list); }
      if (data.task) {
        const details = node('details'); details.append(node('summary', 'Incidencia y tarea Codex'));
        const task = data.task; details.append(node('pre', typeof task === 'string' ? task : task.codex_prompt || task.prompt || task)); answer.append(details);
        const href = safeAdminHref(task.href || '/admin/sentinel-workflow'); if (href) { const link = node('a', 'Abrir workflow existente →'); link.href = href; answer.append(link); }
      }
      if (data.proposal) { const button = node('button', 'Revisar propuesta'); button.type = 'button'; button.addEventListener('click', () => showProposal(data.proposal)); answer.append(button); showProposal(data.proposal); }
      $('[data-master-conversation]').scrollTop = $('[data-master-conversation]').scrollHeight;
    } catch (error) { pending.remove(); addMessage('INFORMACIÓN', errorMessage(error)); }
    finally { state.chatBusy = false; $('#master-chat-form button[type="submit"]').disabled = false; }
  }
  function showProposal(proposal) {
    if (state.executing || state.cancelling) return;
    if (!proposal || !(proposal.proposal_id || proposal.id)) { describe('No hay una propuesta válida para aprobar. No se ha ejecutado ningún cambio.'); return; }
    state.proposal = proposal;
    $('[data-proposal-label]').textContent = proposal.label || proposal.action_id || 'Revisar acción';
    $('[data-proposal-impact]').textContent = proposal.impact || proposal.description || 'Revisa el estado y los parámetros antes de aplicar.';
    const risk = String(proposal.risk_level || proposal.risk || 'UNKNOWN').toUpperCase();
    $('[data-proposal-risk]').textContent = ({ READ_ONLY: 'Solo lectura', LOW: 'Bajo', MEDIUM: 'Medio', HIGH: 'Alto', CRITICAL: 'Crítico / bloqueado', BLOCKED: 'Bloqueado' })[risk] || risk;
    $('[data-proposal-before]').textContent = own(proposal, 'before') ? text(proposal.before) : 'Estado anterior no disponible.';
    $('[data-proposal-after]').textContent = own(proposal, 'after') ? text(proposal.after) : 'Resultado propuesto no disponible.';
    $('[data-proposal-parameters]').textContent = text(proposal.parameters || {});
    const reinforced = risk === 'HIGH'; $('[data-proposal-reinforced]').hidden = !reinforced;
    $('[data-confirmation-label]').textContent = proposal.confirmation_phrase || 'REINTENTAR TELEGRAM'; $('#master-confirmation').value = '';
    $('[data-proposal-result]').hidden = true;
    $('[data-proposal-approve]').disabled = reinforced || ['CRITICAL', 'BLOCKED', 'UNKNOWN'].includes(risk);
    $('[data-proposal-approve]').textContent = 'Aplicar y verificar';
    if (!proposalDialog.open) proposalDialog.showModal();
  }
  async function propose(id, parameters = {}, trigger) {
    if (state.executing || state.busy) return;
    if (!actionList().some((action) => actionId(action) === id)) { describe('Esta acción no está disponible en el registro de esta lectura.'); return; }
    if (trigger) trigger.disabled = true;
    try { const data = await request('/proposals', { action_id: id, parameters }); showProposal(data.proposal || data); }
    catch (error) { describe(errorMessage(error)); }
    finally { if (trigger) trigger.disabled = false; }
  }
  async function execute() {
    if (!state.proposal || state.executing || $('[data-proposal-approve]').disabled) return;
    const proposal = state.proposal, high = String(proposal.risk_level || proposal.risk).toUpperCase() === 'HIGH';
    const confirmation = high ? $('#master-confirmation').value : true;
    if (high && confirmation !== ($('[data-confirmation-label]').textContent)) return;
    state.executing = true; $('[data-proposal-approve]').disabled = true; $('[data-proposal-cancel]').disabled = true; $('.master-dialog-close button').disabled = true;
    const output = $('[data-proposal-result]'); output.hidden = false; output.textContent = 'Ejecutando la acción aprobada y comprobando el resultado…';
    try {
      const data = await request('/execute', { proposal_id: proposal.proposal_id || proposal.id, confirmation });
      const result = data.result || data, verification = data.verification ?? result.verification ?? data.verified ?? result.verified;
      const verified = result.ok !== false && (verification === true || verification === 'VERIFIED' || verification?.verified === true || verification?.status === 'VERIFIED');
      const auditId = data.audit_id || result.audit_id || data.audit?.id;
      output.textContent = `${verified ? 'Acción completada. Verificación correcta.' : 'La ejecución ha terminado. Verificación: ' + text(verification)}${auditId ? '\nAudit ID: ' + auditId : '\nIdentificador de auditoría no recibido.'}`;
      const message = addMessage('RESULT', output.textContent);
      const task = result.result || result;
      if (task.codex_prompt || task.issue_id || task.task_id) {
        const details = node('details'); details.append(node('summary', 'Incidencia y tarea Codex'), node('pre', task.codex_prompt || { issue_id: task.issue_id, task_id: task.task_id })); message.append(details);
        const link = node('a', 'Abrir incidencia y prompt Codex →'); link.href = task.issue_id ? '/admin/sentinel-issues?issue_id=' + encodeURIComponent(String(task.issue_id)) : '/admin/sentinel-workflow'; message.append(link);
      }
      state.proposal = null; $('[data-proposal-approve]').textContent = 'Resultado registrado'; await refresh(true);
    } catch (error) { output.textContent = errorMessage(error) + '\nLa propuesta queda bloqueada en esta vista para evitar una repetición accidental. Consulta la auditoría.'; state.proposal = null; }
    finally { state.executing = false; $('[data-proposal-cancel]').disabled = false; $('[data-proposal-cancel]').textContent = 'Cerrar'; $('.master-dialog-close button').disabled = false; }
  }
  async function cancelProposal() {
    if (state.executing || state.cancelling) return;
    if (!state.proposal) { proposalDialog.close(); return; }
    state.cancelling = true;
    $('[data-proposal-cancel]').disabled = true; $('[data-proposal-approve]').disabled = true;
    $('.master-dialog-close button').disabled = true;
    const output = $('[data-proposal-result]'); output.hidden = false; output.textContent = 'Cancelando la propuesta pendiente…';
    try {
      const data = await request('/cancel', { proposal_id: state.proposal.proposal_id || state.proposal.id });
      if ((data.result || data).state !== 'CANCELLED') throw new Error('UNVERIFIED_CANCELLATION');
      state.proposal = null; proposalDialog.close(); describe('Propuesta cancelada. No se ejecutó la acción.'); await refresh(true);
    } catch (error) { output.textContent = errorMessage(error) + '\nNo se ha confirmado la cancelación. Puedes volver a cancelarla o cerrar esta vista sin ejecutar.'; }
    finally { state.cancelling = false; $('[data-proposal-cancel]').disabled = false; $('.master-dialog-close button').disabled = false; }
  }
  async function rollback(id, button) {
    if (state.executing || state.cancelling) return; button.disabled = true;
    try { const data = await request('/rollback', { audit_id: Number(id) }); showProposal(data.proposal || data); }
    catch (error) { describe(errorMessage(error)); }
    finally { button.disabled = false; }
  }
  function preview() {
    const page = $('[data-preview-page]').value, plan = $('[data-preview-plan]').value, width = $('[data-preview-viewport]').value;
    const query = new URLSearchParams({ page, plan, viewport: width });
    const frame = $('[data-client-preview-frame]'); frame.style.width = width + 'px'; frame.style.minWidth = width + 'px'; frame.src = '/admin/client-preview/frame?' + query;
    const device = ({ '390': 'Móvil', '768': 'Tablet', '1440': 'PC' })[width]; frame.title = `Vista cliente simulada ${plan} · ${device}`;
    $('[data-preview-label]').textContent = `${plan} · ${device} · ${width} px. Si el área disponible es menor, el marco se puede desplazar.`;
    $('[data-preview-full]').href = '/admin/client-preview?' + query;
  }
  function normalize(value) { return String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }
  function commandResults() {
    const query = normalize($('[data-command-search]').value), target = $('[data-command-results]'); target.replaceChildren();
    screens.filter(([label]) => normalize(label).includes(query)).forEach(([label, href]) => { const link = node('a'); link.href = href; link.append(node('span', label), node('small', 'Abrir pantalla')); target.append(link); });
    actionList().filter((action) => normalize(`${action.label} ${action.category || ''} ${action.description || ''}`).includes(query)).forEach((action) => {
      const button = node('button'), id = actionId(action); button.type = 'button'; button.append(node('span', action.label || id), node('small', 'Preparar · ' + text(action.risk_level || action.risk)));
      button.addEventListener('click', () => { commandDialog.close(); if (id === 'settings.update') { $('#master-setting-key').focus(); $('#master-settings-form').scrollIntoView({ block: 'center' }); } else if (id === 'settings.rollback') { $('#master-audit-title').scrollIntoView({ block: 'start' }); } else if (id === 'sentinel.create_improvement') { $('#master-message').value = 'Prepara mejora para la pantalla '; $('#master-message').focus(); } else propose(id, {}, button); }); target.append(button);
    });
    if (!target.childElementCount) target.append(node('p', 'Sin coincidencias. Prueba con el nombre de un área o una acción.', 'master-empty'));
  }
  function openCommand() { commandResults(); if (!commandDialog.open) commandDialog.showModal(); $('[data-command-search]').focus(); }
  root.addEventListener('click', (event) => {
    const button = event.target.closest('button'); if (!button) return;
    if (button.hasAttribute('data-master-refresh')) refresh();
    else if (button.hasAttribute('data-master-prompt')) chat(button.dataset.masterPrompt);
    else if (button.hasAttribute('data-master-propose')) propose(button.dataset.masterPropose, {}, button);
    else if (button.hasAttribute('data-master-rollback')) rollback(button.dataset.masterRollback, button);
    else if (button.hasAttribute('data-open-command')) openCommand();
    else if (button.hasAttribute('data-preview-reload')) preview();
    else if (button.hasAttribute('data-proposal-approve')) execute();
    else if (button.hasAttribute('data-proposal-cancel')) cancelProposal();
  });
  $('#master-chat-form').addEventListener('submit', (event) => { event.preventDefault(); chat($('#master-message').value); });
  $('#master-settings-form').addEventListener('submit', (event) => { event.preventDefault(); const key = $('#master-setting-key').value; const value = key === 'banner_text' ? $('[name="text_value"]').value : $('[name="boolean_value"]').value === 'true'; propose('settings.update', { key, value }, $('#master-settings-form button[type="submit"]')); });
  $('#master-setting-key').addEventListener('change', currentSetting);
  $$('[data-preview-page],[data-preview-plan],[data-preview-viewport]').forEach((control) => control.addEventListener('change', preview));
  $('[data-command-search]').addEventListener('input', commandResults);
  $('#master-confirmation').addEventListener('input', () => { if (!state.executing && state.proposal) $('[data-proposal-approve]').disabled = $('#master-confirmation').value !== $('[data-confirmation-label]').textContent; });
  proposalDialog.addEventListener('cancel', (event) => { if (state.executing || state.cancelling) event.preventDefault(); });
  proposalDialog.addEventListener('close', () => { if (!state.executing) state.proposal = null; $('[data-proposal-cancel]').textContent = 'Cancelar'; });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && commandDialog.open) { event.preventDefault(); event.stopPropagation(); commandDialog.close(); return; }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); if (!proposalDialog.open) openCommand(); }
  }, true);
  document.querySelector('.v933-admin-topbar form[role="search"]')?.addEventListener('submit', (event) => { event.preventDefault(); const query = event.currentTarget.querySelector('input')?.value || ''; $('[data-command-search]').value = query; openCommand(); });
  document.querySelector('.v933-admin-topbar [data-master-command-link]')?.addEventListener('click', (event) => { event.preventDefault(); openCommand(); });
  try { renderSnapshot(JSON.parse($('#admin-master-data').textContent || '{}')); } catch (_error) { describe('La lectura inicial no está disponible. Actualiza para volver a comprobarla.'); }
  const initialQuery = new URLSearchParams(location.search);
  if (initialQuery.has('q') || initialQuery.get('commands') === '1') {
    $('[data-command-search]').value = initialQuery.get('q') || '';
    openCommand();
  }
})();
