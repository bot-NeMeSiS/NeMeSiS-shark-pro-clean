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

/* Progressive SSR sports slides. Presentation only: never replace fixture links. */
(function homeFeaturedSlides() {
  'use strict';
  document.querySelectorAll('[data-home-featured]').forEach(function (root) {
    if (root.getAttribute('data-home-featured-ready') === 'true') return;
    var slides = Array.prototype.slice.call(root.querySelectorAll('[data-home-featured-slide]'));
    var controls = root.querySelector('[data-home-featured-controls]');
    if (slides.length < 2) {
      if (controls) controls.hidden = true;
      return;
    }
    var previous = root.querySelector('[data-home-featured-prev]');
    var next = root.querySelector('[data-home-featured-next]');
    var toggle = root.querySelector('[data-home-featured-toggle]');
    var counter = root.querySelector('[data-home-featured-counter]');
    var status = root.querySelector('[data-home-featured-status]');
    if (!controls || !previous || !next || !toggle || !counter) return;
    root.setAttribute('data-home-featured-ready', 'true');

    var reduce = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : {matches:true};
    var globalToggle = document.querySelector('[data-motion-preferences] [data-motion-toggle]');
    var index = 0, timer = null, hovering = false, pointerHeld = false, pageAway = false;
    var focusWithin = root.contains(document.activeElement);
    var inView = !('IntersectionObserver' in window);
    function globalMotionAllowed() {
      return !globalToggle || (!globalToggle.disabled && globalToggle.getAttribute('aria-pressed') === 'false');
    }
    var wantsPlay = !reduce.matches && !document.hidden && globalMotionAllowed();

    function stopTimer() {
      if (timer !== null) window.clearTimeout(timer);
      timer = null;
    }
    function updateToggle() {
      toggle.textContent = toggle.getAttribute(wantsPlay ? 'data-pause' : 'data-play') || (wantsPlay ? 'Pausar' : 'Reanudar');
      toggle.setAttribute('aria-pressed', String(!wantsPlay));
    }
    function pause() {
      wantsPlay = false;
      stopTimer();
      updateToggle();
    }
    function writing() {
      var focus = document.activeElement;
      return Boolean(focus && !root.contains(focus) &&
        (focus.isContentEditable || (focus.matches && focus.matches('input:not([type=checkbox]):not([type=radio]):not([type=button]):not([type=submit]),textarea,select'))));
    }
    function canAdvance() {
      return wantsPlay && !reduce.matches && !document.hidden && !pageAway && inView &&
        !hovering && !pointerHeld && !focusWithin && globalMotionAllowed() && !writing() &&
        !document.querySelector('dialog[open], [role="dialog"][aria-modal="true"]:not([hidden])');
    }
    function show(position, manual) {
      index = (position + slides.length) % slides.length;
      slides.forEach(function (slide, offset) {
        slide.hidden = offset !== index;
        if ('inert' in slide) slide.inert = offset !== index;
      });
      counter.textContent = (index + 1) + ' / ' + slides.length;
      if (manual && status) status.textContent = counter.textContent;
    }
    function schedule() {
      stopTimer();
      if (!canAdvance()) return;
      timer = window.setTimeout(function () {
        timer = null;
        if (!canAdvance()) return;
        show(index + 1, false);
        schedule();
      }, 9000);
    }
    function stopForInteraction(event) {
      stopTimer();
      // Preserve the toggle's intent until its click: focus/pointer events must
      // not turn a requested Pause into Play, or a requested Play into Pause.
      if (!toggle.contains(event.target)) pause();
    }
    previous.addEventListener('click', function () { pause(); show(index - 1, true); });
    next.addEventListener('click', function () { pause(); show(index + 1, true); });
    toggle.addEventListener('click', function () {
      stopTimer();
      wantsPlay = !wantsPlay && !reduce.matches && !document.hidden && !pageAway && globalMotionAllowed();
      updateToggle();
      if (status) status.textContent = toggle.textContent;
      schedule();
    });
    root.addEventListener('pointerdown', function (event) {
      pointerHeld = true;
      stopForInteraction(event);
    }, true);
    root.addEventListener('keydown', stopForInteraction, true);
    root.addEventListener('focusin', function (event) {
      focusWithin = true;
      stopForInteraction(event);
    });
    root.addEventListener('focusout', function (event) {
      focusWithin = root.contains(event.relatedTarget);
      schedule();
    });
    root.addEventListener('mouseenter', function () { hovering = true; stopTimer(); });
    root.addEventListener('mouseleave', function () { hovering = false; schedule(); });
    window.addEventListener('pointerup', function () { pointerHeld = false; schedule(); });
    window.addEventListener('pointercancel', function () { pointerHeld = false; schedule(); });
    document.addEventListener('focusin', function () { if (writing()) stopTimer(); else schedule(); });
    document.addEventListener('visibilitychange', function () { if (document.hidden) { pointerHeld = false; hovering = false; pause(); } });
    window.addEventListener('pagehide', function () { pageAway = true; pointerHeld = false; hovering = false; pause(); });
    window.addEventListener('pageshow', function (event) {
      pageAway = false;
      if (event.persisted) pause();
      else schedule();
    });
    function reducedMotionChanged() { if (reduce.matches) pause(); }
    if (reduce.addEventListener) reduce.addEventListener('change', reducedMotionChanged);
    else if (reduce.addListener) reduce.addListener(reducedMotionChanged);
    if ('IntersectionObserver' in window) {
      new window.IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.target !== root) return;
          inView = entry.isIntersecting && entry.intersectionRatio >= 0.5;
        });
        schedule();
      }, {threshold:0.5}).observe(root);
    }
    if (typeof MutationObserver !== 'undefined') {
      if (globalToggle) {
        new MutationObserver(function () {
          if (!globalMotionAllowed()) pause();
        }).observe(globalToggle, {attributes:true, attributeFilter:['aria-pressed', 'disabled']});
      }
      new MutationObserver(function (entries) {
        if (entries.some(function (entry) {
          return entry.target.matches && entry.target.matches('dialog,[role="dialog"]');
        })) schedule();
      }).observe(document.body, {subtree:true, attributes:true, attributeFilter:['open', 'aria-modal', 'hidden']});
    }
    controls.hidden = false;
    show(0, false);
    updateToggle();
    schedule();
  });
})();
