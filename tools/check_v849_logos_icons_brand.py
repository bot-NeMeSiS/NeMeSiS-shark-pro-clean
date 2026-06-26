from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
base=(ROOT/"templates/base.html").read_text(encoding="utf-8", errors="replace")
css=(ROOT/"static/app.css").read_text(encoding="utf-8", errors="replace")
checks={
 "logo_asset":(ROOT/"static/img/shark-logo.svg").exists(),
 "favicon":"rel=\"icon\"" in base and "shark-logo.svg" in base,
 "brand_refs":base.count("shark-logo.svg") >= 3,
 "crest_css":all(x in css for x in [".team-crest",".league-logo","object-fit:contain"]),
 "no_runtime_download":"download" not in css.lower(),
}
failed=[k for k,v in checks.items() if not v]
print({"checks":checks,"failed":failed}); raise SystemExit(1 if failed else 0)
