from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
    for token in ["V852 REAL VIDEO PRODUCT PERFECTION FINAL START", "v852-pick-muted", "v852-live-empty-diagnostic", "@media (max-width: 768px)"]:
        assert token in css, token
    print("V852 visual PC/mobile polish OK")


if __name__ == "__main__":
    main()
