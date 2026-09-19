(function v934RealtimeSports() {
  'use strict';

  var bars = Array.prototype.slice.call(document.querySelectorAll('[data-v934-realtime]'));
  var adminButtons = Array.prototype.slice.call(document.querySelectorAll('[data-v934-admin-action]'));
  if (!bars.length && !adminButtons.length) return;
  var shared = window.__nemesisV935Realtime || (window.__nemesisV935Realtime = { entries: {} });
  function text(source, values) {
    return window.NemesisI18n ? window.NemesisI18n.text(source, values) : source;
  }

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
    if (entry.payload && Date.now() - entry.fetchedAt < 15000) return Promise.resolve({payload: entry.payload, serverTime: entry.serverTime, receivedMono: entry.receivedMono});
    if (entry.pending) return entry.pending;
    var headers = { Accept: 'application/json' };
    if (entry.etag) headers['If-None-Match'] = entry.etag;
    if (entry.modified) headers['If-Modified-Since'] = entry.modified;
    var controller = new AbortController();
    var timeout = window.setTimeout(function () { controller.abort(); }, 12000);
    var serverTime = NaN;
    var requestStart = performance.now();
    entry.pending = fetch(key, { headers: headers, cache: 'no-cache', signal: controller.signal })
      .then(function (response) {
        var date = Date.parse(response.headers.get('Date') || '');
        // HTTP Date has one-second precision: use its conservative upper bound.
        serverTime = Number.isFinite(date) ? date + 1000 + (performance.now() - requestStart) : NaN;
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
        entry.serverTime = serverTime;
        entry.receivedMono = performance.now();
        return {payload: payload, serverTime: serverTime, receivedMono: entry.receivedMono};
      })
      .finally(function () { window.clearTimeout(timeout); entry.pending = null; });
    return entry.pending;
  }

  function setText(root, selector, value) {
    var node = root.querySelector(selector);
    if (node && value !== undefined && value !== null) node.textContent = String(value);
  }

  function updateSyncTimestamp(bar, payload, technical) {
    var node = bar.querySelector('[data-v934-last-sync]');
    if (!node) return;
    var rawSync = String(payload.last_safe_sync || '').trim();
    if (rawSync) {
      node.setAttribute('datetime', rawSync);
      node.setAttribute('data-v934-last-sync-raw', rawSync);
    } else {
      node.removeAttribute('datetime');
      node.removeAttribute('data-v934-last-sync-raw');
    }
    var clientLabel = payload.last_safe_sync_label || text('Sin sincronización confirmada');
    if (window.NemesisI18n && window.NemesisI18n.locale !== 'es' && rawSync) {
      clientLabel = window.NemesisI18n.madridDatetime(rawSync);
    }
    node.textContent = technical
      ? (rawSync || 'Sin sincronización confirmada')
      : clientLabel;
  }

  function updateMatch(match) {
    if (!match || !match.id) return;
    document.querySelectorAll('[data-v934-match-id="' + CSS.escape(String(match.id)) + '"]').forEach(function (card) {
      card.classList.toggle('is-stale', Boolean(match.is_stale));
      var score = card.querySelector('[data-v934-score]');
      var upcoming = ['UPCOMING', 'SCHEDULED', 'PREMATCH', 'NOT_STARTED', 'NS'].includes(
        String(match.canonical_status || match.status_key || match.status || '').toUpperCase()
      ) && !match.is_live && !match.is_stale;
      if (score && match.home_score !== null && match.home_score !== undefined && match.away_score !== null && match.away_score !== undefined) {
        score.textContent = match.home_score + ' - ' + match.away_score;
        score.hidden = false;
        card.querySelectorAll('[data-match-kickoff-clock],[data-match-kickoff-zone]').forEach(function (node) { node.hidden = true; });
      } else if (score) {
        score.textContent = 'VS';
        var hasClock = Boolean(card.querySelector('[data-match-kickoff-clock]'));
        score.hidden = upcoming && hasClock;
        card.querySelectorAll('[data-match-kickoff-clock],[data-match-kickoff-zone]').forEach(function (node) { node.hidden = !upcoming; });
      }
      var status = card.querySelector('[data-v934-status] .v933-status-chip') || card.querySelector('[data-v934-status]');
      if (status) {
        status.textContent = text(match.status_label || 'Estado actualizado');
        status.classList.remove('is-success', 'is-blue', 'is-warning', 'is-neutral');
        status.classList.add(match.is_stale ? 'is-warning' : match.is_live ? 'is-success' : 'is-blue');
      }
      var minute = card.querySelector('[data-v934-minute]');
      if (minute) {
        var hasMinute = match.minute !== null && match.minute !== undefined && match.is_live;
        minute.hidden = !hasMinute;
        minute.textContent = hasMinute ? text('Min') + ' ' + match.minute : '';
      }
    });
  }

  // Directo consumes the existing poller, not a second network loop. The server
  // exports the publication deadline. This controller can WITHDRAW a LIVE claim;
  // it cannot infer kickoff, minutes, goals, final scores or restored freshness.
  function createDirectoController(root) {
    var records = new Map();
    var wrappers = new Map();
    var completeCount = false;
    var hasResponse = false;
    var expiryTimer = null;
    var stopped = false;
    var lastFrame = Date.parse(root.getAttribute('data-directo-evaluated-at') || '') || -Infinity;
    var statuses = {
      LIVE: 'En directo', HALFTIME: 'Descanso', FINISHED: 'Finalizado', ARCHIVED: 'Finalizado',
      STALE: 'Datos retrasados', INCOMPLETE: 'Estado pendiente', RESULT_PENDING: 'Resultado pendiente',
      UPCOMING: 'Programado', POSTPONED: 'Aplazado', SUSPENDED: 'Suspendido',
      CANCELLED: 'Cancelado', ABANDONED: 'Abandonado'
    };
    function stamp(value) {
      return typeof value === 'string' && /(?:Z|[+-]\d\d:\d\d)$/.test(value)
        ? Date.parse(value) : NaN;
    }
    function valid(state) {
      if (!state || state.contract !== 'NEMESIS-REALTIME-STATE-V1' ||
          state.sports_truth_contract !== 'MATCH-STATUS-TRUTH-V2' ||
          !Object.prototype.hasOwnProperty.call(statuses, state.status_canonical) ||
          typeof state.fixture_id !== 'string' || !state.fixture_id ||
          !Number.isFinite(stamp(state.evaluated_at_madrid))) return false;
      if (['is_live', 'is_stale', 'is_finished', 'status_conflict'].some(function (key) {
        return typeof state[key] !== 'boolean';
      })) return false;
      return !state.is_live || (!state.is_stale && !state.is_finished && !state.status_conflict &&
        ['LIVE', 'HALFTIME'].includes(state.status_canonical) && state.freshness_state === 'FRESH' &&
        typeof state.provider === 'string' && Boolean(state.provider) &&
        Number.isFinite(stamp(state.provider_observed_at)) &&
        Number.isFinite(stamp(state.live_valid_until_madrid)));
    }
    function remaining(entry) {
      // Date delta catches suspension on platforms whose monotonic clock sleeps;
      // a clock rollback never adds time. Repeated responses never reset a lease.
      return entry.budget - Math.max(0, performance.now() - entry.mono, Date.now() - entry.wall);
    }
    function live(entry) {
      return Boolean(entry && entry.state.is_live && !entry.withheld && remaining(entry) > 0);
    }
    function sameIdentity(a, b) {
      if (a.fixture_id !== b.fixture_id || a.provider !== b.provider) return false;
      return ['competition_id', 'season', 'home_team_id', 'away_team_id'].every(function (key) {
        return !a[key] || !b[key] || a[key] === b[key];
      });
    }
    function accept(id, state, serverNow) {
      var previous = records.get(id);
      if (!valid(state)) {
        if (previous) previous.withheld = 'Información sin confirmar';
        return false;
      }
      var evaluated = stamp(state.evaluated_at_madrid);
      var observed = stamp(state.provider_observed_at);
      if (previous) {
        if (!sameIdentity(previous.state, state)) {
          previous.withheld = 'Identidad pendiente de confirmar';
          return false;
        }
        if (evaluated < previous.evaluated || (Number.isFinite(observed) &&
            Number.isFinite(previous.observed) && observed < previous.observed)) return false;
        // A terminal state cannot be undone by a late/replayed LIVE snapshot.
        if (previous.state.is_finished && state.is_live) return false;
        if (state.is_live && observed === previous.observed &&
            (state.score_home !== previous.state.score_home || state.score_away !== previous.state.score_away ||
             state.minute !== previous.state.minute)) {
          previous.withheld = 'Cambio sin observación nueva';
          return false;
        }
      }
      var budget = state.is_live ? Math.max(0, stamp(state.live_valid_until_madrid) - serverNow) : 0;
      var withheld = '';
      var change = previous ? previous.change : '';
      if (previous && observed > previous.observed && score(state.score_home) && score(state.score_away) &&
          (state.score_home !== previous.state.score_home || state.score_away !== previous.state.score_away)) {
        change = state.score_home + ' - ' + state.score_away;
      }
      if (previous && observed === previous.observed && state.is_live) {
        budget = Math.min(budget, Math.max(0, remaining(previous)));
        withheld = previous.withheld;
      }
      records.set(id, {state: state, evaluated: evaluated, observed: observed, budget: budget,
        mono: performance.now(), wall: Date.now(), withheld: withheld, change:change});
      return true;
    }
    function text(node, value) {
      if (typeof value === 'string' && window.NemesisI18n) value = window.NemesisI18n.text(value);
      if (node && node.textContent !== String(value)) node.textContent = String(value);
    }
    function notice(message, refresh) {
      var node = root.querySelector('[data-directo-notice]');
      if (node) { text(node, message); node.hidden = !message; }
      var link = root.querySelector('[data-directo-refresh-list]');
      if (link) link.hidden = !refresh;
    }
    function score(value) { return typeof value === 'number' && Number.isFinite(value) && value >= 0; }
    function draw(wrapper, entry) {
      var article = wrapper.querySelector('[data-v934-match-card]');
      if (!article) return;
      var state = entry.state;
      var isLive = live(entry);
      var expired = state.is_live && !isLive && !entry.withheld;
      var status = entry.withheld ? 'INCOMPLETE' : expired ? 'STALE' : state.status_canonical;
      var label = entry.withheld || statuses[status];
      var periodLabels = status === 'LIVE' && isLive ? ['Prórroga', 'Penaltis'] :
        status === 'FINISHED' && state.is_finished ? ['Final tras prórroga', 'Final tras penaltis'] : [];
      if (!entry.withheld && periodLabels.includes(state.period_label)) label = state.period_label;
      article.setAttribute('data-canonical-live', String(isLive));
      article.setAttribute('data-canonical-status', status);
      article.classList.toggle('is-stale', status === 'STALE' || Boolean(entry.withheld));
      text(article.querySelector('[data-v934-status] .v933-status-chip'), label);
      var chip = article.querySelector('[data-v934-status] .v933-status-chip');
      if (chip) {
        chip.classList.remove('is-success', 'is-blue', 'is-warning', 'is-neutral');
        chip.classList.add(isLive ? 'is-success' : status === 'STALE' || entry.withheld ? 'is-warning' : 'is-blue');
      }
      var hasScore = score(state.score_home) && score(state.score_away);
      var scoreNode = article.querySelector('[data-v934-score]');
      var showClock = status === 'UPCOMING' && Boolean(article.querySelector('[data-match-kickoff-clock]'));
      if (scoreNode) scoreNode.hidden = showClock;
      article.querySelectorAll('[data-match-kickoff-clock],[data-match-kickoff-zone]').forEach(function (node) { node.hidden = !showClock; });
      text(scoreNode, hasScore && status !== 'UPCOMING'
        ? state.score_home + ' - ' + state.score_away : status === 'UPCOMING' ? 'VS' : 'Resultado pendiente');
      var minute = article.querySelector('[data-v934-minute]');
      var hasMinute = isLive && typeof state.minute === 'string' && /^\d{1,3}(?:\+\d{1,2})?$/.test(state.minute);
      if (minute) { minute.hidden = !hasMinute; text(minute, hasMinute ? 'Min ' + state.minute : ''); }
      var meta = wrapper.querySelector('[data-realtime-freshness]');
      if (meta) {
        meta.setAttribute('data-realtime-freshness', expired ? 'STALE' : entry.withheld ? 'NOT_ESTABLISHED' : state.freshness_state);
        // Keep the time node, but never retain an old 'updated/current' label.
        var labelNode = meta.firstChild;
        if (labelNode && labelNode.nodeType === Node.TEXT_NODE) {
          var observationLabel = isLive ? 'Observación vigente' : expired ? 'Datos retrasados · Última lectura' :
            entry.withheld ? 'Información sin confirmar · Última lectura' : 'Observación registrada';
          labelNode.textContent = (window.NemesisI18n ? window.NemesisI18n.text(observationLabel) : observationLabel) + ' · ';
        }
        var timeNode = meta.querySelector('time');
        if (timeNode) timeNode.hidden = !Number.isFinite(stamp(state.provider_observed_at));
        if (timeNode && !Number.isFinite(stamp(state.provider_observed_at))) timeNode.removeAttribute('datetime');
        if (timeNode && Number.isFinite(stamp(state.provider_observed_at))) {
          timeNode.dateTime = state.provider_observed_at;
          text(timeNode, new Intl.DateTimeFormat((window.NemesisI18n || {}).locale || 'es', {timeZone:'Europe/Madrid', day:'2-digit', month:'2-digit',
            hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false}).format(new Date(state.provider_observed_at)));
        }
      }
      // Do not keep a numeric confidence index computed for a previous render.
      article.querySelectorAll('.v937-confidence-badge').forEach(function (badge) {
        badge.removeAttribute('data-v937-confidence-score');
        var confidenceLabel = isLive ? 'Observación vigente' : label;
        badge.setAttribute('aria-label', window.NemesisI18n ? window.NemesisI18n.text(confidenceLabel) : confidenceLabel);
        var explanation = 'Estado de la observación. No mide probabilidad de ganar.';
        badge.title = window.NemesisI18n ? window.NemesisI18n.text(explanation) : explanation;
        text(badge.querySelector('span[aria-hidden]'), '—');
        text(badge.querySelector('small'), isLive ? 'Observación vigente' : label);
        badge.className = 'v937-confidence-badge is-compact is-' + (isLive ? 'blue' : 'warning');
      });
      article.querySelectorAll('.v935-provenance small').forEach(function (node) { text(node, label); });
      var lane = root.getAttribute('data-directo-lane');
      var outside = (lane === 'live' && !isLive) || (lane === 'break' && (!isLive || status !== 'HALFTIME')) ||
        (lane === 'finished' && !state.is_finished);
      wrapper.setAttribute('data-directo-filter-match', String(!outside));
      var detail = wrapper.querySelector('[data-directo-card-notice]');
      if (detail) {
        detail.hidden = !outside && !entry.change;
        var changeMessage = entry.change ? (window.NemesisI18n
          ? window.NemesisI18n.text('Marcador actualizado: {score}. No confirma un evento de gol.', {score:entry.change})
          : 'Marcador actualizado: ' + entry.change + '. No confirma un evento de gol.') : '';
        text(detail, outside ? 'Fuera del filtro actual. Se conserva la última lectura y el acceso al partido.' : changeMessage);
        detail.setAttribute('data-change-kind', entry.change ? 'SCORE_UPDATE' : '');
      }
      wrapper.setAttribute('data-realtime-observed-at', state.provider_observed_at || '');
      wrapper.setAttribute('data-realtime-evaluated-at', state.evaluated_at_madrid);
    }
    function tick() {
      window.clearTimeout(expiryTimer);
      var delay = Infinity;
      var liveCount = 0;
      var halftimeCount = 0;
      var degraded = records.size < wrappers.size;
      records.forEach(function (entry, id) {
        if (live(entry)) {
          liveCount += 1;
          if (entry.state.status_canonical === 'HALFTIME') halftimeCount += 1;
          delay = Math.min(delay, remaining(entry));
        } else if (entry.state.is_live) degraded = true;
        if (wrappers.has(id)) draw(wrappers.get(id), entry);
      });
      function count(selector, value) {
        var kpi = root.querySelector(selector);
        if (kpi) { text(kpi.querySelector('strong'), value); text(kpi.querySelector('small'), completeCount ? 'Ahora' : 'Pendiente de confirmar'); }
      }
      if (completeCount || degraded || hasResponse) {
        count('.v933-kpi[href="/live?f=live"]', completeCount ? liveCount : '—');
        count('.v933-kpi[href="/live?f=break"]', completeCount ? halftimeCount : '—');
        if (completeCount) root.setAttribute('data-sports-live-confirmed', String(liveCount));
        else root.removeAttribute('data-sports-live-confirmed');
      }
      root.setAttribute('data-directo-visible-live-count', String(Array.from(wrappers.keys()).filter(function (id) { return live(records.get(id)); }).length));
      root.setAttribute('data-directo-live-count-scope', 'snapshot');
      root.setAttribute('data-directo-live-count-state', completeCount ? 'OBSERVED' : 'NOT_ESTABLISHED');
      if (degraded) notice('Algunas lecturas ya no confirman un directo vigente. No se inventan minutos ni resultados.', true);
      if (!stopped && Number.isFinite(delay)) expiryTimer = window.setTimeout(tick, Math.max(1, Math.ceil(delay)));
    }
    root.querySelectorAll('[data-realtime-consumer="directo-v1"]').forEach(function (wrapper) {
      var article = wrapper.querySelector('[data-v934-match-id]');
      if (!article) return;
      var id = article.getAttribute('data-v934-match-id');
      wrappers.set(id, wrapper);
      try {
        var state = JSON.parse(wrapper.getAttribute('data-realtime-state'));
        accept(id, state, Date.now());
      } catch (_) { /* Unknown input is not a LIVE claim to renew. */ }
      if (!records.has(id)) {
        article.setAttribute('data-canonical-live', 'false');
        article.setAttribute('data-canonical-status', 'INCOMPLETE');
        var chip = article.querySelector('[data-v934-status] .v933-status-chip');
        text(chip, 'Estado pendiente');
        if (chip) chip.className = 'v933-status-chip is-warning';
        var minuteNode = article.querySelector('[data-v934-minute]');
        if (minuteNode) { text(minuteNode, ''); minuteNode.hidden = true; }
      }
    });
    var initialLive = Array.from(records.values()).filter(function (entry) { return entry.state.is_live; }).length;
    completeCount = initialLive === Number(root.getAttribute('data-sports-live-confirmed')) && records.size === wrappers.size;
    tick();
    return {
      apply: function (envelope) {
        var payload = envelope.payload;
        if (payload.scope !== 'matches' || !Array.isArray(payload.matches)) throw new Error('invalid_directo_scope');
        var frame = stamp(payload.generated_at_madrid);
        if (!Number.isFinite(frame) || frame < lastFrame) { tick(); return; }
        lastFrame = frame;
        hasResponse = true;
        var serverNow = Number.isFinite(envelope.serverTime)
          ? envelope.serverTime + Math.max(0, performance.now() - envelope.receivedMono) : Date.now();
        var seen = new Set();
        var safe = true;
        var newItems = false;
        var declaredLive = 0;
        payload.matches.forEach(function (row) {
          if (!row || typeof row.id !== 'string' || !row.id || seen.has(row.id)) { safe = false; return; }
          seen.add(row.id);
          if (valid(row.realtime_state) && row.realtime_state.is_live) declaredLive += 1;
          if (!accept(row.id, row.realtime_state, serverNow)) safe = false;
          if (!wrappers.has(row.id)) newItems = true;
        });
        // Omitted records do not become finished or 0-0. Keep the focused DOM
        // and its actions, but withdraw any claim that they are still LIVE.
        records.forEach(function (entry, id) {
          if (!seen.has(id)) {
            if (wrappers.has(id)) entry.withheld = 'Fuera de la última lectura confirmada';
            else records.delete(id);
          }
        });
        if (safe && payload.counts) {
          [['finished', 'finished_verified'], ['with_pick', 'matches_with_picks']].forEach(function (pair) {
            var key = pair[0] === 'finished' ? 'finished' : 'matches_with_picks';
            var value = payload.counts[key];
            if (!Number.isInteger(value) || value < 0) return;
            var kpi = root.querySelector('.v933-kpi[href="/live?f=' + pair[0] + '"] strong');
            text(kpi, value);
            root.setAttribute('data-sports-' + pair[1].replace(/_/g, '-'), String(value));
          });
        }
        completeCount = safe && payload.counts && Number.isInteger(payload.counts.live) && declaredLive === payload.counts.live;
        notice(newItems ? 'Hay partidos fuera de esta vista. Actualiza la lista para aplicar tus filtros al nuevo conjunto.' : '', newItems);
        tick();
      },
      check: tick,
      failed: function () { notice('Actualización no disponible. Las lecturas conservan su vencimiento original.', false); tick(); },
      stop: function () { stopped = true; window.clearTimeout(expiryTimer); },
      resume: function () { stopped = false; tick(); }
    };
  }

  function updatePick(pick) {
    if (!pick || !pick.id) return;
    document.querySelectorAll('[data-v934-pick-id="' + CSS.escape(String(pick.id)) + '"]').forEach(function (card) {
      setText(card, '[data-v934-odds]', pick.odds);
      var freshness = card.querySelector('[data-v934-odds-freshness]');
      if (freshness && pick.odds_freshness) {
        freshness.textContent = text(pick.odds_freshness.label || 'Última registrada');
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
    var technical = bar.getAttribute('data-v934-technical') === 'true';
    var message = technical
      ? 'DB/caché: ' + (payload.cache_state || payload.cache_status || 'estado seguro') + '. Render sin llamada directa al proveedor.'
      : text(payload.safe_message || 'La información confirmada sigue disponible entre actualizaciones.');
    setText(bar, '[data-v934-realtime-title]', text(hasLive ? 'Actualización en directo' : hasData ? 'Datos deportivos sincronizados' : 'Esperando datos reales'));
    setText(bar, '[data-v934-realtime-message]', message);
    setText(bar, '[data-v934-cache-state]', technical ? (payload.cache_state || payload.cache_status || 'cache seguro') : text('Actualización segura'));
    updateSyncTimestamp(bar, payload, technical);
    setText(bar, '[data-v934-next-refresh]', text('Próxima revisión en {seconds} s', {seconds:clampPoll(payload.poll_after_seconds)}));
    bar.classList.toggle('is-live', hasLive);
    bar.classList.toggle('is-stale', payload.realtime_live_status === 'stale');
    bar.classList.remove('is-error');
    (payload.matches || []).forEach(updateMatch);
    (payload.live || []).forEach(updateMatch);
    (payload.picks || []).forEach(updatePick);
  }

  function start(bar) {
    if (bar.dataset.v934Started) return;
    bar.dataset.v934Started = 'true';
    var directo = bar.getAttribute('data-v934-directo') === 'inplace-v1' ? createDirectoController(bar) : null;
    var stopped = false;
    var failures = 0;
    var timer = null;
    var endpoint = bar.getAttribute('data-v934-endpoint') || '/api/realtime/sports';
    var scope = bar.getAttribute('data-v934-realtime') || 'all';

    function schedule(seconds) {
      window.clearTimeout(timer);
      if (!stopped) timer = window.setTimeout(load, (directo ? Math.max(45, clampPoll(seconds)) : jitteredPoll(seconds)) * 1000);
    }

    function load() {
      if (stopped) return;
      if (directo) directo.check();
      if (document.hidden) {
        schedule(180);
        return;
      }
      sharedLoad(endpoint, scope)
        .then(function (envelope) {
          if (stopped) return;
          var payload = envelope.payload;
          if (directo) directo.apply(envelope); else render(bar, payload);
          failures = 0;
          schedule(payload.poll_after_seconds);
        })
        .catch(function () {
          if (stopped) return;
          if (directo) directo.failed();
          failures += 1;
          bar.classList.add('is-error');
          setText(bar, '[data-v934-realtime-message]', text('Actualización temporalmente no disponible. Se conserva la última lectura segura.'));
          schedule(Math.min(300, 30 * Math.pow(2, Math.min(failures, 3))));
        });
    }

    schedule(Math.min(45, clampPoll(bar.getAttribute('data-v934-poll'))));
    bar.addEventListener('v934:refresh', function () { schedule(1); });
    document.addEventListener('visibilitychange', function () {
      if (directo) directo.check();
      if (!document.hidden) schedule(1);
    });
    window.addEventListener('pagehide', function () {
      stopped = true; window.clearTimeout(timer); if (directo) directo.stop();
    });
    window.addEventListener('pageshow', function (event) {
      if (event.persisted) { stopped = false; if (directo) directo.resume(); schedule(1); }
    });
    window.addEventListener('online', function () { if (directo) directo.check(); schedule(1); });
    window.addEventListener('offline', function () { if (directo) directo.failed(); });
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
