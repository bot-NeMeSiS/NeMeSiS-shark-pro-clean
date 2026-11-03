'use strict';
// Execute only through the caller's guarded offline Node process. The complete
// shipped script runs unchanged in this small DOM; no App import or browser.
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const source = readFileSync(join(__dirname, '../static/platform-motion.js'), 'utf8');

class Target {
  constructor() { this.listeners = new Map(); }
  addEventListener(name, callback, capture = false) {
    const entries = this.listeners.get(name) || [];
    entries.push({callback, capture: capture === true});
    this.listeners.set(name, entries);
  }
  emit(name, event = {}) {
    const value = {type:name, target:this, ...event};
    for (const entry of this.listeners.get(name) || []) entry.callback(value);
  }
}
class Element extends Target {
  constructor(kind = 'div', attributes = {}) {
    super();
    this.kind = kind;
    this.attributes = new Map(Object.entries(attributes));
    this.parent = null;
    this.hidden = false;
    this.inert = false;
    this.disabled = false;
    this.isContentEditable = false;
    this.textContent = '';
    this.selectors = new Map();
  }
  contains(other) {
    for (let node = other; node; node = node.parent) if (node === this) return true;
    return false;
  }
  getAttribute(name) { return this.attributes.has(name) ? this.attributes.get(name) : null; }
  setAttribute(name, value) {
    assert.notEqual(name, 'href', 'The carousel must never retarget a fixture link');
    this.attributes.set(name, String(value));
  }
  removeAttribute(name) { this.attributes.delete(name); }
  querySelector(selector) { return this.selectors.get(selector) || null; }
  querySelectorAll(selector) { return this.selectors.get(selector) || []; }
  matches(selector) {
    if (selector.startsWith('dialog')) return this.kind === 'dialog';
    if (selector.startsWith('input')) return ['input', 'textarea', 'select'].includes(this.kind);
    return false;
  }
}
function harness(options = {}) {
  const count = options.count === undefined ? 2 : options.count;
  const root = new Element();
  const controls = new Element(); controls.hidden = true;
  const previous = new Element('button');
  const next = new Element('button');
  const toggle = new Element('button', {
    'data-pause':'Pausar', 'data-play':'Reanudar', 'aria-pressed':'false',
    'data-paused-status':'Avance automático pausado',
    'data-playing-status':'Avance automático activado',
  });
  const toggleLabel = new Element('span'); toggleLabel.parent = toggle;
  const pauseIcon = new Element('g'); pauseIcon.parent = toggle;
  const playIcon = new Element('g', {hidden:''}); playIcon.parent = toggle;
  toggle.selectors.set('[data-home-featured-toggle-label]', toggleLabel);
  toggle.selectors.set('[data-home-featured-pause-icon]', pauseIcon);
  toggle.selectors.set('[data-home-featured-play-icon]', playIcon);
  const counter = new Element(); counter.textContent = '1 / ' + count;
  const status = new Element();
  const globalToggle = options.globalPreference ? new Element('button', {'aria-pressed':'false'}) : null;
  const slides = Array.from({length:count}, (_unused, index) => {
    const slide = new Element(); slide.hidden = index !== 0; slide.parent = root;
    const card = new Element('article', {'data-v934-match-id':'owned-' + index}); card.parent = slide;
    const link = new Element('a', {href:'/match/owned-' + index}); link.parent = card;
    const score = new Element(); score.parent = card; score.textContent = '0 - 0';
    const badge = new Element('span'); badge.parent = slide;
    const favorite = new Element('button', {'data-value':'owned-' + index, 'aria-pressed':'false'});
    favorite.parent = card;
    slide.selectors.set('[data-home-featured-favorite]', badge);
    slide.selectors.set('[data-v934-match-card]', card);
    card.selectors.set('.fav-star[data-kind="match"]', favorite);
    slide.card = card; slide.link = link; slide.score = score;
    slide.badge = badge; slide.favorite = favorite;
    return slide;
  });
  root.selectors.set('[data-home-featured-slide]', slides);
  const parts = {controls, prev:previous, next, toggle, counter, status};
  for (const [name, node] of Object.entries(parts)) {
    node.parent = name === 'controls' || name === 'status' ? root : controls;
    root.selectors.set('[data-home-featured-' + name + ']', node);
  }
  if (options.missingControl) root.selectors.delete('[data-home-featured-' + options.missingControl + ']');
  const document = new Target();
  document.hidden = Boolean(options.hidden);
  document.body = new Element('body'); root.parent = document.body;
  document.activeElement = document.body;
  document.querySelectorAll = selector => selector === '[data-home-featured]' && options.root !== false ? [root] : [];
  let dialog = null;
  document.querySelector = selector => {
    if (selector === '[data-motion-preferences] [data-motion-toggle]') return globalToggle;
    if (selector.startsWith('dialog[')) return dialog;
    // Decoration is absent: the independent sports controller must still work.
    return null;
  };
  const media = new Target(); media.matches = Boolean(options.reduce);
  const timers = new Map();
  let timerSerial = 0, maximumTimers = 0;
  const window = new Target();
  window.matchMedia = () => media;
  window.setTimeout = (callback, delay) => {
    assert.equal(delay, 9000, 'Only the single nine-second rotation timeout is needed');
    const id = ++timerSerial;
    timers.set(id, callback);
    maximumTimers = Math.max(maximumTimers, timers.size);
    assert.ok(timers.size <= 1, 'A controller must never own duplicate timers');
    return id;
  };
  window.clearTimeout = id => timers.delete(id);
  const intersections = [], mutations = [];
  if (options.intersection) {
    window.IntersectionObserver = class {
      constructor(callback, settings) { this.callback = callback; this.settings = settings; intersections.push(this); }
      observe(target) { this.target = target; }
    };
  }
  class MutationObserver {
    constructor(callback) { this.callback = callback; mutations.push(this); }
    observe(target, settings) { this.target = target; this.settings = settings; }
  }
  const forbidden = () => assert.fail('No network, storage, navigation or external API access is allowed');
  window.fetch = forbidden;
  const context = {document, window, MutationObserver, fetch:forbidden, console};
  for (const name of ['localStorage', 'sessionStorage']) {
    Object.defineProperty(context, name, {get:forbidden});
    Object.defineProperty(window, name, {get:forbidden});
  }
  const evaluate = () => vm.runInNewContext(source, context, {filename:'platform-motion.js'});
  function dispatch(target, name, detail = {}) {
    const event = {type:name, target, defaultPrevented:false,
      preventDefault() { this.defaultPrevented = true; }, ...detail};
    const ancestors = [];
    for (let node = target.parent; node; node = node.parent) ancestors.push(node);
    for (const node of [...ancestors].reverse()) {
      for (const entry of node.listeners.get(name) || []) if (entry.capture) entry.callback(event);
    }
    for (const entry of target.listeners.get(name) || []) entry.callback(event);
    for (const node of ancestors) {
      for (const entry of node.listeners.get(name) || []) if (!entry.capture) entry.callback(event);
    }
    if (name === 'focusin') document.emit(name, event);
    return event;
  }
  function focus(target) {
    const old = document.activeElement;
    document.activeElement = target;
    if (old && old !== target) dispatch(old, 'focusout', {relatedTarget:target});
    dispatch(target, 'focusin', {relatedTarget:old});
  }
  function tick() {
    assert.equal(timers.size, 1);
    const [id, callback] = timers.entries().next().value;
    timers.delete(id);
    callback();
  }
  function mutation(target) {
    for (const observer of mutations) {
      if (observer.target === target || observer.settings.subtree) observer.callback([{target}]);
    }
  }
  evaluate();
  return {root, controls, previous, next, toggle, toggleLabel, pauseIcon, playIcon, counter, status, slides, timers, document, window,
    dispatch, focus, tick, evaluate, globalToggle,
    favorite(index, active) { const button = slides[index].favorite; button.setAttribute('aria-pressed', String(active)); mutation(button); },
    maximumTimers:() => maximumTimers,
    visible:() => slides.filter(slide => !slide.hidden),
    reduced(value) { media.matches = value; media.emit('change'); },
    visibility(value) { document.hidden = value; document.emit('visibilitychange'); },
    intersect(ratio) {
      for (const observer of intersections) {
        assert.equal(observer.settings.threshold, 0.5);
        observer.callback([{target:root, isIntersecting:ratio > 0, intersectionRatio:ratio}]);
      }
    },
    preference(paused) { globalToggle.setAttribute('aria-pressed', String(paused)); mutation(globalToggle); },
    dialog(open) {
      const changed = dialog || new Element('dialog');
      dialog = open ? changed : null;
      mutation(changed);
    },
  };
}

