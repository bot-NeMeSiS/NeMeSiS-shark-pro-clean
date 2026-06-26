from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
css=(ROOT/"static/app.css").read_text(encoding="utf-8", errors="replace")
checks={
 "safe_area":"env(safe-area-inset-bottom)" in css,
 "bottom_nav_centered":"translateX(-50%)" in css and "grid-template-columns:repeat(5" in css,
 "floating_safe":"bottom:calc(env(safe-area-inset-bottom) + 78px)" in css,
 "no_overflow":"overflow-x:hidden" in css,
 "mobile_quick_scroll":"overflow-x:auto" in css,
}
failed=[k for k,v in checks.items() if not v]
print({"checks":checks,"failed":failed}); raise SystemExit(1 if failed else 0)
