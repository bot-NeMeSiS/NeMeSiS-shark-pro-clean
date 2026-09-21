/* Calendar progressive enhancement: navigation context, never a second sports feed. */
(() => {
  "use strict";
  const root = document.querySelector("[data-v940-calendar-experience]");
  if (!root || root.dataset.v940Enhanced === "true") return;
  root.dataset.v940Enhanced = "true";

  const search = root.querySelector("[data-v940-calendar-search]");
  const form = root.querySelector("[data-v940-discovery-form]");
  const pending = root.querySelector("[data-v940-pending-filters]");
  if (form && pending) {
    // A detached, reset clone reads server defaults, not browser-restored edits.
    const original = form.cloneNode(true);
    original.reset();
    const applied = new URLSearchParams(new FormData(original)).toString();
    const updatePending = () => {
      pending.hidden = new URLSearchParams(new FormData(form)).toString() === applied;
    };
    form.addEventListener("input", updatePending);
    form.addEventListener("change", updatePending);
    form.addEventListener("reset", () => window.requestAnimationFrame(updatePending));
    window.addEventListener("pageshow", updatePending);
    updatePending();
  }

  const currentContext = root.querySelector("[data-v940-current-context]");
  const sections = Array.from(root.querySelectorAll("[data-v940-calendar-section]"));
  const currentUrl = `${window.location.pathname}${window.location.search}`;
  const storageKey = `nemesis:v940:calendar:${document.documentElement.lang}:${currentUrl}`;
  const maxRestoreAgeMs = 2 * 60 * 60 * 1000;
  let sectionId = "";
  let userInteracted = false;

  const storage = {
    get() {
      try { return window.sessionStorage.getItem(storageKey); }
      catch (_error) { return null; }
    },
    set(value) {
      try { window.sessionStorage.setItem(storageKey, value); }
      catch (_error) { /* Native GET navigation works without storage. */ }
    },
  };

  function savePosition() {
    const y = Number(window.scrollY || 0);
    storage.set(JSON.stringify({
      contract: "calendar-position-v2", url: currentUrl,
      scrollY: Number.isFinite(y) ? Math.max(0, Math.round(y)) : 0,
      sectionId, savedAt: Date.now(),
    }));
  }

  function navigationType() {
    if (!window.performance || !window.performance.getEntriesByType) return "";
    const entries = window.performance.getEntriesByType("navigation");
    return entries.length ? entries[0].type : "";
  }

  function restorePosition() {
    // Do not override a fresh visit, reload, explicit anchor, or the user's input.
    if (navigationType() !== "back_forward" || window.location.hash) return;
    const raw = storage.get();
    if (!raw) return;
    try {
      const state = JSON.parse(raw);
      if (!state || state.contract !== "calendar-position-v2" || state.url !== currentUrl) return;
      const age = Date.now() - state.savedAt;
      if (typeof state.savedAt !== "number" || !Number.isFinite(state.savedAt)
          || age < 0 || age > maxRestoreAgeMs
          || typeof state.scrollY !== "number" || !Number.isFinite(state.scrollY)
          || state.scrollY < 0) return;
      window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
        if (userInteracted || window.location.hash) return;
        // Labels always come from this response, not a cached sports observation.
        const section = sections.find((element) => element.id === state.sectionId);
        const label = section ? section.getAttribute("data-v940-context-label") : "";
        if (currentContext && label) {
          currentContext.textContent = label;
          sectionId = section.id;
        }
        const maximum = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
        window.scrollTo({top: Math.min(state.scrollY, maximum), left: 0, behavior: "instant"});
      }));
    } catch (_error) { /* Malformed local state does not alter server content. */ }
  }

  const visibleSections = new Map();
  function updateCurrentContext(entries) {
    if (!currentContext) return;
    entries.forEach((entry) => {
      if (entry.isIntersecting) visibleSections.set(entry.target, entry.intersectionRatio);
      else visibleSections.delete(entry.target);
    });
    const visible = Array.from(visibleSections).sort((left, right) => right[1] - left[1]);
    const target = visible.length ? visible[0][0] : null;
    const label = target ? target.getAttribute("data-v940-context-label") : "";
    if (label) { currentContext.textContent = label; sectionId = target.id || ""; }
  }
  if ("IntersectionObserver" in window && sections.length) {
    const observer = new IntersectionObserver(updateCurrentContext, {
      root: null, rootMargin: "-92px 0px -62% 0px", threshold: [0, 0.2, 0.55, 1],
    });
    sections.forEach((section) => observer.observe(section));
  }

  ["pointerdown", "touchstart", "wheel"].forEach((name) => {
    document.addEventListener(name, () => { userInteracted = true; }, {capture: true, passive: true});
  });
  document.addEventListener("keydown", (event) => {
    userInteracted = true;
    const active = document.activeElement;
    const target = event.target instanceof Element ? event.target : active;
    if (event.key !== "/" || event.defaultPrevented || event.ctrlKey || event.metaKey
        || event.altKey || event.repeat || event.isComposing || !root.contains(active)
        || (target && target.closest("input,textarea,select,[contenteditable]:not([contenteditable='false']),[role='textbox'],[role='combobox'],[role='searchbox'],[role='dialog'],[aria-modal='true']"))) return;
    if (search) { event.preventDefault(); search.focus(); search.select(); }
  });

  root.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    const plainClick = !event.defaultPrevented && event.button === 0
      && !event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey;
    if (!plainClick) return;
    const link = target.closest("a");
    if (!link || link.hasAttribute("download") || (link.target && link.target !== "_self")) return;
    if (link.getAttribute("href") === "#v933-calendar-filters" && search) {
      // Native anchor scroll and history remain intact; keyboard focus follows.
      window.requestAnimationFrame(() => search.focus({preventScroll: true}));
    }
    if (link.closest("[data-v934-match-card]")) savePosition();
  });
  window.addEventListener("pagehide", savePosition);
  restorePosition();
})();
