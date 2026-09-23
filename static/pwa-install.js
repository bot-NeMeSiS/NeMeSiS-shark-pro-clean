(function nemesisPwaInstallExperience() {
  'use strict';

  var ua = navigator.userAgent || '';
  var isIos = /iPad|iPhone|iPod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var isStandalone = window.matchMedia && window.matchMedia('(display-mode: standalone)').matches;
  isStandalone = isStandalone || window.navigator.standalone === true;
  var isAdminSurface = document.body && document.body.classList.contains('ns-admin');
  if (isStandalone || isAdminSurface) return;

  var iconMeta = document.querySelector('meta[name="nemesis-app-icon-version"]');
  var iconVersion = iconMeta ? (iconMeta.getAttribute('content') || 'current') : 'current';
  var dismissedKey = 'nemesis-pwa-install-dismissed-' + iconVersion;
  var dismissForMs = 7 * 24 * 60 * 60 * 1000;

  function isDismissed() {
    try {
      var stored = parseInt(localStorage.getItem(dismissedKey) || '0', 10);
      return stored > 0 && (Date.now() - stored) < dismissForMs;
    } catch (e) {
      return false;
    }
  }

  var deferredPrompt = null;
  var root = null;
  var button = null;
  var panel = null;
  var live = null;

  function ensureUi() {
    if (root) return root;
    root = document.createElement('div');
    root.className = 'ns-pwa-install';
    root.setAttribute('data-ns-pwa-install', '');
    root.hidden = true;

    button = document.createElement('button');
    button.type = 'button';
    button.className = 'ns-pwa-install__button';
    button.setAttribute('aria-expanded', 'false');
    button.innerHTML = '<span aria-hidden="true">＋</span><strong>Añadir NeMeSiS</strong><small>Pantalla de inicio</small>';

    panel = document.createElement('div');
    panel.className = 'ns-pwa-install__panel';
    panel.hidden = true;
    panel.innerHTML =
      '<strong>Ten NeMeSiS como una app</strong>' +
      '<p data-ns-pwa-copy>Instálala desde el navegador para abrirla desde tu pantalla de inicio.</p>' +
      '<div class="ns-pwa-install__actions">' +
      '<button type="button" data-ns-pwa-confirm>Instalar</button>' +
      '<a href="/instalar">Ver guía</a>' +
      '<button type="button" data-ns-pwa-close>Ahora no</button>' +
      '</div>';

    live = document.createElement('span');
    live.className = 'ns-pwa-install__live';
    live.setAttribute('aria-live', 'polite');

    root.appendChild(button);
    root.appendChild(panel);
    root.appendChild(live);
    document.body.appendChild(root);

    button.addEventListener('click', function () {
      if (deferredPrompt) {
        triggerInstall();
        return;
      }
      panel.hidden = !panel.hidden;
      button.setAttribute('aria-expanded', panel.hidden ? 'false' : 'true');
    });

    panel.querySelector('[data-ns-pwa-confirm]').addEventListener('click', function () {
      if (deferredPrompt) {
        triggerInstall();
        return;
      }
      if (isIos) {
        live.textContent = 'En iPhone o iPad: toca Compartir y después “Añadir a pantalla de inicio”.';
      }
    });

    panel.querySelector('[data-ns-pwa-close]').addEventListener('click', function () {
      panel.hidden = true;
      button.setAttribute('aria-expanded', 'false');
      try { localStorage.setItem(dismissedKey, String(Date.now())); } catch (e) {}
      root.hidden = true;
    });

    return root;
  }

  function show(mode) {
    ensureUi();
    if (isDismissed()) return;
    root.hidden = false;
    var copy = panel.querySelector('[data-ns-pwa-copy]');
    var confirm = panel.querySelector('[data-ns-pwa-confirm]');
    if (mode === 'ios') {
      button.querySelector('strong').textContent = 'Añadir a inicio';
      copy.textContent = 'En iPhone o iPad: toca Compartir y después “Añadir a pantalla de inicio”.';
      confirm.textContent = 'Ver cómo';
    } else {
      button.querySelector('strong').textContent = 'Instalar app';
      copy.textContent = 'Instala NeMeSiS para abrirla como una app desde móvil o PC.';
      confirm.textContent = 'Instalar';
    }
  }

  async function triggerInstall() {
    if (!deferredPrompt) {
      if (isIos) {
        ensureUi();
        panel.hidden = false;
        button.setAttribute('aria-expanded', 'true');
        live.textContent = 'Toca Compartir y después “Añadir a pantalla de inicio”.';
      }
      return;
    }
    var promptEvent = deferredPrompt;
    deferredPrompt = null;
    try {
      promptEvent.prompt();
      var choice = await promptEvent.userChoice;
      if (choice && choice.outcome === 'accepted') {
        if (root) root.hidden = true;
        if (live) live.textContent = 'NeMeSiS se está instalando.';
      } else {
        show('native');
        if (live) live.textContent = 'Instalación cancelada. Puedes intentarlo cuando quieras.';
      }
    } catch (e) {
      show(isIos ? 'ios' : 'native');
      if (live) live.textContent = 'No se pudo abrir el instalador. Usa el menú del navegador.';
    }
  }

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredPrompt = event;
    show('native');
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    if (root) root.hidden = true;
    try { localStorage.removeItem(dismissedKey); } catch (e) {}
  });

  document.addEventListener('DOMContentLoaded', function () {
    if (isIos) show('ios');
  });

  window.nemesisInstallApp = triggerInstall;
})();
