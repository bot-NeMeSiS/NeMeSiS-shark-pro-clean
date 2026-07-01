from pathlib import Path


def main():
    css = Path("static/app.css").read_text(encoding="utf-8")
    for item in ["V850 LIVE CRESTS API SPORTS FINAL START", ".v850-live-provider", ".v850-score-focus", ".v850-live-pill", "@media (max-width: 768px)"]:
        assert item in css, item
    print("check_v850_live_crests_visual_pc_mobile OK")


if __name__ == "__main__":
    main()