test('SSR remains usable without a carousel, with one slide or incomplete controls', () => {
  for (const options of [{root:false}, {count:0}, {count:1}, {missingControl:'next'}]) {
    const h = harness(options);
    assert.equal(h.timers.size, 0);
    assert.equal(h.controls.hidden, true);
    if (h.slides.length) assert.equal(h.slides[0].hidden, false);
  }
});

test('independent controller rotates existing hidden DOM cards after nine seconds without announcements', () => {
  const h = harness();
  assert.equal(h.controls.hidden, false);
  assert.equal(h.timers.size, 1);
  const original = h.slides.slice();
  h.slides[1].score.textContent = '0 - 1'; // An existing realtime updater can update a hidden card.
  h.tick();
  assert.equal(h.visible()[0], original[1]);
  assert.equal(h.visible()[0].score.textContent, '0 - 1');
  assert.equal(h.visible()[0].link.getAttribute('href'), '/match/owned-1');
  assert.equal(h.slides[0].inert, true);
  assert.equal(h.status.textContent, '');
  assert.equal(h.counter.textContent, '2 / 2');
  h.tick();
  assert.equal(h.visible()[0], original[0]);
  assert.equal(h.maximumTimers(), 1);
});

test('manual next and previous wrap, pause autoplay and announce only the manual selection', () => {
  const h = harness();
  h.dispatch(h.next, 'click');
  assert.equal(h.visible()[0], h.slides[1]);
  assert.equal(h.status.textContent, 'Partido 2 de 2');
  assert.equal(h.toggleLabel.textContent, 'Reanudar');
  assert.equal(h.timers.size, 0);
  h.dispatch(h.previous, 'click');
  assert.equal(h.visible()[0], h.slides[0]);
  h.dispatch(h.previous, 'click');
  assert.equal(h.visible()[0], h.slides[1]);
});

