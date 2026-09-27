"""V941 dead-code purge regression.

The current SHARK answer path delegates to V845. Legacy code after the
unconditional return and helpers used only by that unreachable branch must not
return. The /dashboard compatibility route is redirect-only as well.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"

REMOVED_SHARK_HELPERS = {
    "_shark_line_match",
    "_shark_pick_parts",
    "_shark_line_pick",
    "_shark_card_pick",
    "_shark_count_requested",
    "_shark_actions",
}


def _module() -> ast.Module:
    return ast.parse(APP.read_text(encoding="utf-8"))


def _function(name: str) -> ast.FunctionDef:
    for node in _module().body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function: {name}")


def test_legacy_shark_helpers_used_only_by_unreachable_branch_are_gone():
    names = {
        node.name
        for node in _module().body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert REMOVED_SHARK_HELPERS.isdisjoint(names)
    assert "_shark_visible_picks" in names
    assert "v845_build_product_assistant_context" in names


def test_shark_answer_ends_at_v845_return_without_unreachable_tail():
    fn = _function("shark_answer")
    assert isinstance(fn.body[-1], ast.Return)
    source = ast.get_source_segment(APP.read_text(encoding="utf-8"), fn) or ""
    assert "v845_answer_shark_question" in source
    assert "q_norm = normalized_label(q)" not in source
    assert "Mi mejor opción ahora mismo" not in source


def test_dashboard_compatibility_route_is_redirect_only():
    fn = _function("v566_dashboard_page")
    assert len(fn.body) == 1
    assert isinstance(fn.body[0], ast.Return)
    source = ast.get_source_segment(APP.read_text(encoding="utf-8"), fn) or ""
    assert 'redirect("/app")' in source
    assert "dashboard_data()" not in source
    assert "render_template(" not in source
