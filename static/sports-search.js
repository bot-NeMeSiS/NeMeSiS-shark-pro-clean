/* Progressive discovery: local GET only; saving is an explicit CSRF-protected form. */
(() => {
  'use strict';
  const text = (source, values = {}) => window.NemesisI18n?.text(source, values) || source.replace(/\{(\w+)\}/g, (_, key) => values[key] ?? '');
  const kinds = {team: 'Equipo', league: 'Liga / competición', match: 'Partido'};
  document.querySelectorAll('input[data-sports-search]').forEach(input => {
    const panel = document.getElementById(input.dataset.sportsSearch);
    if (!panel) return;
    const list = panel.querySelector('[data-sports-options]');
    const status = panel.querySelector('[data-sports-status]');
    const selection = document.querySelector(`[data-sports-selection="${panel.id}"]`);
    const kindSelect = input.dataset.sportsKind ? document.getElementById(input.dataset.sportsKind) : null;
    let controller, timer, sequence = 0, active = -1, items = [], composing = false;
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-controls', list.id);
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('autocomplete', 'off');
    function close() {
      clearTimeout(timer); controller?.abort(); sequence++;
      panel.hidden = true; active = -1; items = [];
      list.replaceChildren(); input.removeAttribute('aria-activedescendant');
      input.setAttribute('aria-expanded', 'false');
    }
    function invalidateSelection() {
      if (!selection) return;
      selection.hidden = true;
      selection.querySelector('button[type="submit"]').disabled = true;
      ['kind', 'value', 'label'].forEach(name => { selection.querySelector(`[name="${name}"]`).value = ''; });
    }
    function choose(item) {
      if (!item) return;
      close();
      if (panel.dataset.mode !== 'favorite') {
        // Only the closed set of local destinations produced by this API.
        if (/^\/(team|competition|match)\/[^?#]+$/.test(item.href) || /^\/favoritos\?/.test(item.href)) window.location.assign(item.href);
        return;
      }
      if (!selection) return;
      selection.querySelector('[data-selection-label]').textContent = item.label;
      selection.querySelector('[data-selection-context]').textContent = item.context;
      selection.querySelector('[data-selection-kind]').textContent = text(kinds[item.kind]);
      selection.querySelector('[data-selection-link]').href = item.href;
      ['kind', 'value', 'label'].forEach(name => { selection.querySelector(`[name="${name}"]`).value = item[name]; });
      const button = selection.querySelector('button[type="submit"]');
      button.disabled = item.saved;
      button.textContent = text(item.saved ? 'Ya está en favoritos' : 'Guardar favorito');
      selection.hidden = false;
      (item.saved ? selection.querySelector('[data-selection-link]') : button).focus();
    }
    function highlight(index) {
      active = index;
      [...list.children].forEach((row, i) => row.setAttribute('aria-selected', String(i === active)));
      const option = list.children[active];
      if (option) { input.setAttribute('aria-activedescendant', option.id); option.scrollIntoView({block:'nearest'}); }
      else input.removeAttribute('aria-activedescendant');
    }
    async function search(query, id) {
      controller = new AbortController();
      panel.hidden = false;
      input.setAttribute('aria-expanded', 'true');
      status.textContent = text('Buscando coincidencias…');
      try {
        const parameters = new URLSearchParams({q:query, kind:kindSelect?.value || panel.dataset.kind || '', scope:panel.dataset.scope || 'all'});
        const response = await fetch('/api/sports-search?' + parameters, {signal:controller.signal, credentials:'same-origin', cache:'no-store', headers:{Accept:'application/json'}});
        if (!response.ok) throw new Error('search_unavailable');
        const result = await response.json();
        if (id !== sequence || composing || document.activeElement !== input) return;
        items = Array.isArray(result.items) ? result.items : [];
        list.replaceChildren(); active = -1;
        items.forEach((item, index) => {
          const row = document.createElement('li');
          row.id = `${list.id}-${index}`; row.setAttribute('role','option'); row.setAttribute('aria-selected','false');
          const badge = document.createElement('span'); badge.className = 'sports-search-kind'; badge.textContent = text(kinds[item.kind] || 'Favorito');
          const label = document.createElement('strong'); label.textContent = item.label;
          const context = document.createElement('small'); context.textContent = item.context;
          row.append(badge, label, context);
          row.addEventListener('pointerdown', event => event.preventDefault());
          row.addEventListener('click', () => choose(item));
          list.append(row);
        });
        status.textContent = text(items.length === 1 ? '{count} coincidencia' : '{count} coincidencias', {count:items.length});
        if (!result.complete) status.textContent = text('La búsqueda no ha terminado. Prueba con un nombre más concreto.');
        else if (result.has_more) status.textContent += ' · ' + text('Hay más coincidencias. Añade otra palabra para afinar.');
        else if (!items.length) status.textContent = text('Sin coincidencias entre los datos disponibles. Prueba con otro nombre.');
      } catch (error) {
        if (id !== sequence || error.name === 'AbortError') return;
        list.replaceChildren(); items = [];
        status.textContent = text('No se ha podido buscar. Vuelve a intentarlo o pulsa Buscar.');
      }
    }
    function schedule() {
      close(); invalidateSelection();
      document.querySelector(`[data-sports-server-results="${panel.id}"]`)?.setAttribute('hidden','');
      if (composing) return;
      const query = input.value.trim().slice(0,90);
      if (query.length < 2) return;
      const id = sequence;
      timer = setTimeout(() => search(query, id), 280);
    }
    input.addEventListener('input', schedule);
    input.addEventListener('sports:query', schedule);
    input.addEventListener('compositionstart', () => { composing = true; close(); invalidateSelection(); });
    input.addEventListener('compositionend', () => { composing = false; schedule(); });
    kindSelect?.addEventListener('change', () => { input.focus(); schedule(); });
    input.addEventListener('keydown', event => {
      if (event.isComposing || composing || panel.hidden) return;
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(); }
      if (['ArrowDown','ArrowUp'].includes(event.key) && items.length) {
        event.preventDefault(); event.stopPropagation();
        highlight(active < 0 ? (event.key === 'ArrowDown' ? 0 : items.length - 1) : (active + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length);
      }
      if (event.key === 'Enter' && active >= 0) { event.preventDefault(); event.stopPropagation(); choose(items[active]); }
    });
    input.addEventListener('blur', () => {
      const blurredSequence = sequence;
      setTimeout(() => {
        // Returning to edit invalidates a queued departure from the old query.
        if (blurredSequence === sequence && document.activeElement !== input) close();
      }, 0);
    });
    input.closest('dialog')?.addEventListener('close', close);
    document.addEventListener('pointerdown', event => { if (event.target !== input && !panel.contains(event.target)) close(); });
  });
})();
