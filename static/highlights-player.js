/* Opt-in external players. No provider lookup, autoplay, cookies before a click or automatic retry. */
(() => {
  'use strict';
  document.querySelectorAll('[data-highlight-player]').forEach((root) => {
    if (root.dataset.playerReady) return;
    const button = root.querySelector('[data-highlight-load]');
    const frame = root.querySelector('[data-highlight-frame]');
    const status = root.querySelector('[data-highlight-status]');
    if (!button || !frame) return;
    let url;
    try {
      url = new URL(button.dataset.embedUrl);
      const allowed = url.protocol === 'https:' && !url.username && !url.password && !url.port
        && ((url.hostname === 'www.youtube-nocookie.com' && /^\/embed\/[A-Za-z0-9_-]{1,80}$/.test(url.pathname))
          || (url.hostname === 'player.vimeo.com' && /^\/video\/[0-9]{1,20}$/.test(url.pathname)))
        && !url.search && !url.hash;
      if (!allowed) return;
    } catch (_error) { return; }
    root.dataset.playerReady = 'true';
    button.hidden = false;
    button.addEventListener('click', () => {
      if (frame.childElementCount) {
        frame.replaceChildren(); frame.hidden = true;
        button.textContent = '▶ Cargar vídeo-resumen';
        button.setAttribute('aria-expanded', 'false');
        if (status) status.textContent = 'Reproductor cerrado. El enlace externo sigue disponible.';
        return;
      }
      const player = document.createElement('iframe');
      player.src = url.href;
      player.title = button.dataset.videoTitle || 'Vídeo-resumen';
      player.allowFullscreen = true;
      player.allow = 'encrypted-media; picture-in-picture; fullscreen';
      player.referrerPolicy = 'strict-origin-when-cross-origin';
      player.addEventListener('error', () => {
        if (status) status.textContent = 'No se pudo cargar el reproductor. Prueba el enlace original.';
      });
      frame.append(player); frame.hidden = false;
      button.textContent = 'Cerrar reproductor'; button.setAttribute('aria-expanded', 'true');
      // An iframe load is not evidence that playback is allowed, available or has succeeded.
      if (status) status.textContent = 'Reproductor solicitado. Si no reproduce, abre la fuente original.';
    });
  });
})();
