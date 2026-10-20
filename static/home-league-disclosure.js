/* Home league discovery only. No requests, storage, history writes or sports mutations. */
(() => {
  'use strict';
  if (window.NemesisHomeLeagues) return;
  const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const text = (source, values) => window.NemesisI18n?.text(source, values) || source.replace(/\{(\w+)\}/g, (_, key) => values[key]);
  const controls = new Map();
  document.querySelectorAll('[data-home-more-leagues]').forEach(more => {
    const input = more.querySelector('[data-home-league-search]');
    const clear = more.querySelector('[data-home-league-clear]');
    const status = more.querySelector('[data-home-league-search-status]');
    const empty = more.querySelector('[data-home-no-league-results]');
    const rows = [...more.querySelectorAll('[data-home-importance="secondary"]')];
    if (!input || !clear || !status || !empty) return;
    let composing = false;
    const filter = () => {
      const query = input.value.trim().slice(0,90);
      const terms = normalize(query).split(/\s+/).filter(Boolean);
      let count = 0;
      rows.forEach(row => {
        row.hidden = !terms.every(term => normalize(row.dataset.homeLeagueSearchLabel).includes(term));
        if (!row.hidden) count++;
      });
      more.querySelectorAll('[data-home-competition-section]').forEach(section => {
        const entries = [...section.querySelectorAll('[data-home-importance="secondary"]')];
        section.hidden = entries.length > 0 && entries.every(row => row.hidden);
      });
      clear.hidden = !query;
      empty.hidden = count > 0;
      status.textContent = query ? text('{count} competiciones en esta selección', { count }) : '';
    };
    const reset = () => { input.value = ''; filter(); };
    input.addEventListener('input', () => { if (!composing) filter(); });
    input.addEventListener('compositionstart', () => { composing = true; });
    input.addEventListener('compositionend', () => { composing = false; filter(); });
    input.addEventListener('keydown', event => {
      if (event.isComposing || composing) return;
      if (event.key === 'Escape' && input.value) { event.preventDefault(); event.stopPropagation(); reset(); }
    });
    clear.addEventListener('click', () => { reset(); input.focus(); });
    more.querySelector('[data-home-league-filter]').hidden = false;
    controls.set(more, reset);
  });
  // Preserve existing deep links, even when their league now starts folded.
  const revealHash = () => {
    let id;
    try { id = decodeURIComponent(window.location.hash.slice(1)); } catch (_) { return; }
    const target = id && document.getElementById(id);
    if (!target || !target.closest('[data-home-league-browser]')) return;
    const more = target.closest('[data-home-more-leagues]');
    if (more) { controls.get(more)?.(); more.open = true; }
    let node = target;
    while (node && node.closest('[data-home-league-browser]')) {
      if (node instanceof HTMLDetailsElement) node.open = true;
      node = node.parentElement;
    }
    target.scrollIntoView({ block:'start' });
  };
  window.addEventListener('hashchange', revealHash);
  window.NemesisHomeLeagues = Object.freeze({ revealHash });
  revealHash();
})();
