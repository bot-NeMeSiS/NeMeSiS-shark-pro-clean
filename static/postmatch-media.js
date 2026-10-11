/* External media is untrusted. Load only the server-approved fixed player hosts,
   after an explicit action. iframe load cannot certify playback across origins. */
(() => {
  'use strict';
  if (window.NemesisPostmatchMedia) return;
  const active = new Map();
  const text = source => window.NemesisI18n?.text(source) || source;
  function approved(value) {
    let url;
    try { url = new URL(value); } catch (_) { return null; }
    const allowed = url.protocol === 'https:' && !url.username && !url.password && !url.port && !url.search && !url.hash &&
      ((url.hostname === 'www.youtube-nocookie.com' && /^\/embed\/[A-Za-z0-9_-]{1,80}$/.test(url.pathname)) ||
       (url.hostname === 'player.vimeo.com' && /^\/video\/\d{1,20}$/.test(url.pathname)));
    return allowed ? url.href : null;
  }
  function close(card, restoreFocus = true) {
    const entry = active.get(card);
    if (!entry) return;
    entry.mount.replaceChildren(); entry.mount.hidden = true;
    entry.controls.remove();
    entry.button.disabled = false; entry.button.textContent = entry.label;
    entry.button.setAttribute('aria-expanded', 'false');
    entry.notice.textContent = entry.initialNotice;
    active.delete(card);
    if (restoreFocus && entry.button.isConnected) entry.button.focus();
  }
  function load(entry) {
    // Revalidate every explicit retry. Never use a redirect or infer playback.
    const url = approved(entry.button.dataset.videoActivate);
    if (!url) {
      entry.notice.textContent = text('No se puede cargar este reproductor. Revisa el enlace original.');
      return false;
    }
    const frame = document.createElement('iframe');
    frame.src = url;
    frame.title = text('Resumen del partido en una plataforma externa');
    frame.allowFullscreen = true;
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    frame.style.width = '100%'; frame.style.aspectRatio = '16 / 9'; frame.style.border = '0';
    entry.mount.hidden = false; entry.mount.style.removeProperty('display');
    entry.mount.replaceChildren(frame);
    // Neither load nor error can establish third-party video availability.
    entry.notice.textContent = text('La plataforma puede limitar o retirar el vídeo. Si no reproduce, prueba el enlace original cuando esté disponible.');
    return true;
  }
  document.addEventListener('click', event => {
    const target = event.target instanceof Element ? event.target : null;
    const button = target?.closest('[data-video-activate]');
    if (!button || button.disabled) return;
    const card = button.closest('[data-postmatch-video]');
    const mount = card?.querySelector('[data-video-mount]');
    const notice = card?.querySelector('[data-video-notice]');
    if (!card || !mount || !notice || active.has(card)) return;
    if (!approved(button.dataset.videoActivate)) {
      notice.textContent = text('No se puede cargar este reproductor. Revisa el enlace original.');
      return;
    }
    const controls = document.createElement('div');
    controls.className = 'v933-page-actions'; controls.dataset.videoControls = '';
    const retry = document.createElement('button');
    retry.type = 'button'; retry.className = 'btn'; retry.dataset.videoRetry = '';
    retry.textContent = text('Reintentar');
    const dismiss = document.createElement('button');
    dismiss.type = 'button'; dismiss.className = 'btn'; dismiss.dataset.videoClose = '';
    dismiss.textContent = text('Cerrar');
    dismiss.setAttribute('aria-label', text('Cerrar reproductor'));
    controls.append(retry, dismiss);
    const entry = { button, mount, notice, controls, label: button.textContent, initialNotice: notice.textContent };
    if (!load(entry)) return;
    active.set(card, entry);
    button.disabled = true; button.textContent = text('Reproductor solicitado');
    button.setAttribute('aria-expanded', 'true');
    button.insertAdjacentElement('afterend', controls);
    retry.addEventListener('click', () => { load(entry); });
    dismiss.addEventListener('click', () => close(card));
    // The disabled opener cannot retain keyboard focus. Give a visible way back.
    dismiss.focus();
  });
  window.addEventListener('pagehide', () => {
    [...active.keys()].forEach(card => close(card, false));
  });
  window.NemesisPostmatchMedia = Object.freeze({ closeAll: () => [...active.keys()].forEach(card => close(card, false)) });
})();
