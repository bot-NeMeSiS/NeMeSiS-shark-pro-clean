(function v934RealtimeSports() {
  'use strict';

  var bars = Array.prototype.slice.call(document.querySelectorAll('[data-v934-realtime]'));
  var adminButtons = Array.prototype.slice.call(document.querySelectorAll('[data-v934-admin-action]'));
  if (!bars.length && !adminButtons.length) return;
  var shared = window.__nemesisV935Realtime || (window.__nemesisV935Realtime = { entries: {} });
  function text(source, values) {
    return window.NemesisI18n ? window.NemesisI18n.text(source, values) : source;
  }

  function clientMessage(value) {
    var message = String(value || '');
    return text(!message || /runtime|cron|storage|provider|cache|caché|backfill|sentinel|\b(?:partial|pass|fail)\b|pipeline|sports truth|db_path/i.test(message)
      ? 'La información confirmada sigue disponible entre actualizaciones.' : message);
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
    var lastTrustedServerNow = Date.now();
    var lastTrustedServerMono = performance.now();
    var lastTrustedClientWall = Date.now();
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
    function belongsToLane(entry, id) {
      var lane = root.getAttribute('data-directo-lane');
      if (!entry || entry.withheld) return false;
      if (lane === 'finished') return entry.state.is_finished && !entry.state.status_conflict;
      if (!live(entry)) return false;
      if (lane === 'break') return entry.state.status_canonical === 'HALFTIME';
      // Membership in the pick-filtered set is only known for server-rendered
      // cards. The public matches snapshot must not invent a published pick.
      if (lane === 'with_pick') return wrappers.has(id);
      return lane === 'live';
    }
    function kpis(key) {
      var paths = {
        live: ['/directo?f=live', '/live?f=live'],
        break: ['/directo?f=break', '/live?f=break'],
        finished: ['/calendario?lane=results', '/calendario?lane=finished', '/live?f=finished'],
        with_pick: ['/directo?f=with_pick', '/live?f=with_pick']
      };
      return root.querySelectorAll(paths[key].map(function (path) {
        return '.v933-kpi[href="' + path + '"]';
      }).join(','));
    }
    function delayedNotice() {
      return root.getAttribute('data-directo-lane') !== 'finished' &&
        root.getAttribute('data-directo-delayed') === 'true';
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
    function setNodeText(node, value) {
      if (typeof value === 'string' && window.NemesisI18n) value = window.NemesisI18n.text(value);
      if (node && node.textContent !== String(value)) node.textContent = String(value);
    }
    function notice(message, refresh) {
      var node = root.querySelector('[data-directo-notice]');
      if (node) { setNodeText(node, message); node.hidden = !message; }
      var link = root.querySelector('[data-directo-refresh-list]');
      if (link) link.hidden = !refresh;
    }
    function score(value) { return typeof value === 'number' && Number.isFinite(value) && value >= 0; }
    function validStatClock(raw, serverNow) {
      var value = stamp(raw);
      return Number.isFinite(value) && value <= serverNow ? value : NaN;
    }
    function estimatedServerNow() {
      var elapsed = Math.max(0, performance.now() - lastTrustedServerMono, Date.now() - lastTrustedClientWall);
      return lastTrustedServerNow + elapsed;
    }
    function safeStatValue(value) {
      if (typeof value === 'number') return Number.isFinite(value) && value >= 0 ? String(value) : null;
      if (typeof value !== 'string') return null;
      var normalized = value.trim();
      if (!/^(?:\d+(?:\.\d*)?|\.\d+)%?$/.test(normalized)) return null;
      var numeric = Number(normalized.replace(/%$/, ''));
      return Number.isFinite(numeric) && numeric >= 0 ? normalized : null;
    }
    function statTimeLabel(raw) {
      var value = stamp(raw);
      if (!Number.isFinite(value)) return '';
      try {
        return new Intl.DateTimeFormat((window.NemesisI18n || {}).locale || 'es', {
          timeZone: 'Europe/Madrid', day: '2-digit', month: '2-digit',
          hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
        }).format(new Date(value));
      } catch (_) { return ''; }
    }
    function findStatNode(section, key) {
      return Array.prototype.find.call(section.querySelectorAll('[data-stat-key]'), function (node) {
        return node.getAttribute('data-stat-key') === key;
      }) || null;
    }
    function ensureStatSection(wrapper) {
      var section = wrapper.querySelector('[data-live-statistics]');
      if (section) return section;
      section = document.createElement('section');
      section.className = 'v934-live-stats';
      section.setAttribute('data-live-statistics', '');
      section.setAttribute('data-stat-source', 'API-Football');
      section.setAttribute('data-stat-updated-at', '');
      section.setAttribute('aria-label', text('Estadísticas reales disponibles'));
      var ribbon = document.createElement('div');
      ribbon.className = 'v934-live-stats__ribbon';
      ribbon.setAttribute('aria-label', text('Resumen de estadísticas del proveedor'));
      section.appendChild(ribbon);
      var source = document.createElement('small');
      source.className = 'v934-live-stats__source';
      source.appendChild(document.createTextNode('API-Football · ' + text('Último dato recibido por NeMeSiS') + ': '));
      var latest = document.createElement('time');
      latest.setAttribute('data-live-stats-latest', '');
      source.appendChild(latest);
      section.appendChild(source);
      var article = wrapper.querySelector('[data-v934-match-card]') || wrapper.firstElementChild;
      if (article && article.parentNode) article.parentNode.insertBefore(section, article.nextSibling);
      else wrapper.appendChild(section);
      return section;
    }
    function matchTeamNames(wrapper) {
      var teams = wrapper.querySelector('.v933-match-teams');
      var columns = teams ? teams.querySelectorAll(':scope > div') : [];
      function nameAt(index, fallback) {
        var node = columns[index] && columns[index].querySelector('strong');
        var value = node ? node.textContent.trim() : '';
        return value || text(fallback);
      }
      return {home: nameAt(0, 'Local'), away: nameAt(columns.length - 1, 'Visitante')};
    }
    function captureAriaLabel(side, teamNames, delayed) {
      var prefix = text(side === 'home' ? 'Hora de recepción del equipo local' : 'Hora de recepción del equipo visitante');
      var name = teamNames && teamNames[side] ? teamNames[side] : text(side === 'home' ? 'Local' : 'Visitante');
      return prefix + ': ' + name + (delayed ? ' · ' + text('Datos retrasados') : '');
    }
    function ensureCapture(parent, side, teamNames) {
      var selector = side === 'home' ? '[data-stat-home-capture]' : '[data-stat-away-capture]';
      var capture = parent.querySelector(selector);
      if (!capture) {
        capture = document.createElement('small');
        capture.className = 'v934-live-stats__captured';
        capture.setAttribute(side === 'home' ? 'data-stat-home-capture' : 'data-stat-away-capture', '');
        capture.setAttribute('data-stat-side-label', side === 'home' ? 'L' : 'V');
        parent.appendChild(capture);
      }
      var timeSelector = side === 'home' ? '[data-stat-home-time]' : '[data-stat-away-time]';
      var timeNode = capture.querySelector(timeSelector);
      if (!timeNode) {
        timeNode = document.createElement('time');
        timeNode.setAttribute(side === 'home' ? 'data-stat-home-time' : 'data-stat-away-time', '');
        capture.insertBefore(timeNode, capture.querySelector('[data-stat-age]'));
      }
      var age = capture.querySelector('[data-stat-age]');
      if (!age) {
        age = document.createElement('span');
        age.setAttribute('data-stat-age', '');
        age.hidden = true;
        capture.appendChild(age);
      }
      capture.setAttribute('aria-label', captureAriaLabel(side, teamNames, capture.classList.contains('is-delayed')));
      return capture;
    }
    function updateStatTeamNames(section, teamNames) {
      section.querySelectorAll('[data-stat-home-capture]').forEach(function (capture) {
        capture.setAttribute('aria-label', captureAriaLabel('home', teamNames, capture.classList.contains('is-delayed')));
      });
      section.querySelectorAll('[data-stat-away-capture]').forEach(function (capture) {
        capture.setAttribute('aria-label', captureAriaLabel('away', teamNames, capture.classList.contains('is-delayed')));
      });
      var headers = section.querySelectorAll('.v934-live-stats__all-header [role="columnheader"]');
      if (headers.length >= 3) {
        setNodeText(headers[0], teamNames.home);
        setNodeText(headers[2], teamNames.away);
      }
    }
    function refreshStatFreshness(section, serverNow) {
      section.querySelectorAll('[data-stat-home-capture],[data-stat-away-capture]').forEach(function (capture) {
        var home = capture.hasAttribute('data-stat-home-capture');
        var timeNode = capture.querySelector(home ? '[data-stat-home-time]' : '[data-stat-away-time]');
        var capturedAt = stamp(timeNode && timeNode.getAttribute('datetime'));
        if (!Number.isFinite(capturedAt) || !Number.isFinite(serverNow)) return;
        var delayed = serverNow - capturedAt > 10 * 60 * 1000;
        capture.classList.toggle('is-delayed', delayed);
        capture.setAttribute('data-stat-freshness', delayed ? 'DELAYED' : 'CURRENT');
        var age = capture.querySelector('[data-stat-age]');
        if (!age) {
          age = document.createElement('span');
          age.setAttribute('data-stat-age', '');
          capture.appendChild(age);
        }
        age.hidden = !delayed;
        setNodeText(age, delayed ? 'Datos retrasados' : '');
        var side = home ? 'home' : 'away';
        capture.setAttribute('aria-label', captureAriaLabel(side, matchTeamNames(section.closest('[data-realtime-consumer="directo-v1"]') || section), delayed));
      });
    }
    function ensureDisclosure(section, teamNames) {
      var details = section.querySelector('[data-live-statistics-more]');
      if (details) {
        var currentHeaders = details.querySelectorAll('.v934-live-stats__all-header [role="columnheader"]');
        if (currentHeaders.length >= 3) {
          setNodeText(currentHeaders[0], teamNames.home);
          setNodeText(currentHeaders[2], teamNames.away);
        }
        return details;
      }
      details = document.createElement('details');
      details.className = 'v934-live-stats__more';
      details.setAttribute('data-live-statistics-more', '');
      var summaryNode = document.createElement('summary');
      summaryNode.setAttribute('data-live-statistics-summary', '');
      details.appendChild(summaryNode);
      var table = document.createElement('div');
      table.className = 'v934-live-stats__all';
      table.setAttribute('role', 'table');
      table.setAttribute('aria-label', text('Todas las estadísticas disponibles del proveedor'));
      var header = document.createElement('div');
      header.className = 'v934-live-stats__all-header';
      header.setAttribute('role', 'row');
      [[teamNames.home, 'columnheader'], [text('Estadística'), 'columnheader'], [teamNames.away, 'columnheader']].forEach(function (item) {
        var cell = document.createElement(item[1] === 'columnheader' ? 'span' : 'span');
        cell.setAttribute('role', item[1]);
        setNodeText(cell, item[0]);
        header.appendChild(cell);
      });
      table.appendChild(header);
      details.appendChild(table);
      section.insertBefore(details, section.querySelector('.v934-live-stats__source'));
      return details;
    }
    function ensureStatNode(section, stat, teamNames) {
      var existing = findStatNode(section, stat.key);
      if (existing) return existing;
      var priority = ['shots_on_goal', 'fouls', 'corners', 'throw_ins'].includes(stat.key);
      if (priority) {
        var ribbon = section.querySelector('.v934-live-stats__ribbon');
        if (!ribbon) {
          ribbon = document.createElement('div');
          ribbon.className = 'v934-live-stats__ribbon';
          ribbon.setAttribute('aria-label', text('Resumen de estadísticas del proveedor'));
          section.insertBefore(ribbon, section.querySelector('[data-live-statistics-more]') || section.querySelector('.v934-live-stats__source'));
        }
        var item = document.createElement('span');
        item.setAttribute('data-stat-key', stat.key);
        item.setAttribute('data-stat-home', '');
        item.setAttribute('data-stat-away', '');
        var label = document.createElement('strong'); setNodeText(label, stat.label); item.appendChild(label);
        var values = document.createElement('b'); values.setAttribute('data-stat-values', ''); item.appendChild(values);
        ensureCapture(item, 'home', teamNames); ensureCapture(item, 'away', teamNames);
        ribbon.appendChild(item);
        return item;
      }
      var details = ensureDisclosure(section, teamNames);
      var table = details.querySelector('.v934-live-stats__all');
      var row = document.createElement('div');
      row.className = 'v934-live-stats__all-row';
      row.setAttribute('role', 'row');
      row.setAttribute('data-stat-key', stat.key);
      function valueCell(side) {
        var cell = document.createElement('span'); cell.setAttribute('role', 'cell');
        var value = document.createElement('span'); value.setAttribute(side === 'home' ? 'data-stat-home-value' : 'data-stat-away-value', '');
        cell.appendChild(value); ensureCapture(cell, side, teamNames);
        return cell;
      }
      row.appendChild(valueCell('home'));
      var label = document.createElement('strong'); label.setAttribute('role', 'rowheader'); setNodeText(label, stat.label);
      row.appendChild(label);
      row.appendChild(valueCell('away'));
      table.appendChild(row);
      return row;
    }
    function statValueNode(node, side) {
      if (node.classList.contains('v934-live-stats__all-row')) {
        return node.querySelector(side === 'home' ? '[data-stat-home-value]' : '[data-stat-away-value]');
      }
      return node.querySelector('[data-stat-values]');
    }
    function existingStatValue(node, side) {
      if (node.classList.contains('v934-live-stats__all-row')) {
        var valueNode = statValueNode(node, side);
        return valueNode ? valueNode.textContent.trim() : '';
      }
      return node.getAttribute(side === 'home' ? 'data-stat-home' : 'data-stat-away') || '';
    }
    function applyStatSide(node, side, value, rawCapture, serverNow, teamNames) {
      var normalizedValue = safeStatValue(value);
      if (normalizedValue === null) return false;
      var incoming = validStatClock(rawCapture, serverNow);
      if (!Number.isFinite(incoming)) return false;
      var capture = ensureCapture(node.classList.contains('v934-live-stats__all-row')
        ? node.querySelector(side === 'home' ? '[role="cell"]:first-child' : '[role="cell"]:last-child') || node
        : node, side, teamNames);
      var timeNode = capture.querySelector('time');
      var previousRaw = timeNode && timeNode.getAttribute('datetime');
      var previous = stamp(previousRaw);
      var oldValue = existingStatValue(node, side);
      if (Number.isFinite(previous) && incoming < previous) return false;
      if (Number.isFinite(previous) && incoming === previous && oldValue !== normalizedValue) return false;
      if (!Number.isFinite(previous) || incoming > previous) {
        if (node.classList.contains('v934-live-stats__all-row')) {
          var valueNode = statValueNode(node, side);
          if (valueNode) setNodeText(valueNode, normalizedValue);
        } else {
          node.setAttribute(side === 'home' ? 'data-stat-home' : 'data-stat-away', normalizedValue);
          var homeValue = node.getAttribute('data-stat-home') || '—';
          var awayValue = node.getAttribute('data-stat-away') || '—';
          setNodeText(node.querySelector('[data-stat-values]'), homeValue + '–' + awayValue);
        }
        if (timeNode) {
          timeNode.setAttribute('datetime', rawCapture);
          setNodeText(timeNode, statTimeLabel(rawCapture));
          capture.hidden = false;
        }
        refreshStatFreshness(capture.closest('[data-live-statistics]') || capture.parentNode, serverNow);
        return true;
      }
      return oldValue === normalizedValue;
    }
    function parsePercent(value) {
      var parsed = Number(String(value == null ? '' : value).replace('%', '').trim());
      return Number.isFinite(parsed) && parsed >= 0 && parsed <= 100 ? parsed : NaN;
    }
    function updatePossession(section, card, serverNow, teamNames) {
      var chart = section.querySelector('[data-live-stat-possession]');
      if (!card) {
        // Preserve the last measured value. Its own timestamp below exposes age.
        return;
      }
      var homeAt = validStatClock(card.home_captured_at, serverNow);
      var awayAt = validStatClock(card.away_captured_at, serverNow);
      var homePct = parsePercent(card.home);
      var awayPct = parsePercent(card.away);
      var comparable = Number.isFinite(homeAt) && homeAt === awayAt && Number.isFinite(homePct) && Number.isFinite(awayPct);
      if (!comparable) {
        if (chart) chart.hidden = true;
        var row = ensureStatNode(section, card, teamNames);
        row.hidden = false;
        applyStatSide(row, 'home', card.home, card.home_captured_at, serverNow, teamNames);
        applyStatSide(row, 'away', card.away, card.away_captured_at, serverNow, teamNames);
        return;
      }
      var priorPossessionRow = findStatNode(section, 'possession');
      if (priorPossessionRow) {
        var priorHome = stamp(priorPossessionRow.querySelector('[data-stat-home-time]') && priorPossessionRow.querySelector('[data-stat-home-time]').getAttribute('datetime'));
        var priorAway = stamp(priorPossessionRow.querySelector('[data-stat-away-time]') && priorPossessionRow.querySelector('[data-stat-away-time]').getAttribute('datetime'));
        if ((Number.isFinite(priorHome) && homeAt < priorHome) || (Number.isFinite(priorAway) && awayAt < priorAway)) {
          var retainedChart = section.querySelector('[data-live-stat-possession]');
          if (retainedChart) retainedChart.hidden = true;
          priorPossessionRow.hidden = false;
          applyStatSide(priorPossessionRow, 'home', card.home, card.home_captured_at, serverNow, teamNames);
          applyStatSide(priorPossessionRow, 'away', card.away, card.away_captured_at, serverNow, teamNames);
          return;
        }
      }
      if (!chart) {
        chart = document.createElement('div');
        chart.className = 'v944-possession v944-possession--compact';
        chart.setAttribute('data-live-stat-possession', '');
        chart.setAttribute('data-visualization', 'aggregate-share');
        chart.setAttribute('data-spatial-map-available', 'false');
        var heading = document.createElement('div'); heading.className = 'v944-possession__heading';
        var title = document.createElement('strong'); setNodeText(title, 'Posesión del balón'); heading.appendChild(title);
        var provider = document.createElement('span'); setNodeText(provider, 'Porcentaje real del proveedor'); heading.appendChild(provider);
        chart.appendChild(heading);
        var pitch = document.createElement('div'); pitch.className = 'v944-possession__pitch'; pitch.setAttribute('role', 'img');
        var homeBar = document.createElement('span'); homeBar.className = 'v944-possession__share is-home'; homeBar.setAttribute('data-possession-home-bar', ''); pitch.appendChild(homeBar);
        var awayBar = document.createElement('span'); awayBar.className = 'v944-possession__share is-away'; awayBar.setAttribute('data-possession-away-bar', ''); pitch.appendChild(awayBar);
        var midline = document.createElement('span'); midline.className = 'v944-possession__midline'; midline.setAttribute('aria-hidden', 'true'); pitch.appendChild(midline);
        chart.appendChild(pitch);
        var teams = document.createElement('div'); teams.className = 'v944-possession__teams';
        [['home', teamNames.home], ['away', teamNames.away]].forEach(function (side) {
          var group = document.createElement('span'); var name = document.createElement('strong'); setNodeText(name, side[1]); group.appendChild(name);
          var pct = document.createElement('b'); pct.setAttribute(side[0] === 'home' ? 'data-possession-home-value' : 'data-possession-away-value', ''); group.appendChild(pct);
          teams.appendChild(group);
        });
        chart.appendChild(teams);
        var capturePair = document.createElement('div');
        capturePair.className = 'v934-live-stats__capture-pair';
        capturePair.setAttribute('data-possession-capture-pair', '');
        ensureCapture(capturePair, 'home', teamNames); ensureCapture(capturePair, 'away', teamNames);
        chart.appendChild(capturePair);
        var note = document.createElement('small'); note.className = 'v944-possession__note';
        setNodeText(note, 'Reparto total de posesión; no es un mapa de zonas ni la ubicación del balón.'); chart.appendChild(note);
        section.insertBefore(chart, section.querySelector('.v934-live-stats__ribbon') || section.firstChild);
      }
      var possessionRow = findStatNode(section, 'possession');
      if (possessionRow) possessionRow.hidden = true;
      var previousChartAt = stamp(chart.getAttribute('data-possession-captured-at'));
      if (Number.isFinite(previousChartAt)) {
        if (homeAt < previousChartAt) return;
        if (homeAt === previousChartAt) {
          var previousHome = parsePercent(chart.querySelector('[data-possession-home-value]') && chart.querySelector('[data-possession-home-value]').textContent);
          var previousAway = parsePercent(chart.querySelector('[data-possession-away-value]') && chart.querySelector('[data-possession-away-value]').textContent);
          if (previousHome !== homePct || previousAway !== awayPct) return;
        }
      }
      chart.hidden = false;
      chart.setAttribute('data-possession-captured-at', card.home_captured_at);
      chart.querySelector('[data-possession-home-bar]').style.width = homePct + '%';
      chart.querySelector('[data-possession-away-bar]').style.width = awayPct + '%';
      setNodeText(chart.querySelector('[data-possession-home-value]'), homePct + '%');
      setNodeText(chart.querySelector('[data-possession-away-value]'), awayPct + '%');
      var capturePairNode = chart.querySelector('[data-possession-capture-pair]');
      if (!capturePairNode) {
        capturePairNode = document.createElement('div');
        capturePairNode.className = 'v934-live-stats__capture-pair';
        capturePairNode.setAttribute('data-possession-capture-pair', '');
        chart.appendChild(capturePairNode);
      }
      [['home', card.home_captured_at], ['away', card.away_captured_at]].forEach(function (item) {
        if (!Number.isFinite(validStatClock(item[1], serverNow))) return;
        var capture = ensureCapture(capturePairNode, item[0], teamNames);
        var timeNode = capture.querySelector('time');
        if (timeNode) {
          timeNode.setAttribute('datetime', item[1]);
          setNodeText(timeNode, statTimeLabel(item[1]));
          capture.hidden = false;
        }
      });
      var pitchNode = chart.querySelector('.v944-possession__pitch');
      if (pitchNode) pitchNode.setAttribute('aria-label', text('Reparto porcentual de posesión: {homeTeam} {home}%, {awayTeam} {away}%.', {homeTeam:teamNames.home, home:homePct, awayTeam:teamNames.away, away:awayPct}));
    }
    function ensureActivitySection(section, teamNames) {
      var activity = section.querySelector('[data-live-stat-activity]');
      if (activity) return activity;
      activity = document.createElement('section');
      activity.className = 'v934-live-activity';
      activity.setAttribute('data-live-stat-activity', '');
      activity.setAttribute('data-activity-index', 'weighted-provider-statistics');
      activity.setAttribute('data-provider-metric', 'false');
      activity.setAttribute('data-spatial-map-available', 'false');
      activity.setAttribute('aria-label', text('Índice estadístico orientativo de actividad'));
      var heading = document.createElement('div'); heading.className = 'v934-live-activity__heading';
      var title = document.createElement('strong'); setNodeText(title, 'Actividad estadística orientativa'); heading.appendChild(title);
      var subtitle = document.createElement('span'); setNodeText(subtitle, 'Estimación NeMeSiS · no es un dato del proveedor'); heading.appendChild(subtitle);
      activity.appendChild(heading);
      var bar = document.createElement('div'); bar.className = 'v934-live-activity__bar'; bar.setAttribute('role', 'img');
      var homeBar = document.createElement('span'); homeBar.className = 'is-home'; homeBar.setAttribute('data-activity-home-bar', ''); bar.appendChild(homeBar);
      var awayBar = document.createElement('span'); awayBar.className = 'is-away'; awayBar.setAttribute('data-activity-away-bar', ''); bar.appendChild(awayBar);
      activity.appendChild(bar);
      var teams = document.createElement('div'); teams.className = 'v934-live-activity__teams';
      [['home', teamNames.home], ['away', teamNames.away]].forEach(function (side) {
        var group = document.createElement('span');
        group.appendChild(document.createTextNode(side[1] + ' '));
        var value = document.createElement('b'); value.setAttribute(side[0] === 'home' ? 'data-activity-home-value' : 'data-activity-away-value', ''); group.appendChild(value);
        teams.appendChild(group);
      });
      activity.appendChild(teams);
      var note = document.createElement('small');
      setNodeText(note, 'Cálculo orientativo basado en las estadísticas disponibles. No representa posesión oficial, ubicación del balón ni zonas del campo.');
      activity.appendChild(note);
      section.insertBefore(activity, section.querySelector('.v934-live-stats__ribbon') || section.querySelector('[data-live-statistics-more]') || section.querySelector('.v934-live-stats__source'));
      return activity;
    }
    function updateActivity(section, field, updatedAt, teamNames) {
      var activity = section.querySelector('[data-live-stat-activity]');
      var home = field.home_activity_index_pct;
      var away = field.away_activity_index_pct;
      var available = field.activity_index_available === true && Number.isFinite(home) && Number.isFinite(away) &&
        home >= 0 && home <= 100 && away >= 0 && away <= 100;
      if (!available) {
        if (activity) activity.hidden = true;
        return;
      }
      activity = activity || ensureActivitySection(section, teamNames);
      activity.hidden = false;
      var homeActivity = Math.max(0, Math.min(100, home));
      var awayActivity = Math.max(0, Math.min(100, away));
      setNodeText(activity.querySelector('[data-activity-home-value]'), homeActivity + '%');
      setNodeText(activity.querySelector('[data-activity-away-value]'), awayActivity + '%');
      var homeBar = activity.querySelector('[data-activity-home-bar]');
      var awayBar = activity.querySelector('[data-activity-away-bar]');
      if (homeBar) homeBar.style.width = homeActivity + '%';
      if (awayBar) awayBar.style.width = awayActivity + '%';
      var groups = activity.querySelectorAll('.v934-live-activity__teams > span');
      if (groups.length >= 2) {
        groups[0].firstChild.textContent = teamNames.home + ' ';
        groups[1].firstChild.textContent = teamNames.away + ' ';
      }
      var image = activity.querySelector('[role="img"]');
      if (image) image.setAttribute('aria-label', text('Índice estadístico orientativo: {homeTeam} {home}%, {awayTeam} {away}%.', {homeTeam:teamNames.home, home:homeActivity, awayTeam:teamNames.away, away:awayActivity}));
      activity.setAttribute('data-activity-updated-at', updatedAt);
    }
    function updateLiveStatistics(wrapper, state, rawStats, serverNow) {
      if (!rawStats || rawStats.available !== true || rawStats.external_calls !== 0 ||
          typeof rawStats.fixture_id !== 'string' || rawStats.fixture_id !== state.fixture_id ||
          typeof state.provider !== 'string' || !/api.*football|football.*api/i.test(state.provider)) return;
      var globalAt = validStatClock(rawStats.statistics_updated_at, serverNow);
      if (!Number.isFinite(globalAt) || !Array.isArray(rawStats.stat_cards)) return;
      var cards = rawStats.stat_cards.slice(0, 40).filter(function (card) {
        return card && typeof card.key === 'string' && /^[a-zA-Z0-9_-]{1,80}$/.test(card.key);
      }).map(function (card) {
        var home = safeStatValue(card.home);
        var away = safeStatValue(card.away);
        var homeAt = home !== null && Number.isFinite(validStatClock(card.home_captured_at, serverNow)) ? card.home_captured_at : '';
        var awayAt = away !== null && Number.isFinite(validStatClock(card.away_captured_at, serverNow)) ? card.away_captured_at : '';
        return {key:card.key, label:typeof card.label === 'string' ? card.label.slice(0, 100) : card.key,
          home:home, away:away, home_captured_at:homeAt, away_captured_at:awayAt};
      }).filter(function (card) { return card.home_captured_at || card.away_captured_at; });
      if (!cards.length) return;
      var section = ensureStatSection(wrapper);
      var teamNames = matchTeamNames(wrapper);
      updateStatTeamNames(section, teamNames);
      var oldGlobal = stamp(section.getAttribute('data-stat-updated-at'));
      if (Number.isFinite(oldGlobal) && globalAt < oldGlobal) return;
      cards.forEach(function (card) {
        var homeValue = card.home;
        var awayValue = card.away;
        var homeClock = homeValue !== null ? validStatClock(card.home_captured_at, serverNow) : NaN;
        var awayClock = awayValue !== null ? validStatClock(card.away_captured_at, serverNow) : NaN;
        if (!Number.isFinite(homeClock) && !Number.isFinite(awayClock)) return;
        var stat = {
          key: card.key,
          label: typeof card.label === 'string' ? card.label.slice(0, 100) : card.key,
          home: homeValue,
          away: awayValue,
          home_captured_at: Number.isFinite(homeClock) ? card.home_captured_at : '',
          away_captured_at: Number.isFinite(awayClock) ? card.away_captured_at : ''
        };
        var row = findStatNode(section, stat.key);
        var isPossessionChart = stat.key === 'possession' &&
          Number.isFinite(homeClock) && homeClock === awayClock &&
          Number.isFinite(parsePercent(card.home)) && Number.isFinite(parsePercent(card.away));
        if (stat.key !== 'possession' || !isPossessionChart) {
          row = row || ensureStatNode(section, stat, teamNames);
          row.hidden = false;
          var homeApplied = applyStatSide(row, 'home', stat.home, stat.home_captured_at, serverNow, teamNames);
          var awayApplied = applyStatSide(row, 'away', stat.away, stat.away_captured_at, serverNow, teamNames);
          if (!homeApplied && !awayApplied) return;
          if (row.classList.contains('v934-live-stats__all-row')) {
            var labelNode = row.querySelector('[role="rowheader"]');
          if (labelNode) setNodeText(labelNode, stat.label);
          } else {
            var ribbonLabel = row.querySelector('strong');
          if (ribbonLabel) setNodeText(ribbonLabel, stat.label);
          }
        }
      });
      var possession = cards.find(function (card) { return card.key === 'possession'; });
      if (possession) updatePossession(section, possession, serverNow, teamNames);
      updateActivity(section, rawStats.field_state || {}, rawStats.statistics_updated_at, teamNames);
      updateStatTeamNames(section, teamNames);
      section.setAttribute('data-stat-updated-at', rawStats.statistics_updated_at);
      var latest = section.querySelector('[data-live-stats-latest]');
      if (latest && (!Number.isFinite(oldGlobal) || globalAt > oldGlobal)) {
        latest.setAttribute('datetime', rawStats.statistics_updated_at);
        setNodeText(latest, statTimeLabel(rawStats.statistics_updated_at));
      }
      var details = section.querySelector('[data-live-statistics-more]');
      if (details) {
        var count = details.querySelectorAll('.v934-live-stats__all-row:not([hidden])').length;
        var summaryNode = details.querySelector('summary');
        if (summaryNode) setNodeText(summaryNode, text('Ver todas las estadísticas disponibles') + ' · ' + count);
        details.hidden = count === 0;
      }
      refreshStatFreshness(section, serverNow);
    }
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
      setNodeText(article.querySelector('[data-v934-status] .v933-status-chip'), label);
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
      setNodeText(scoreNode, hasScore && status !== 'UPCOMING'
        ? state.score_home + ' - ' + state.score_away : status === 'UPCOMING' ? 'VS' : 'Resultado pendiente');
      var minute = article.querySelector('[data-v934-minute]');
      var hasMinute = isLive && typeof state.minute === 'string' && /^\d{1,3}(?:\+\d{1,2})?$/.test(state.minute);
      if (minute) { minute.hidden = !hasMinute; setNodeText(minute, hasMinute ? 'Min ' + state.minute : ''); }
      var meta = wrapper.querySelector('[data-realtime-freshness]');
      if (meta) {
        meta.setAttribute('data-realtime-freshness', expired ? 'STALE' : entry.withheld ? 'NOT_ESTABLISHED' : state.freshness_state);
        // Keep the observation time visible while updating only its state label.
        var labelNode = meta.querySelector('[data-realtime-freshness-label]');
        if (labelNode) {
          var observationLabel = isLive ? 'Observación vigente' : expired ? 'Datos retrasados · Última lectura' :
            entry.withheld ? 'Información sin confirmar · Última lectura' : 'Observación registrada';
          setNodeText(labelNode, window.NemesisI18n ? window.NemesisI18n.text(observationLabel) : observationLabel);
        }
        var timeNode = meta.querySelector('time');
        if (timeNode) timeNode.hidden = !Number.isFinite(stamp(state.provider_observed_at));
        if (timeNode && !Number.isFinite(stamp(state.provider_observed_at))) timeNode.removeAttribute('datetime');
        if (timeNode && Number.isFinite(stamp(state.provider_observed_at))) {
          timeNode.dateTime = state.provider_observed_at;
          setNodeText(timeNode, new Intl.DateTimeFormat((window.NemesisI18n || {}).locale || 'es', {timeZone:'Europe/Madrid', day:'2-digit', month:'2-digit',
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
        setNodeText(badge.querySelector('span[aria-hidden]'), '—');
        setNodeText(badge.querySelector('small'), isLive ? 'Observación vigente' : label);
        badge.className = 'v937-confidence-badge is-compact is-' + (isLive ? 'blue' : 'warning');
      });
      article.querySelectorAll('.v935-provenance small').forEach(function (node) { setNodeText(node, label); });
      var lane = root.getAttribute('data-directo-lane');
      var outside = (['live', 'with_pick'].includes(lane) && !isLive) || (lane === 'break' && (!isLive || status !== 'HALFTIME')) ||
        (lane === 'finished' && !state.is_finished);
      wrapper.setAttribute('data-directo-filter-match', String(!outside));
      var detail = wrapper.querySelector('[data-directo-card-notice]');
      if (detail) {
        detail.hidden = !outside && !entry.change;
        var changeMessage = entry.change ? (window.NemesisI18n
          ? window.NemesisI18n.text('Marcador actualizado: {score}. No confirma un evento de gol.', {score:entry.change})
          : 'Marcador actualizado: ' + entry.change + '. No confirma un evento de gol.') : '';
        setNodeText(detail, outside ? 'Fuera del filtro actual. Se conserva la última lectura y el acceso al partido.' : changeMessage);
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
      var statsNow = estimatedServerNow();
      wrappers.forEach(function (wrapper) {
        var statsSection = wrapper.querySelector('[data-live-statistics]');
        if (statsSection) refreshStatFreshness(statsSection, statsNow);
      });
      function count(key, value) {
        kpis(key).forEach(function (kpi) {
          setNodeText(kpi.querySelector('strong'), value);
          setNodeText(kpi.querySelector('small'), completeCount ? 'Ahora' : 'Pendiente de confirmar');
        });
      }
      if (completeCount || degraded || hasResponse) {
        count('live', completeCount ? liveCount : '—');
        count('break', completeCount ? halftimeCount : '—');
        if (completeCount) root.setAttribute('data-sports-live-confirmed', String(liveCount));
        else root.removeAttribute('data-sports-live-confirmed');
      }
      root.setAttribute('data-directo-visible-live-count', String(Array.from(wrappers.keys()).filter(function (id) { return live(records.get(id)); }).length));
      root.setAttribute('data-directo-live-count-scope', 'snapshot');
      root.setAttribute('data-directo-live-count-state', completeCount ? 'OBSERVED' : 'NOT_ESTABLISHED');
      if (degraded) notice('Algunas lecturas ya no confirman un directo vigente. No se inventan minutos ni resultados.', true);
      else if (delayedNotice()) notice('Algunas lecturas ya no confirman un directo vigente. No se inventan minutos ni resultados.', false);
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
        setNodeText(chip, 'Estado pendiente');
        if (chip) chip.className = 'v933-status-chip is-warning';
        var minuteNode = article.querySelector('[data-v934-minute]');
        if (minuteNode) { setNodeText(minuteNode, ''); minuteNode.hidden = true; }
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
        lastTrustedServerNow = serverNow;
        lastTrustedServerMono = performance.now();
        lastTrustedClientWall = Date.now();
        var seen = new Set();
        var safe = true;
        var newItems = false;
        var declaredLive = 0;
        payload.matches.forEach(function (row) {
          if (!row || typeof row.id !== 'string' || !row.id || seen.has(row.id)) { safe = false; return; }
          seen.add(row.id);
          if (valid(row.realtime_state) && row.realtime_state.is_live) declaredLive += 1;
          var accepted = accept(row.id, row.realtime_state, serverNow);
          if (accepted && wrappers.has(row.id)) {
            updateLiveStatistics(wrappers.get(row.id), records.get(row.id).state, row.live_statistics, serverNow);
          }
          if (!accepted) safe = false;
          if (accepted && !wrappers.has(row.id) && belongsToLane(records.get(row.id), row.id)) newItems = true;
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
            kpis(pair[0]).forEach(function (kpi) { setNodeText(kpi.querySelector('strong'), value); });
            root.setAttribute('data-sports-' + pair[1].replace(/_/g, '-'), String(value));
          });
        }
        completeCount = safe && payload.counts && Number.isInteger(payload.counts.live) && declaredLive === payload.counts.live;
        root.setAttribute('data-directo-delayed', String(safe && payload.realtime_live_status === 'stale' &&
          payload.counts && payload.counts.live === 0 && Number.isInteger(payload.counts.stale_live) && payload.counts.stale_live > 0));
        newItems = Boolean(safe && newItems);
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
    var technical = location.pathname.indexOf('/admin/') === 0 && bar.getAttribute('data-v934-technical') === 'true';
    var message = technical
      ? 'DB/caché: ' + (payload.cache_state || payload.cache_status || 'estado seguro') + '. Render sin llamada directa al proveedor.'
      : clientMessage(payload.safe_message);
    setText(bar, '[data-v934-realtime-title]', text(hasLive ? 'Actualización en directo' : payload.realtime_live_status === 'stale' ? 'Datos retrasados' : hasData ? 'Datos deportivos sincronizados' : 'Esperando datos reales'));
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
