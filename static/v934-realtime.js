(function v934RealtimeSports() {
  'use strict';

  var bars = Array.prototype.slice.call(document.querySelectorAll('[data-v934-realtime]'));
  var adminButtons = Array.prototype.slice.call(document.querySelectorAll('[data-v934-admin-action]'));
  if (!bars.length && !adminButtons.length) return;
  var shared = window.__nemesisV935Realtime || (window.__nemesisV935Realtime = { entries: {} });

  function number(value) {
    var parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function clampPoll(value) {
    return Math.max(30, Math.min(number(value) || 180, 300));
  }

  function jitteredPoll(value) {
    var seconds = clampPoll(value);
    return Math.max(30, Math.round(seconds * (0.92 + Math.random() * 0.16)));
  }

  function sharedLoad(endpoint, scope) {
    var key = endpoint + '?scope=' + encodeURIComponent(scope);
    var entry = shared.entries[key] || (shared.entries[key] = { payload: null, fetchedAt: 0, etag: '', modified: '', pending: null });
    if (entry.payload && Date.now() - entry.fetchedAt < 15000) return Promise.resolve(entry.payload);
    if (entry.pending) return entry.pending;
    var headers = { Accept: 'application/json' };
    if (entry.etag) headers['If-None-Match'] = entry.etag;
    if (entry.modified) headers['If-Modified-Since'] = entry.modified;
    entry.pending = fetch(key, { headers: headers, cache: 'no-cache' })
      .then(function (response) {
        if (response.status === 304 && entry.payload) return entry.payload;
        if (!response.ok) throw new Error('http_' + response.status);
        entry.etag = response.headers.get('ETag') || entry.etag;
        entry.modified = response.headers.get('Last-Modified') || entry.modified;
        return response.json();
      })
      .then(function (payload) {
        if (!payload || payload.ok !== true) throw new Error('unsafe_payload');
        entry.payload = payload;
        entry.fetchedAt = Date.now();
        return payload;
      })
      .finally(function () { entry.pending = null; });
    return entry.pending;
  }

  function setText(root, selector, value) {
    var node = root.querySelector(selector);
    if (node && value !== undefined && value !== null) node.textContent = String(value);
  }

  function updateMatch(match) {
    if (!match || !match.id) return;
    document.querySelectorAll('[data-v934-match-id="' + CSS.escape(String(match.id)) + '"]').forEach(function (card) {
      card.classList.toggle('is-stale', Boolean(match.is_stale));
      var score = card.querySelector('[data-v934-score]');
      if (score && match.home_score !== null && match.home_score !== undefined && match.away_score !== null && match.away_score !== undefined) {
        score.textContent = match.home_score + ' - ' + match.away_score;
      }
      var status = card.querySelector('[data-v934-status] .v933-status-chip') || card.querySelector('[data-v934-status]');
      if (status) {
        status.textContent = match.status_label || 'Estado actualizado';
        status.classList.remove('is-success', 'is-blue', 'is-warning', 'is-neutral');
        status.classList.add(match.is_stale ? 'is-warning' : match.is_live ? 'is-success' : 'is-blue');
      }
      var minute = card.querySelector('[data-v934-minute]');
      if (minute) {
        var hasMinute = match.minute !== null && match.minute !== undefined && match.is_live;
        minute.hidden = !hasMinute;
        minute.textContent = hasMinute ? 'Min ' + match.minute : '';
      }
    });
  }

  function updatePick(pick) {
    if (!pick || !pick.id) return;
    document.querySelectorAll('[data-v934-pick-id="' + CSS.escape(String(pick.id)) + '"]').forEach(function (card) {
      setText(card, '[data-v934-odds]', pick.odds);
      var freshness = card.querySelector('[data-v934-odds-freshness]');
      if (freshness && pick.odds_freshness) {
        freshness.textContent = pick.odds_freshness.label || 'Última registrada';
        freshness.className = 'v934-odds-freshness is-' + (pick.odds_freshness.status || 'recorded');
      }
    });
  }

  function render(bar, payload) {
    var counts = payload.counts || {};
    ['matches', 'live', 'picks'].forEach(function (key) {
      setText(bar, '[data-v934-count="' + key + '"]', counts[key] || 0);
    });
    var hasLive = number(counts.live) > 0;
    var hasData = number(counts.matches) > 0 || number(counts.picks) > 0;
    setText(bar, '[data-v934-realtime-title]', hasLive ? 'Actualización en directo' : hasData ? 'Datos deportivos sincronizados' : 'Esperando datos reales');
    setText(bar, '[data-v934-realtime-message]', payload.safe_message || 'La vista se mantiene operativa con DB y caché.');
    var technical = bar.getAttribute('data-v934-technical') === 'true';
    setText(bar, '[data-v934-cache-state]', technical ? (payload.cache_state || payload.cache_status || 'cache seguro') : 'Actualización segura');
    setText(bar, '[data-v934-last-sync]', payload.last_safe_sync || 'Sin sincronización confirmada');
    setText(bar, '[data-v934-next-refresh]', 'Próxima revisión en ' + clampPoll(payload.poll_after_seconds) + ' s');
    bar.classList.toggle('is-live', hasLive);
    bar.classList.toggle('is-stale', payload.realtime_live_status === 'stale');
    bar.classList.remove('is-error');
    (payload.matches || []).forEach(updateMatch);
    (payload.live || []).forEach(updateMatch);
    (payload.picks || []).forEach(updatePick);
  }

  function start(bar) {
    var failures = 0;
    var timer = null;
    var endpoint = bar.getAttribute('data-v934-endpoint') || '/api/realtime/sports';
    var scope = bar.getAttribute('data-v934-realtime') || 'all';

    function schedule(seconds) {
      window.clearTimeout(timer);
      timer = window.setTimeout(load, jitteredPoll(seconds) * 1000);
    }

    function load() {
      if (document.hidden) {
        schedule(180);
        return;
      }
      sharedLoad(endpoint, scope)
        .then(function (payload) {
          failures = 0;
          render(bar, payload);
          schedule(payload.poll_after_seconds);
        })
        .catch(function () {
          failures += 1;
          bar.classList.add('is-error');
          setText(bar, '[data-v934-realtime-message]', 'Actualización temporalmente no disponible. Se conserva la última lectura segura.');
          schedule(Math.min(300, 30 * Math.pow(2, Math.min(failures, 3))));
        });
    }

    schedule(Math.min(45, clampPoll(bar.getAttribute('data-v934-poll'))));
    bar.addEventListener('v934:refresh', function () { schedule(1); });
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) schedule(1);
    });
  }

  bars.forEach(start);

  adminButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      var endpoint = button.getAttribute('data-v934-admin-action');
      var output = document.querySelector('[data-v934-admin-output]');
      if (!endpoint || button.disabled) return;
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      if (output) output.textContent = 'Ejecutando acción segura...';
      fetch(endpoint, { method: 'POST', headers: window.nemesisJsonHeaders ? window.nemesisJsonHeaders() : { 'Content-Type': 'application/json' }, body: '{}' })
        .then(function (response) { return response.json().then(function (payload) { return { ok: response.ok, payload: payload }; }); })
        .then(function (result) {
          if (output) output.textContent = result.payload.safe_message || result.payload.status || (result.ok ? 'Acción completada.' : 'No se pudo completar.');
          if (result.ok) bars.forEach(function (bar) { bar.dispatchEvent(new Event('v934:refresh')); });
        })
        .catch(function () { if (output) output.textContent = 'No se pudo completar la acción segura.'; })
        .finally(function () { button.disabled = false; button.removeAttribute('aria-busy'); });
    });
  });
})();
