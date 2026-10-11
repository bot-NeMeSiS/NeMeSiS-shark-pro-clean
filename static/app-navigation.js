/* Local navigation only: no network requests, stored searches or mutations. */
(() => {
  'use strict';
  const dialog = document.getElementById('app-navigation-dialog');
  const normalize = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const text = (source, values) => window.NemesisI18n?.text(source, values) || source.replace(/\{(\w+)\}/g, (_, key) => values[key]);
  const controls = new Map();
  document.querySelectorAll('[data-app-explore]').forEach(root => {
    const input = root.querySelector('[data-explore-query]');
    const items = [...root.querySelectorAll('[data-explore-item]')];
    const match = root.querySelector('[data-explore-match]');
    const form = root.querySelector('[data-explore-form]');
    if (!input || !form || root.dataset.exploreReady === 'true') return;
    root.dataset.exploreReady = 'true';
    let composing = false;
    const clear = document.createElement('button');
    clear.type = 'button'; clear.className = 'v933-action';
    clear.dataset.exploreClear = '';
    clear.textContent = text('Limpiar filtros', {});
    clear.hidden = true;
    form.insertAdjacentElement('afterend', clear);
    const results = () => [...items.filter(item => !item.hidden), ...(match && !match.hidden ? [match] : [])];
    function filter() {
      const query = input.value.trim().slice(0, 90);
      const terms = normalize(query).split(/\s+/).filter(Boolean);
      clear.hidden = !query;
      items.forEach(item => { item.hidden = !terms.every(term => normalize(item.dataset.exploreLabel).includes(term)); });
      root.querySelectorAll('[data-explore-group]').forEach(group => { group.hidden = !group.querySelector('[data-explore-item]:not([hidden])'); });
      const count = items.filter(item => !item.hidden).length;
      root.querySelector('[data-explore-count]').textContent = text(count === 1 ? '{count} sección disponible' : '{count} secciones disponibles', { count });
      root.querySelector('[data-explore-empty]').hidden = count > 0;
      if (match) {
        match.hidden = !query;
        match.href = '/calendario?' + new URLSearchParams({ lane: 'week', q: query });
        match.querySelector('[data-explore-match-query]').textContent = query;
      }
    }
    input.addEventListener('input', filter);
    input.addEventListener('compositionstart', () => { composing = true; });
    input.addEventListener('compositionend', () => { composing = false; filter(); });
    clear.addEventListener('click', () => {
      input.value = ''; input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('sports:query')); input.focus();
    });
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (composing) return;
      filter();
      const query = normalize(input.value.trim().slice(0, 90));
      if (!query) return;
      const visible = items.filter(item => !item.hidden);
      const exact = visible.filter(item => normalize(item.querySelector('span')?.textContent.trim() || '') === query);
      // Do not send an ambiguous search to the first section by accident.
      const destination = exact.length === 1 ? exact[0] : visible.length === 1 ? visible[0]
        : visible.length === 0 && match && !match.hidden ? match : null;
      if (destination) destination.click();
      else {
        root.querySelector('[data-explore-count]').textContent = text('{count} secciones disponibles', { count: visible.length });
        visible[0]?.focus();
      }
    });
    root.addEventListener('keydown', event => {
      if (event.defaultPrevented || event.isComposing || event.altKey || event.ctrlKey || event.metaKey || !['ArrowDown', 'ArrowUp'].includes(event.key)) return;
      const choices = results();
      const index = choices.indexOf(document.activeElement);
      if (document.activeElement !== input && index < 0) return;
      event.preventDefault();
      if (!choices.length) return;
      const next = event.key === 'ArrowDown' ? index + 1 : (index < 0 ? choices.length - 1 : index - 1);
      (next < 0 || next >= choices.length ? input : choices[next]).focus();
    });
    controls.set(root, { input, filter });
    filter();
  });
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const control = controls.get(dialog.querySelector('[data-app-explore]'));
  if (!control) return;
  let opener = null;
  function open(source, query = '') {
    // Never replace a confirmation or another active modal.
    if ([...document.querySelectorAll('dialog[open]')].some(item => item !== dialog)) return;
    if (!dialog.open) {
      opener = source || document.activeElement;
      control.input.value = query.slice(0, 90);
      control.filter();
      dialog.showModal();
      control.input.dispatchEvent(new Event('sports:query'));
    }
    control.input.focus();
  }
  dialog.querySelector('[data-explore-keyboard]').hidden = false;
  document.querySelectorAll('[data-open-explore]').forEach(link => {
    link.setAttribute('aria-haspopup', 'dialog');
    link.setAttribute('aria-controls', dialog.id);
    link.addEventListener('click', event => {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault(); open(link);
    });
  });
  document.querySelector('[data-explore-admin-form]')?.addEventListener('submit', event => {
    event.preventDefault(); open(event.currentTarget.querySelector('input'), event.currentTarget.querySelector('input').value);
  });
  document.addEventListener('keydown', event => {
    if (event.defaultPrevented || event.isComposing || event.repeat || event.altKey) return;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault(); open(document.activeElement);
    }
  });
  dialog.addEventListener('close', () => {
    // The browser queues this event; a new search may already be open.
    if (dialog.open) return;
    if (opener?.isConnected && opener.getClientRects().length) opener.focus();
    // Do not retain typed names in a closed overlay.
    control.input.value = ''; control.filter();
    control.input.dispatchEvent(new Event('sports:query'));
  });
  dialog.addEventListener('keydown', event => {
    // Search inputs consume Escape to clear themselves in some browsers.
    if (event.key === 'Escape' && !event.isComposing) {
      event.preventDefault(); event.stopPropagation(); dialog.close();
    }
  }, true);
  dialog.addEventListener('click', event => {
    if (event.target.closest('a[href]') && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
      dialog.close(); return;
    }
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  });
  window.NemesisNavigation = Object.freeze({ open });
})();
