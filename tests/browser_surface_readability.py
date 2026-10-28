"""Conservative measurements of rendered, flat browser surfaces.

This helper deliberately refuses to assign a contrast ratio to unresolved
images, gradients, blending, filters or generated decoration. Transparent text
ancestors are composited only as far as an observed opaque background. It never
assumes that an unobserved browser canvas is black or white.
"""
from __future__ import annotations

import json
import math


_OBSERVE = r"""(root, selectors) => {
  const rgba = value => {
    const match = value.trim().match(/^rgba?\(([^)]+)\)$/i);
    if (!match) return null;
    const parts = match[1].replace(/[,/]/g, ' ').trim().split(/\s+/);
    if (parts.length !== 3 && parts.length !== 4) return null;
    const rgb = parts.slice(0, 3).map(v => v.endsWith('%') ? parseFloat(v) * 2.55 : Number(v));
    const a = parts.length === 4 ? (parts[3].endsWith('%') ? parseFloat(parts[3]) / 100 : Number(parts[3])) : 1;
    return [...rgb, a].every(Number.isFinite) ? [...rgb, a] : null;
  };
  const over = (front, back) => {
    const alpha = front[3] + back[3] * (1 - front[3]);
    if (!alpha) return [0, 0, 0, 0];
    return [0, 1, 2].map(i => (front[i] * front[3] + back[i] * back[3] * (1 - front[3])) / alpha).concat(alpha);
  };
  const visible = el => {
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility === 'visible'
      && el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true});
  };
  const identity = el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + '.' + [...el.classList].join('.');
  const generatedPaint = el => ['::before', '::after'].flatMap(pseudo => {
    const s = getComputedStyle(el, pseudo);
    if (s.content === 'none' || s.content === 'normal' || s.display === 'none' || s.visibility !== 'visible' || Number(s.opacity) === 0) return [];
    const color = rgba(s.backgroundColor);
    return s.backgroundImage !== 'none' || (color && color[3] > 0)
      ? [{element: identity(el), pseudo, image: s.backgroundImage, color: s.backgroundColor}] : [];
  });
  const sample = (el, spec) => {
    const s = getComputedStyle(el), unknown = [], ancestry = [];
    let opacity = 1;
    for (let n = el; n; n = n.parentElement) {
      const style = getComputedStyle(n);
      opacity *= Number(style.opacity);
      if (style.filter !== 'none' || style.mixBlendMode !== 'normal')
        unknown.push({element: identity(n), filter: style.filter, blend: style.mixBlendMode});
    }
    let background = [0, 0, 0, 0];
    for (let n = el; n; n = n.parentElement) {
      const style = getComputedStyle(n), color = rgba(style.backgroundColor);
      ancestry.push({element: identity(n), background: style.backgroundColor, image: style.backgroundImage});
      if (!color) { unknown.push({element: identity(n), color: style.backgroundColor}); break; }
      if (style.backgroundImage !== 'none') unknown.push({element: identity(n), image: style.backgroundImage});
      unknown.push(...generatedPaint(n));
      background = over(background, color);
      if (background[3] >= 1) break;
    }
    if (background[3] < 1) unknown.push({reason: 'no observed opaque ancestor'});
    const textStyle = spec.pseudo ? getComputedStyle(el, spec.pseudo) : s;
    const foreground = rgba(textStyle.color);
    if (!foreground) unknown.push({foreground: textStyle.color});
    if (foreground && spec.pseudo) foreground[3] *= Number(textStyle.opacity);
    const text = spec.pseudo === '::placeholder' ? el.getAttribute('placeholder') :
      el.matches('input,textarea,select') ? el.value : el.textContent.trim();
    return {selector: spec.selector, pseudo: spec.pseudo || null, element: identity(el),
      visible: visible(el), text: (text || '').slice(0, 100), opacity,
      foreground, background, renderedForeground: foreground && background[3] === 1 ? over(foreground, background) : null,
      unknown, ancestry, fontSize: s.fontSize, fontWeight: s.fontWeight};
  };
  const style = getComputedStyle(root);
  const samples = selectors.map(value => {
    const spec = typeof value === 'string' ? {selector: value} : value;
    const candidates = spec.selector === ':scope' ? [root] : [...root.querySelectorAll(spec.selector)];
    const found = candidates.find(el => visible(el) && (spec.pseudo ? el.matches(':placeholder-shown') && el.getAttribute('placeholder') :
      el.matches('input,textarea,select') ? el.value : el.textContent.trim()));
    return found ? sample(found, spec) : {selector: spec.selector, missingVisibleText: true};
  });
  return {element: identity(root), visible: visible(root), background: rgba(style.backgroundColor),
    backgroundImage: style.backgroundImage, opacity: Number(style.opacity), backdropFilter: style.backdropFilter,
    samples};
}"""


def _luminance(rgb):
    channels = [value / 255 for value in rgb[:3]]
    linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4
              for value in channels]
    return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))


def observe_surface(locator, selectors):
    """Return measurements, including explicit reasons when contrast is unknown."""
    assert locator.is_visible(), "The requested surface must actually be visible"
    result = locator.evaluate(_OBSERVE, list(selectors))
    for sample in result["samples"]:
        if not sample.get("unknown") and sample.get("renderedForeground") is not None:
            foreground = _luminance(sample["renderedForeground"])
            background = _luminance(sample["background"])
            sample["contrast"] = (max(foreground, background) + .05) / (min(foreground, background) + .05)
        else:
            sample["contrast"] = None
    return result


def assert_surface_legible(locator, selectors, *, require_solid=True):
    """Assert opaque content and >=4.5:1 for actual text, without rounding."""
    result = observe_surface(locator, selectors)
    evidence = json.dumps(result, ensure_ascii=False)
    assert result["visible"] and result["samples"], evidence
    assert math.isclose(result["opacity"], 1, abs_tol=1e-9), evidence
    if require_solid:
        assert result["background"] and result["background"][3] == 1, evidence
        assert result["backgroundImage"] == "none", evidence
        assert result["backdropFilter"] == "none", evidence
    for sample in result["samples"]:
        assert not sample.get("missingVisibleText"), evidence
        assert sample["visible"] and sample["text"], evidence
        assert math.isclose(sample["opacity"], 1, abs_tol=1e-9), evidence
        assert not sample["unknown"], evidence
        assert sample["background"][3] == 1, evidence
        assert sample["contrast"] is not None and sample["contrast"] >= 4.5, evidence
    return result
