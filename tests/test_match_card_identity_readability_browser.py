"""Browser geometry on canonical match cards with synthetic favorite_page data."""
import pytest
from test_match_card_favorite_browser import favorite_page
from test_app_navigation_browser import browser


@pytest.mark.parametrize("width,height,min_crest,min_text", [
    (1440, 900, 35, 14),
    (390, 844, 32, 13),
    (340, 720, 30, 13),
])
def test_match_identity_readable_in_desktop_and_mobile(favorite_page, width, height, min_crest, min_text):
    page, _pending = favorite_page
    page.set_viewport_size({"width": width, "height": height})
    card = page.locator("#favorite-primary .v933-match-card")
    card.wait_for(state="visible")
    info = card.evaluate("""node => {
      const box = node.getBoundingClientRect();
      return {
        width: box.width, scroll: node.scrollWidth,
        teams: [...node.querySelectorAll('.v933-match-teams > div')].filter(
          el => el.querySelector('.v933-team-logo')
        ).map(team => {
          const crest = team.querySelector('.v933-team-logo');
          const name = team.querySelector('strong');
          const rect = name.getBoundingClientRect();
          return {crest: crest.getBoundingClientRect().width,
                  text: parseFloat(getComputedStyle(name).fontSize),
                  left: rect.left, right: rect.right,
                  cardLeft: box.left, cardRight: box.right};
        })
      };
    }""")
    assert len(info["teams"]) == 2, info
    assert info["width"] > 0
    assert info["scroll"] <= info["width"] + 2, info
    for team in info["teams"]:
        assert team["crest"] >= min_crest, (width, team)
        assert team["text"] >= min_text, (width, team)
        assert team["left"] >= team["cardLeft"] - 2, (width, team)
        assert team["right"] <= team["cardRight"] + 2, (width, team)
