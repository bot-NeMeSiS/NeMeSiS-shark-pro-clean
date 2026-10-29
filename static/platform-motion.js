/* Optional decoration only. No network, sports clock, identity or AI access. */
(function () {
  'use strict';
  var controls = document.querySelector('[data-motion-preferences]');
  if (!controls) return;
  var toggle = controls.querySelector('[data-motion-toggle]');
  var lightSwitch = controls.querySelector('[data-marine-toggle]');
  var light = document.querySelector('[data-marine-light]');
  var launcher = document.querySelector('[data-ns-assistant-open]');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var transparency = window.matchMedia('(prefers-reduced-transparency: reduce)');
  var stored = false, paused = true, marine = false, discovered = true;
  var pulse = false, pulseTimer = null, launcherVisible = false;
  try {
    paused = localStorage.getItem('nemesis.motion.paused.v1') === 'true';
    marine = localStorage.getItem('nemesis.motion.marine.v1') === 'true';
    discovered = localStorage.getItem('nemesis.shark.discovery.v1') === 'seen';
    // A restricted store must fail quiet, including when it permits reads only.
    sessionStorage.setItem('nemesis.motion.storage-check', '1');
    sessionStorage.removeItem('nemesis.motion.storage-check');
    localStorage.setItem('nemesis.motion.storage-check', '1');
    localStorage.removeItem('nemesis.motion.storage-check');
    stored = true;
  } catch (_) { paused = true; marine = false; discovered = true; }

  function dialogOpen() {
    return Boolean(document.querySelector('dialog[open], [role="dialog"][aria-modal="true"]:not([hidden])'));
  }
  function writing() {
    var focus = document.activeElement;
    return Boolean(focus && !controls.contains(focus) && (focus.matches('input:not([type=checkbox]):not([type=radio]):not([type=button]):not([type=submit]),textarea,select') || focus.isContentEditable));
  }
  function eligible() {
    return stored && !paused && !reduce.matches && !document.hidden && !dialogOpen() && !writing();
  }
  function stopPulse() {
    if (pulseTimer !== null) window.clearTimeout(pulseTimer);
    pulseTimer = null; pulse = false;
    if (launcher) launcher.classList.remove('ns-discovery-pulse');
  }
  function update() {
    var allowed = eligible();
    if (!allowed) stopPulse();
    if (light) light.classList.toggle('is-running', allowed && marine && !transparency.matches && !pulse);
    toggle.disabled = !stored || reduce.matches;
    toggle.setAttribute('aria-pressed', String(paused));
    toggle.textContent = !stored ? controls.dataset.unavailable : (reduce.matches ? controls.dataset.reduced : (paused ? controls.dataset.resume : controls.dataset.pause));
    lightSwitch.checked = marine;
    lightSwitch.disabled = !stored || reduce.matches || transparency.matches;
    controls.hidden = false;
  }
  function rememberDiscovery() {
    discovered = true;
    try { localStorage.setItem('nemesis.shark.discovery.v1', 'seen'); }
    catch (_) { stored = false; }
  }
  function discover() {
    if (discovered || !launcherVisible || !launcher || launcher.hidden || getComputedStyle(launcher).visibility === 'hidden') return;
    // Reduced motion and a manual pause consume discovery without a later replay.
    if (reduce.matches || paused) { rememberDiscovery(); update(); return; }
    if (!eligible()) return;
    rememberDiscovery();
    if (!stored) { update(); return; }
    pulse = true;
    launcher.classList.add('ns-discovery-pulse');
    update();
    pulseTimer = window.setTimeout(function () { stopPulse(); update(); }, 3000);
  }
  toggle.addEventListener('click', function () {
    paused = !paused;
    try { localStorage.setItem('nemesis.motion.paused.v1', String(paused)); }
    catch (_) { stored = false; paused = true; }
    update();
  });
  lightSwitch.addEventListener('change', function () {
    marine = lightSwitch.checked;
    try { localStorage.setItem('nemesis.motion.marine.v1', String(marine)); }
    catch (_) { stored = false; marine = false; }
    update();
  });
  function onChange() { update(); discover(); }
  window.addEventListener('load', onChange);
  new MutationObserver(onChange).observe(document.body, {attributes:true, attributeFilter:['class']});
  document.addEventListener('visibilitychange', onChange);
  document.addEventListener('focusin', onChange);
  document.addEventListener('focusout', function () { window.setTimeout(onChange, 0); });
  window.addEventListener('pagehide', function () { stopPulse(); if (light) light.classList.remove('is-running'); });
  window.addEventListener('pageshow', function (event) {
    if (event.persisted && stored) {
      try {
        paused = localStorage.getItem('nemesis.motion.paused.v1') === 'true';
        marine = localStorage.getItem('nemesis.motion.marine.v1') === 'true';
        discovered = localStorage.getItem('nemesis.shark.discovery.v1') === 'seen';
      } catch (_) { stored = false; paused = true; marine = false; discovered = true; }
    }
    onChange();
  });
  window.addEventListener('storage', function (event) {
    if (event.key === 'nemesis.shark.discovery.v1' && event.newValue === 'seen') { discovered = true; stopPulse(); }
    if (event.key === 'nemesis.motion.paused.v1') paused = event.newValue === 'true';
    if (event.key === 'nemesis.motion.marine.v1') marine = event.newValue === 'true';
    update();
  });
  [reduce, transparency].forEach(function (media) {
    if (media.addEventListener) media.addEventListener('change', onChange);
    else if (media.addListener) media.addListener(onChange);
  });
  new MutationObserver(onChange).observe(document.body, {subtree:true, attributes:true, attributeFilter:['open','aria-modal']});
  if (launcher) {
    launcher.addEventListener('animationend', function (event) {
      if (event.animationName === 'ns-discovery-pulse') { stopPulse(); update(); }
    });
    ['pointerdown','keydown','focus','mouseenter'].forEach(function (name) {
      launcher.addEventListener(name, function () { rememberDiscovery(); stopPulse(); update(); });
    });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        launcherVisible = entries[0].isIntersecting;
        if (!launcherVisible) stopPulse();
        onChange();
      }, {threshold:0.8}).observe(launcher);
    } else { rememberDiscovery(); }
  }
  update();
})();