test('toggle focus and pointer events stop the timer without reversing Pause or explicit Play intent', () => {
  const h = harness();
  h.dispatch(h.toggle, 'pointerdown');
  h.focus(h.toggle);
  h.window.emit('pointerup');
  assert.equal(h.timers.size, 0);
  h.dispatch(h.toggle, 'click');
  assert.equal(h.toggleLabel.textContent, 'Reanudar');
  assert.equal(h.toggle.getAttribute('aria-pressed'), 'true');
  h.dispatch(h.toggle, 'pointerdown');
  h.window.emit('pointerup');
  h.dispatch(h.toggle, 'click');
  assert.equal(h.toggleLabel.textContent, 'Pausar');
  assert.equal(h.toggle.getAttribute('aria-pressed'), 'false');
  assert.equal(h.timers.size, 0, 'No retargeting while focus remains inside');
  h.focus(h.document.body);
  assert.equal(h.timers.size, 1);
});

test('fixture interaction latches pause and never changes or intercepts the native exact link', () => {
  const h = harness();
  const link = h.slides[0].link;
  h.dispatch(link, 'pointerdown');
  h.window.emit('pointerup');
  const event = h.dispatch(link, 'click');
  assert.equal(h.timers.size, 0);
  assert.equal(event.defaultPrevented, false);
  assert.equal(link.getAttribute('href'), '/match/owned-0');
  assert.equal(h.visible()[0], h.slides[0]);
  h.root.emit('mouseleave');
  assert.equal(h.timers.size, 0);
});

test('hover suspends rotation and a card focus or key interaction requires explicit Play', () => {
  const h = harness();
  h.root.emit('mouseenter');
  assert.equal(h.timers.size, 0);
  h.root.emit('mouseleave');
  assert.equal(h.timers.size, 1);
  h.focus(h.slides[0].link);
  h.focus(h.document.body);
  assert.equal(h.timers.size, 0);
  h.dispatch(h.toggle, 'click');
  assert.equal(h.timers.size, 1);
  h.dispatch(h.slides[0].link, 'keydown', {key:'Enter'});
  assert.equal(h.timers.size, 0);
});

test('page visibility never silently resumes a paused carousel', () => {
  const h = harness();
  h.visibility(true);
  h.visibility(false);
  assert.equal(h.timers.size, 0);
  h.dispatch(h.toggle, 'click');
  assert.equal(h.timers.size, 1);
  const initiallyHidden = harness({hidden:true});
  initiallyHidden.visibility(false);
  assert.equal(initiallyHidden.timers.size, 0);
});

