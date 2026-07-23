/* V940 Calendar progressive enhancement: local context only, no API or DB writes. */
(() => {
  "use strict";

  const root = document.querySelector("[data-v940-calendar-experience]");
  if (!root) return;

  const search = root.querySelector("[data-v940-calendar-search]");
  const currentContext = root.querySelector("[data-v940-current-context]");
  const sections = Array.from(root.querySelectorAll("[data-v940-calendar-section]"));
  const storageKey = `nemesis:v940:calendar:${window.location.pathname}${window.location.search}`;
  const maxRestoreAgeMs = 2 * 60 * 60 * 1000;

  const storage = {
    get() {
      try {
        return window.sessionStorage.getItem(storageKey);
      } catch (_error) {
        return null;
      }
    },
    set(value) {
      try {
        window.sessionStorage.setItem(storageKey, value);
      } catch (_error) {
        /* Calendar remains fully usable without session storage. */
      }
    },
  };

  function savePosition() {
    storage.set(JSON.stringify({
      url: `${window.location.pathname}${window.location.search}`,
      scrollY: Math.max(0, Math.round(window.scrollY || 0)),
      context: currentContext ? currentContext.textContent.trim() : "",
      savedAt: Date.now(),
    }));
  }

  function navigationType() {
    if (!window.performance || !window.performance.getEntriesByType) return "";
    const entries = window.performance.getEntriesByType("navigation");
    return entries.length ? entries[0].type : "";
  }

  function restorePosition() {
    if (navigationType() !== "back_forward") return;
    const raw = storage.get();
    if (!raw) return;
    try {
      const state = JSON.parse(raw);
      const currentUrl = `${window.location.pathname}${window.location.search}`;
      if (state.url !== currentUrl || Date.now() - Number(state.savedAt || 0) > maxRestoreAgeMs) return;
      if (currentContext && state.context) currentContext.textContent = state.context;
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => window.scrollTo(0, Number(state.scrollY || 0)));
      });
    } catch (_error) {
      /* Ignore malformed local state; server-rendered navigation stays intact. */
    }
  }

  function updateCurrentContext(entries) {
    if (!currentContext) return;
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((left, right) => right.intersectionRatio - left.intersectionRatio);
    const target = visible.length ? visible[0].target : null;
    const label = target ? target.getAttribute("data-v940-context-label") : "";
    if (label) currentContext.textContent = label;
  }

  if ("IntersectionObserver" in window && sections.length) {
    const observer = new IntersectionObserver(updateCurrentContext, {
      root: null,
      rootMargin: "-92px 0px -62% 0px",
      threshold: [0, 0.2, 0.55, 1],
    });
    sections.forEach((section) => observer.observe(section));
  }

  document.addEventListener("keydown", (event) => {
    if (
      event.key !== "/"
      || event.defaultPrevented
      || event.ctrlKey
      || event.metaKey
      || event.altKey
      || /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement ? document.activeElement.tagName : "")
    ) return;
    if (search) {
      event.preventDefault();
      search.focus();
      search.select();
    }
  });

  root.addEventListener("click", (event) => {
    const matchLink = event.target.closest("[data-v934-match-card] a");
    if (matchLink) savePosition();
  });
  window.addEventListener("pagehide", savePosition);
  restorePosition();
})();
