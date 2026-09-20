(() => {
  'use strict';
  // Only choose the initial composition; subsequent user toggles stay native.
  if (window.matchMedia('(max-width: 700px)').matches) {
    document.querySelectorAll('[data-account-disclosure]').forEach((panel) => {
      panel.open = false;
    });
  }
})();
