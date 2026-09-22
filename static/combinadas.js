/* Progressive enhancement only: normal links/forms remain functional without JS.
 * No odds math, account data in localStorage, provider fetch, or automatic retry. */
(() => {
  'use strict';
  document.querySelectorAll('[data-copy-combi][data-action="copy-combi"]').forEach((button) => {
    button.hidden = false;
    button.addEventListener('click', async () => {
      const box = button.closest('details');
      const source = box && box.querySelector('textarea');
      const status = box && box.querySelector('[data-copy-status]');
      if (!source || !status) return;
      try {
        if (!navigator.clipboard) throw new Error('unavailable');
        await navigator.clipboard.writeText(source.value);
        status.textContent = 'Borrador copiado. No se ha colocado ninguna apuesta.';
      } catch (_) {
        source.focus(); source.select();
        status.textContent = 'Copia el texto seleccionado con el menú del dispositivo.';
      }
    });
  });
})();

// Local selection feedback only. No prices are trusted or calculated in the browser.
(() => {
  'use strict';
  document.querySelectorAll('form[data-combi-form]').forEach((form) => {
    const status = form.querySelector('[data-selection-count]');
    if (!status) return;
    const update = (changed) => {
      if (changed && changed.matches('[data-market-choice]') && changed.checked) {
        form.querySelectorAll('[data-market-choice]').forEach((other) => {
          if (other !== changed && other.dataset.marketEvent === changed.dataset.marketEvent) other.checked = false;
        });
      }
      const count = form.querySelectorAll('input[name="pick_ids"]:checked:not(:disabled)').length;
      status.textContent = count + (count === 1 ? ' selección marcada' : ' selecciones marcadas');
    };
    form.addEventListener('change', (event) => update(event.target));
    update(null);
  });
})();
