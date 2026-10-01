/* External media is untrusted. Load only the server-approved fixed player hosts,
   after an explicit action. iframe load cannot certify playback across origins. */
(() => {
  'use strict';
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-video-activate]');
    if (!button || button.disabled) return;
    const card = button.closest('[data-postmatch-video]');
    const mount = card && card.querySelector('[data-video-mount]');
    const notice = card && card.querySelector('[data-video-notice]');
    if (!mount || !notice) return;
    let url;
    try { url = new URL(button.dataset.videoActivate); } catch (_) { return; }
    const allowed = url.protocol === 'https:' && !url.username && !url.password && !url.port && !url.search && !url.hash &&
      ((url.hostname === 'www.youtube-nocookie.com' && /^\/embed\/[A-Za-z0-9_-]{1,80}$/.test(url.pathname)) ||
       (url.hostname === 'player.vimeo.com' && /^\/video\/\d{1,20}$/.test(url.pathname)));
    if (!allowed) { notice.textContent = 'No se puede cargar este reproductor. Revisa el enlace original.'; return; }
    const frame = document.createElement('iframe');
    frame.src = url.href;
    frame.title = 'Resumen del partido en una plataforma externa';
    frame.allowFullscreen = true;
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    frame.style.width = '100%'; frame.style.aspectRatio = '16 / 9'; frame.style.border = '0';
    frame.addEventListener('error', () => { notice.textContent = 'No se pudo cargar el reproductor. Prueba el enlace original cuando esté disponible.'; });
    mount.hidden = false; mount.style.removeProperty('display');
    mount.replaceChildren(frame);
    button.disabled = true; button.textContent = 'Reproductor solicitado';
    notice.textContent = 'La plataforma puede limitar o retirar el vídeo. Si no reproduce, prueba el enlace original cuando esté disponible.';
  });
})();
