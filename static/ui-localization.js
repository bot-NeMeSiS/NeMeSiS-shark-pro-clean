(() => {
  'use strict';
  const node = document.getElementById('nemesis-ui-messages');
  const messages = node ? JSON.parse(node.textContent) : {};
  const preferredTerms = (value) => {
    const raw = String(value ?? '');
    if (!/^es(?:-|$)/i.test(document.documentElement.lang || 'es')) return raw;
    return raw.replace(/\bpick\(s\)/gi, 'pronóstico(s)').replace(/\bpicks?\b/gi, (token) => {
      const plural = token.toLowerCase().endsWith('s');
      let replacement = plural ? 'pronósticos' : 'pronóstico';
      if (token === token.toUpperCase()) return replacement.toUpperCase();
      if (token[0] === token[0].toUpperCase()) replacement = replacement[0].toUpperCase() + replacement.slice(1);
      return replacement;
    });
  };
  const formatMadrid = (instant, options) => new Intl.DateTimeFormat(
    document.documentElement.lang || 'es', {...options, timeZone:'Europe/Madrid'}
  ).format(instant);
  window.NemesisI18n = Object.freeze({
    preferredTerms,
    locale: document.documentElement.lang || 'es',
    madridDatetime(value) {
      // Only absolute instants: do not reinterpret manual Madrid civil values.
      if (!/(Z|[+-]\d{2}:?\d{2})$/i.test(String(value))) return this.text('Sin sincronización confirmada');
      const instant = new Date(value);
      if (!Number.isFinite(instant.getTime())) return this.text('Sin sincronización confirmada');
      return formatMadrid(instant, {day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit', hourCycle:'h23'});
    },
    madridClock(instant) {
      return formatMadrid(instant, {hour:'2-digit', minute:'2-digit', second:'2-digit', hourCycle:'h23'});
    },
    madridDate(instant) {
      return formatMadrid(instant, {day:'2-digit', month:'short', year:'numeric'});
    },
    text(source, values = {}) {
      let message = Object.hasOwn(messages, source) ? messages[source] : source;
      if (!Object.hasOwn(messages, source) && typeof source === 'string') {
        const live = /^En directo( · [0-9]{1,3}(?:\+[0-9]{1,2})?['’]?)$/.exec(source);
        if (live && live[0] === source) message = (messages['En directo'] || 'En directo') + live[1];
      }
      message = preferredTerms(message);
      return String(message).replace(/\{(\w+)\}/g, (match, name) => Object.hasOwn(values, name) ? String(values[name]) : match);
    }
  });

  const skipTags = new Set(['SCRIPT','STYLE','CODE','PRE','KBD','SAMP','TEXTAREA']);
  const applyPreferredTerms = (root) => {
    if (!root || !/^es(?:-|$)/i.test(document.documentElement.lang || 'es')) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach((textNode) => {
      const parent = textNode.parentElement;
      if (!parent || skipTags.has(parent.tagName) || parent.closest('[data-keep-internal-term],[contenteditable="true"]')) return;
      const next = preferredTerms(textNode.nodeValue);
      if (next !== textNode.nodeValue) textNode.nodeValue = next;
    });
  };
  document.addEventListener('DOMContentLoaded', () => {
    applyPreferredTerms(document.body);
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => mutation.addedNodes.forEach((added) => {
        if (added.nodeType === Node.TEXT_NODE) {
          const parent = added.parentElement;
          if (parent && !skipTags.has(parent.tagName) && !parent.closest('[data-keep-internal-term],[contenteditable="true"]')) {
            const next = preferredTerms(added.nodeValue);
            if (next !== added.nodeValue) added.nodeValue = next;
          }
        } else if (added.nodeType === Node.ELEMENT_NODE) applyPreferredTerms(added);
      }));
    });
    observer.observe(document.body, {childList:true, subtree:true});
  });
})();
