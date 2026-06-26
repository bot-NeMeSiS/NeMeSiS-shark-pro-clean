from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
css=(ROOT/"static/app.css").read_text(encoding="utf-8", errors="replace")
checks={
 "v849_block":"V849 FULL COMPANY VISUAL PRODUCT ADVANCEMENT START" in css,
 "keeps_v848":"V848 SHARK REFERENCE BACKGROUND PC MOBILE START" in css,
 "cards_depth":".card::before" in css and ".match-card::before" in css,
 "mobile":"@media(max-width:760px)" in css and "v829-mobile-quick" in css,
 "desktop":"@media(min-width:1200px)" in css,
 "admin_tables":"body[data-v849-shell=\"true\"].ns-admin table" in css,
}
failed=[k for k,v in checks.items() if not v]
print({"checks":checks,"failed":failed}); raise SystemExit(1 if failed else 0)