test('visibility ends an interrupted pointer gesture before explicit keyboard Play', () => {
  const h = harness();
  h.root.emit('mouseenter');
  h.dispatch(h.toggle, 'pointerdown');
  h.focus(h.toggle);
  // The gesture can finish elsewhere while the page is hidden, without this
  // document receiving pointerup or pointercancel. No automatic resume follows.
  h.visibility(true);
  h.visibility(false);
  assert.equal(h.timers.size, 0);
  h.dispatch(h.toggle, 'keydown', {key:'Enter'});
  h.dispatch(h.toggle, 'click');
  assert.equal(h.toggleLabel.textContent, 'Pausar');
  assert.equal(h.timers.size, 0, 'Focused controls still prevent retargeting');
  h.focus(h.document.body);
  assert.equal(h.timers.size, 1, 'Explicit Play can resume after focus leaves');
  h.tick();
  assert.equal(h.visible()[0], h.slides[1]);
});

test('bfcache return remains paused until explicit Play', () => {
  const h = harness();
  h.dispatch(h.toggle, 'pointerdown'); // Navigation can interrupt a gesture before pointerup.
  h.window.emit('pagehide');
  h.window.emit('pageshow', {persisted:true});
  assert.equal(h.timers.size, 0);
  assert.equal(h.visible()[0], h.slides[0]);
  h.dispatch(h.toggle, 'click');
  assert.equal(h.timers.size, 1);
});

test('initial and dynamic reduced motion prevent autoplay while manual navigation remains available', () => {
  const h = harness({reduce:true});
  assert.equal(h.timers.size, 0);
  h.dispatch(h.next, 'click');
  assert.equal(h.visible()[0], h.slides[1]);
  h.dispatch(h.toggle, 'click');
  assert.equal(h.timers.size, 0);
  h.reduced(false);
  assert.equal(h.timers.size, 0);
  h.dispatch(h.toggle, 'click');
  assert.equal(h.timers.size, 1);
  h.reduced(true);
  h.reduced(false);
  assert.equal(h.timers.size, 0);
});

test('intersection suspends below half visibility without losing startup Play intent', () => {
  const h = harness({intersection:true});
  assert.equal(h.timers.size, 0);
  h.intersect(0.5);
  assert.equal(h.timers.size, 1);
  h.intersect(0.49);
  assert.equal(h.timers.size, 0);
  h.intersect(1);
  assert.equal(h.timers.size, 1);
  h.visibility(true); h.visibility(false);
  h.intersect(1);
  assert.equal(h.timers.size, 0, 'Intersection cannot override a visibility pause');
});

test('optional global motion pause is respected without reading storage or requiring its controls', () => {
  const h = harness({globalPreference:true});
  h.preference(true);
  assert.equal(h.timers.size, 0);
  h.preference(false);
  assert.equal(h.timers.size, 0);
  h.dispatch(h.toggle, 'click');
  assert.equal(h.timers.size, 1);
});

test('reduced motion disables the native Play control and restoration enables it without autoplay', () => {
  const h = harness();
  assert.equal(h.toggle.disabled, false);
  h.reduced(true);
  assert.equal(h.toggle.disabled, true);
  assert.equal(h.toggleLabel.textContent, 'Reanudar');
  assert.equal(h.toggle.getAttribute('aria-pressed'), 'true');
  assert.equal(h.timers.size, 0);
  h.dispatch(h.next, 'click');
  assert.equal(h.visible()[0], h.slides[1], 'Manual arrows remain usable');
  assert.equal(h.toggle.disabled, true);
  h.reduced(false);
  assert.equal(h.toggle.disabled, false);
  assert.equal(h.toggleLabel.textContent, 'Reanudar');
  assert.equal(h.timers.size, 0, 'Restored permission is not Play intent');
  h.dispatch(h.toggle, 'click');
  assert.equal(h.toggle.getAttribute('aria-pressed'), 'false');
  assert.equal(h.timers.size, 1);
});

test('global motion pause disables native Play and restoration leaves manual Play available but idle', () => {
  const h = harness({globalPreference:true});
  assert.equal(h.toggle.disabled, false);
  h.preference(true);
  assert.equal(h.toggle.disabled, true);
  assert.equal(h.toggleLabel.textContent, 'Reanudar');
  assert.equal(h.timers.size, 0);
  h.dispatch(h.previous, 'click');
  assert.equal(h.visible()[0], h.slides[1], 'Global motion pause does not disable manual arrows');
  assert.equal(h.toggle.disabled, true);
  h.preference(false);
  assert.equal(h.toggle.disabled, false);
  assert.equal(h.toggle.getAttribute('aria-pressed'), 'true');
  assert.equal(h.timers.size, 0);
  h.dispatch(h.toggle, 'click');
  assert.equal(h.toggleLabel.textContent, 'Pausar');
  assert.equal(h.timers.size, 1);
});

