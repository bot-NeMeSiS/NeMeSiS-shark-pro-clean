(() => {
  "use strict";

  const body = document.body;
  const crestSelector = '.crest,.compact-crest,.v779-crest,.v928-crest,.team-crest,.identity-crest';
  function refreshCrest(box) {
    if (!box || box.tagName === 'IMG') return;
    const image = box.querySelector('img');
    let fallback = box.querySelector('em,[data-fallback-label]');
    if (!fallback) {
      const label = box.dataset.fallback || box.title || image?.alt || box.textContent.trim() || 'NS';
      fallback = document.createElement('em');
      fallback.textContent = box.dataset.fallback || label.split(/\s+/).filter(Boolean).map(word => word[0]).join('').slice(0, 3);
      fallback.setAttribute('aria-hidden', 'true');
      [...box.childNodes].filter(node => node.nodeType === Node.TEXT_NODE).forEach(node => node.textContent = '');
      box.appendChild(fallback);
    }
    if (image) image.removeAttribute('onerror');
    const source = (image?.getAttribute('src') || '').trim();
    let valid = false;
    try { valid = Boolean(source) && ['https:', 'http:'].includes(new URL(source, location.href).protocol); } catch (_) { /* Invalid source uses initials. */ }
    const loaded = Boolean(image && valid && image.complete && image.naturalWidth > 0);
    const pending = Boolean(image && valid && !image.complete);
    box.dataset.crestState = loaded ? 'loaded' : pending ? 'loading' : 'fallback';
    box.classList.toggle('crest-image-error', !loaded && !pending);
    if (image) {
      image.hidden = false;
      image.style.display = loaded || pending ? '' : 'none';
      image.style.visibility = loaded ? 'visible' : 'hidden';
      image.style.gridArea = '1 / 1';
    }
    fallback.style.display = loaded ? 'none' : '';
    fallback.style.visibility = loaded ? 'hidden' : 'visible';
    fallback.style.opacity = loaded ? '0' : '1';
    fallback.style.gridArea = '1 / 1';
  }
  function refreshCrests(root = document) {
    if (root.matches?.(crestSelector)) refreshCrest(root);
    root.querySelectorAll?.(crestSelector).forEach(refreshCrest);
  }
  // Capture failures for late/lazy inserts and also reconcile cached failures.
  for (const eventName of ['load', 'error']) {
    document.addEventListener(eventName, event => {
      if (event.target.tagName === 'IMG') refreshCrest(event.target.closest(crestSelector));
    }, true);
  }
  const crestObserver = new MutationObserver(records => {
    for (const record of records) {
      if (record.type === 'attributes') refreshCrest(record.target.closest(crestSelector));
      else record.addedNodes.forEach(node => {
        if (node.nodeType !== Node.ELEMENT_NODE) return;
        refreshCrests(node);
        refreshCrest(node.closest(crestSelector));
      });
    }
  });
  if (body) {
    refreshCrests(body);
    crestObserver.observe(body, {childList: true, subtree: true, attributes: true, attributeFilter: ['src', 'srcset']});
  }
  if (!body || body.classList.contains("ns-admin") || body.dataset.admin === "true") return;

  const route = body.dataset.nsRoute || body.dataset.route || location.pathname || "/";
  body.classList.add("v937-client-route");
  body.dataset.v937Route = route;

  document.querySelectorAll("img").forEach((image) => {
    if (image.closest(crestSelector)) return;
    image.addEventListener(
      "error",
      () => {
        image.hidden = true;
        image.parentElement?.classList.add("v937-image-fallback");
      },
      { once: true }
    );
  });

  const memoryKey = "nemesis.launch.recentRoutes.v1";
  const onboardingKey = "nemesis.launch.onboarding.dismissed.v1";
  const allowedRoutePrefixes = [
    "/",
    "/app",
    "/calendar",
    "/calendario",
    "/live",
    "/picks",
    "/track-record",
    "/telegram",
    "/memberships",
    "/membresias",
    "/favorites",
    "/profile",
    "/user-intelligence",
    "/smart-home",
    "/daily-briefing",
    "/evening-recap",
    "/activity-center",
    "/shark",
    "/shark-intelligence",
    "/match/",
    "/team/",
    "/competition/",
    "/player/",
  ];

  function storageAvailable() {
    try {
      const probe = "nemesis.launch.probe";
      window.localStorage.setItem(probe, "1");
      window.localStorage.removeItem(probe);
      return true;
    } catch (error) {
      return false;
    }
  }

  const hasStorage = storageAvailable();

  function normalizePath(path) {
    try {
      return new URL(path, location.origin).pathname;
    } catch (error) {
      return "/";
    }
  }

  function isSafeRoute(path) {
    const normalized = normalizePath(path);
    if (!normalized.startsWith("/") || normalized.startsWith("/api") || normalized.startsWith("/admin")) return false;
    return allowedRoutePrefixes.some((prefix) => normalized === prefix || (prefix !== "/" && normalized.startsWith(prefix)));
  }

  function routeLabel(path) {
    const normalized = normalizePath(path);
    if (normalized.startsWith("/match/")) return "Volver al partido";
    if (normalized.startsWith("/team/")) return "Volver al equipo";
    if (normalized.startsWith("/competition/")) return "Volver a la competicion";
    if (normalized.startsWith("/player/")) return "Volver al jugador";
    if (normalized.startsWith("/calendar") || normalized.startsWith("/calendario")) return "Calendario";
    if (normalized.startsWith("/favorites")) return "Favoritos";
    if (normalized.startsWith("/daily-briefing")) return "Briefing diario";
    if (normalized.startsWith("/evening-recap")) return "Recap nocturno";
    if (normalized.startsWith("/activity-center")) return "Actividad reciente";
    if (normalized.startsWith("/shark")) return "SHARK";
    if (normalized.startsWith("/smart-home")) return "Smart Home";
    if (normalized.startsWith("/memberships") || normalized.startsWith("/membresias")) return "Planes";
    if (normalized.startsWith("/picks")) return "Picks";
    if (normalized.startsWith("/live")) return "Directo";
    if (normalized.startsWith("/app")) return "Mi panel";
    return "Continuar";
  }

  function readRecentRoutes() {
    if (!hasStorage) return [];
    try {
      const parsed = JSON.parse(window.localStorage.getItem(memoryKey) || "[]");
      return Array.isArray(parsed) ? parsed.filter((item) => item && isSafeRoute(item.path)).slice(0, 6) : [];
    } catch (error) {
      return [];
    }
  }

  function writeRecentRoutes(items) {
    if (!hasStorage) return;
    try {
      window.localStorage.setItem(memoryKey, JSON.stringify(items.slice(0, 6)));
    } catch (error) {
      // Local continuity is optional; the app remains fully usable without it.
    }
  }

  let recentRoutes = readRecentRoutes();
  const normalizedRoute = normalizePath(route);
  if (isSafeRoute(normalizedRoute) && normalizedRoute !== "/") {
    recentRoutes = [
      { path: normalizedRoute, label: routeLabel(normalizedRoute), at: new Date().toISOString() },
      ...recentRoutes.filter((item) => normalizePath(item.path) !== normalizedRoute),
    ].slice(0, 6);
    writeRecentRoutes(recentRoutes);
  }

  const continueLink = document.querySelector("[data-launch-continue]");
  if (continueLink) {
    const nextRoute = recentRoutes.find((item) => normalizePath(item.path) !== normalizedRoute && normalizePath(item.path) !== "/");
    if (nextRoute) {
      continueLink.setAttribute("href", nextRoute.path);
      continueLink.querySelector("strong") && (continueLink.querySelector("strong").textContent = nextRoute.label || "Continuar");
      continueLink.querySelector("small") && (continueLink.querySelector("small").textContent = "Ultimo contexto abierto en este navegador.");
    }
  }

  const lastMatchLink = document.querySelector("[data-launch-last-match]");
  if (lastMatchLink) {
    const lastMatch = recentRoutes.find((item) => normalizePath(item.path).startsWith("/match/"));
    if (lastMatch) {
      lastMatchLink.setAttribute("href", lastMatch.path);
      lastMatchLink.querySelector("strong") && (lastMatchLink.querySelector("strong").textContent = "Volver al partido");
      lastMatchLink.querySelector("small") && (lastMatchLink.querySelector("small").textContent = "Ultimo Match Center abierto.");
    }
  }

  const onboarding = document.querySelector("[data-launch-onboarding]");
  if (onboarding) {
    let dismissed = false;
    if (hasStorage) {
      dismissed = window.localStorage.getItem(onboardingKey) === "1";
    }
    if (dismissed) {
      onboarding.classList.add("is-hidden");
    } else {
      body.dataset.launchOnboarding = "visible";
    }
    const dismissButton = onboarding.querySelector("[data-launch-onboarding-dismiss]");
    dismissButton?.addEventListener("click", () => {
      if (hasStorage) window.localStorage.setItem(onboardingKey, "1");
      onboarding.classList.add("is-hidden");
      body.dataset.launchOnboarding = "dismissed";
    });
  }
})();
