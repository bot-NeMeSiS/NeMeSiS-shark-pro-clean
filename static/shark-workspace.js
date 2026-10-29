/* A temporary same-document conversation; authentication/quotas stay on server. */
(function () {
  'use strict';
  if (document.documentElement.hasAttribute('data-ns-session-transitions')) return;
  document.documentElement.setAttribute('data-ns-session-transitions', 'ready');
  var invalidate = function () {};
  var channel;
  try {
    channel = new BroadcastChannel('nemesis-document-transitions');
    channel.addEventListener('message', function (event) {
      if (event.data === 'document-transition') invalidate();
    });
    // No identity, token, question or response is transmitted or persisted.
    channel.postMessage('document-transition');
  } catch (_) {
    // Older/restricted browsers clear on focus loss instead of retaining an
    // unverifiable conversation while another tab changes the account.
    window.addEventListener('blur', function () { invalidate(); });
  }
  window.addEventListener('pagehide', function () { invalidate(); });
  window.addEventListener('pageshow', function (event) { if (event.persisted) invalidate(); });

  var root = document.querySelector('[data-ns-assistant]');
  if (!root) return; // Admin/full-page SHARK still broadcasts transitions only.
  var dialog = root.querySelector('dialog');
  var launcher = root.querySelector('[data-ns-assistant-open]');
  if (!dialog || typeof dialog.showModal !== 'function') return; // Useful GET fallback.
  var messages = root.querySelector('[data-assistant-messages]');
  var status = root.querySelector('[data-assistant-status]');
  var usage = root.querySelector('[data-assistant-usage]');
  var form = root.querySelector('form');
  var input = form && form.querySelector('[name="q"]');
  var submit = form && form.querySelector('[type="submit"]');
  var login = root.querySelector('[data-assistant-login]');
  var upgrade = root.querySelector('[data-assistant-upgrade]');
  var expand = root.querySelector('[data-assistant-expand]');
  var copy;
  try { copy = JSON.parse(root.querySelector('[data-assistant-copy]').textContent); }
  catch (_) { return; }
  var pending = false, quotaBlocked = false, sessionInvalid = false;
  var generation = 0, controller = null, returnFocus = null;

  function controls() {
    if (submit) submit.disabled = pending || quotaBlocked || sessionInvalid;
    if (input) input.readOnly = pending;
    if (form) form.setAttribute('aria-busy', String(pending));
  }
  function close(hide) {
    if (dialog.open) dialog.close();
    launcher.hidden = Boolean(hide);
    launcher.setAttribute('aria-expanded', 'false');
    root.dataset.state = hide ? 'hidden' : 'closed';
    var target = returnFocus;
    if (!hide && (!target || !target.isConnected || !target.getClientRects().length)) target = launcher;
    if (target && target.isConnected && target.getClientRects().length) target.focus({preventScroll:true});
  }
  function open(from) {
    var explorer = document.getElementById('app-navigation-dialog');
    if (explorer && explorer.open) explorer.close();
    launcher.hidden = false;
    returnFocus = from || launcher;
    if (!dialog.open) dialog.showModal();
    document.body.classList.remove('ns-navigating', 'ns-route-loading');
    launcher.setAttribute('aria-expanded', 'true');
    root.dataset.state = dialog.classList.contains('is-expanded') ? 'expanded' : 'open';
    // Do not summon the mobile keyboard merely by opening the panel.
    root.querySelector('h2').focus({preventScroll:true});
  }
  function openFromLink(event, source) {
    // Preserve the browser's new-tab/window and download link gestures.
    if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    open(source);
  }
  invalidate = function () {
    generation += 1;
    if (controller) controller.abort();
    controller = null;
    pending = false;
    quotaBlocked = false;
    sessionInvalid = true;
    messages.replaceChildren();
    usage.textContent = '';
    if (form) { form.reset(); form.hidden = true; }
    login.hidden = false;
    upgrade.hidden = true;
    status.textContent = copy.session;
    controls();
    close(false);
  };
  function add(text, author) {
    var item = document.createElement('p');
    item.className = 'ns-assistant-message is-' + author;
    var label = document.createElement('strong');
    label.textContent = author === 'user' ? copy.you : 'SHARK';
    var body = document.createElement('span');
    body.textContent = String(text);
    item.append(label, body);
    messages.appendChild(item);
    messages.scrollTop = messages.scrollHeight;
  }
  async function ask() {
    if (!input || pending || quotaBlocked || sessionInvalid) return;
    var question = input.value.trim();
    if (!question) { status.textContent = copy.empty; return; }
    var token = window.nemesisCsrfToken && window.nemesisCsrfToken();
    if (!token) { invalidate(); return; }
    var ownGeneration = generation;
    var ownController = new AbortController();
    controller = ownController;
    pending = true;
    controls();
    add(question, 'user');
    input.value = '';
    status.textContent = copy.pending;
    var timeout = window.setTimeout(function () { ownController.abort(); }, 30000);
    try {
      var requestPayload = {question:question};
      ['match_id', 'pick_id'].forEach(function (name) {
        var field = form.elements.namedItem(name);
        if (field && typeof field.value === 'string' && field.value) requestPayload[name] = field.value;
      });
      var response = await fetch('/api/shark/ask', {
        method:'POST', credentials:'same-origin', signal:ownController.signal,
        headers:window.nemesisJsonHeaders(), body:JSON.stringify(requestPayload)
      });
      if (ownGeneration !== generation) return;
      if (response.status === 401 || response.status === 403) { invalidate(); return; }
      var payload = await response.json();
      if (ownGeneration !== generation) return;
      if (response.status === 429) {
        quotaBlocked = true;
        status.textContent = copy.limit;
        upgrade.hidden = false;
        input.value = question;
      } else if (response.status === 400 && payload.quota_consumed === false) {
        status.textContent = copy.invalid;
        input.value = question;
      } else if (response.ok && payload.ok === true && payload.shark && typeof payload.shark.answer === 'string') {
        add(payload.shark.answer, 'bot');
        status.textContent = '';
      } else {
        status.textContent = copy.uncertain;
        input.value = question;
      }
      if (payload.usage && Number.isSafeInteger(payload.usage.remaining) && payload.usage.remaining >= 0) {
        usage.textContent = copy.remaining.replace('{count}', String(payload.usage.remaining));
      }
    } catch (_) {
      if (ownGeneration === generation) {
        status.textContent = copy.uncertain;
        if (!input.value) input.value = question;
      }
    } finally {
      window.clearTimeout(timeout);
      if (ownGeneration === generation) {
        pending = false;
        controller = null;
        controls();
      }
    }
  }
  launcher.addEventListener('click', function (event) { openFromLink(event, launcher); });
  root.querySelector('[data-assistant-minimize]').addEventListener('click', function () { close(false); });
  root.querySelector('[data-assistant-hide]').addEventListener('click', function () {
    close(true);
    var target = document.querySelector('[data-open-explore]');
    if (target && target.getClientRects().length) target.focus({preventScroll:true});
  });
  expand.addEventListener('click', function () {
    var full = dialog.classList.toggle('is-expanded');
    expand.setAttribute('aria-pressed', String(full));
    expand.setAttribute('aria-label', full ? copy.reduce : copy.expand);
    root.dataset.state = full ? 'expanded' : 'open';
  });
  dialog.addEventListener('cancel', function (event) { event.preventDefault(); close(false); });
  dialog.addEventListener('keydown', function (event) {
    if (event.key !== 'Tab') return;
    var targets = Array.from(dialog.querySelectorAll('a[href],button:not(:disabled),textarea:not(:disabled),input:not([type="hidden"]):not(:disabled),[tabindex="0"]'))
      .filter(function (node) { return node.getClientRects().length && getComputedStyle(node).visibility !== 'hidden'; });
    var first = targets[0], last = targets[targets.length - 1];
    if (!first) { event.preventDefault(); root.querySelector('h2').focus(); return; }
    var active = document.activeElement;
    if (event.shiftKey && (active === first || active === root.querySelector('h2') || !dialog.contains(active))) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && (active === last || !dialog.contains(active))) {
      event.preventDefault(); first.focus();
    }
  });
  document.addEventListener('visibilitychange', function () { if (!document.hidden) controls(); });
  if (form) form.addEventListener('submit', function (event) { event.preventDefault(); ask(); });
  document.addEventListener('click', function (event) {
    var target = event.target.closest && event.target.closest('[data-ns-assistant-restore]');
    if (target) openFromLink(event, target);
  });
}());