test('writing elsewhere suspends autoplay without moving focus', () => {
  const h = harness();
  const editor = new Element('textarea'); editor.parent = h.document.body;
  h.focus(editor);
  assert.equal(h.timers.size, 0);
  assert.equal(h.document.activeElement, editor);
  h.focus(h.document.body);
  assert.equal(h.timers.size, 1);
});

test('a modal dialog suspends the timer while open', () => {
  const h = harness();
  h.dialog(true);
  assert.equal(h.timers.size, 0);
  assert.equal(h.visible()[0], h.slides[0]);
  h.dialog(false);
  assert.equal(h.timers.size, 1);
});

test('repeated script initialization does not duplicate timers or manual handlers', () => {
  const h = harness();
  h.evaluate();
  assert.equal(h.timers.size, 1);
  h.dispatch(h.next, 'click');
  assert.equal(h.visible()[0], h.slides[1]);
  assert.equal(h.timers.size, 0);
});

test('persistent icon nodes, accessible action and explicit state survive repeated updates', () => {
  const h = harness();
  const original = [h.toggleLabel, h.pauseIcon, h.playIcon];
  assert.equal(h.toggle.getAttribute('aria-label'), 'Pausar');
  assert.equal(h.pauseIcon.getAttribute('hidden'), null);
  assert.equal(h.playIcon.getAttribute('hidden'), '');
  h.dispatch(h.toggle, 'click');
  assert.equal(h.status.textContent, 'Avance automático pausado');
  assert.equal(h.toggleLabel.textContent, 'Reanudar');
  assert.equal(h.toggle.getAttribute('aria-label'), 'Reanudar');
  assert.equal(h.toggle.getAttribute('data-home-featured-tooltip'), 'Reanudar');
  assert.equal(h.pauseIcon.getAttribute('hidden'), '');
  assert.equal(h.playIcon.getAttribute('hidden'), null);
  h.dispatch(h.toggle, 'click');
  assert.equal(h.status.textContent, 'Avance automático activado');
  assert.equal(h.toggle.getAttribute('aria-label'), 'Pausar');
  h.reduced(true); h.reduced(false);
  assert.equal(h.toggleLabel, original[0]);
  assert.equal(h.toggle.querySelector('[data-home-featured-pause-icon]'), original[1]);
  assert.equal(h.toggle.querySelector('[data-home-featured-play-icon]'), original[2]);
});

test('entry is not initial and manual changes honor reduced and global motion permission', () => {
  const h = harness({globalPreference:true});
  const entered = () => h.slides.filter(slide => slide.getAttribute('data-home-featured-enter') === 'true');
  assert.equal(entered().length, 0);
  h.dispatch(h.next, 'click');
  assert.deepEqual(entered(), [h.slides[1]]);
  assert.equal(h.visible().length, 1);
  assert.equal(h.slides[0].getAttribute('aria-hidden'), 'true');
  assert.equal(h.slides[1].getAttribute('aria-hidden'), 'false');
  h.reduced(true);
  assert.equal(entered().length, 0);
  h.dispatch(h.next, 'click');
  assert.equal(h.visible()[0], h.slides[0]);
  assert.equal(entered().length, 0);
  h.reduced(false); h.preference(true);
  h.dispatch(h.previous, 'click');
  assert.equal(h.visible()[0], h.slides[1]);
  assert.equal(entered().length, 0);
  h.preference(false);
  assert.equal(h.timers.size, 0);
  h.dispatch(h.next, 'click');
  assert.deepEqual(entered(), [h.slides[0]]);
  h.dispatch(h.slides[0], 'animationcancel', {animationName:'home-featured-enter'});
  assert.equal(entered().length, 0);
});

test('favorite badge follows only its same-card accepted control, including one static slide', () => {
  for (const count of [1, 2]) {
    const h = harness({count});
    assert.equal(h.slides[0].badge.hidden, true);
    if (count === 2) assert.equal(h.slides[1].badge.hidden, true);
    h.favorite(0, true);
    assert.equal(h.slides[0].badge.hidden, false);
    if (count === 2) assert.equal(h.slides[1].badge.hidden, true);
    h.evaluate();
    h.favorite(0, false);
    assert.equal(h.slides[0].badge.hidden, true);
    assert.equal(h.slides[0].link.getAttribute('href'), '/match/owned-0');
    assert.equal(h.maximumTimers(), count === 2 ? 1 : 0);
  }
});
