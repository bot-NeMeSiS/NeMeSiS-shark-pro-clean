(() => {
  "use strict";

  const body = document.body;
  if (!body || body.classList.contains("ns-admin") || body.dataset.admin === "true") return;

  const route = body.dataset.nsRoute || body.dataset.route || location.pathname || "/";
  body.classList.add("v937-client-route");
  body.dataset.v937Route = route;

  document.querySelectorAll("img").forEach((image) => {
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
