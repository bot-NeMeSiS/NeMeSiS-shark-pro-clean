(() => {
  'use strict';
  const node = document.getElementById('nemesis-ui-messages');
  const messages = node ? JSON.parse(node.textContent) : {};
  const formatMadrid = (instant, options) => new Intl.DateTimeFormat(
    document.documentElement.lang || 'es', {...options, timeZone:'Europe/Madrid'}
  ).format(instant);
  window.NemesisI18n = Object.freeze({
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
      return String(message).replace(/\{(\w+)\}/g, (match, name) => Object.hasOwn(values, name) ? String(values[name]) : match);
    }
  });
})();
