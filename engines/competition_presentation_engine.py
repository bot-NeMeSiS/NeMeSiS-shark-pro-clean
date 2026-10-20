"""Presentation-only competition grouping shared by client and calendar views.

The grouping never changes competition identity or match truth. It uses explicit
scope/country metadata first and a small set of well-known international cup
names only when providers omit scope.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping

from engines.spanish_localization_engine import spanish_country_name


_INTERNATIONAL_SCOPES = {
    "continental", "international", "global", "worldwide", "national-team",
    "national_teams", "national teams",
}
_GEOGRAPHIC_LABELS = {
    "africa", "asia", "europe", "global", "international", "north america",
    "oceania", "south america", "world", "mundial", "uefa", "conmebol",
    "caf", "afc", "concacaf", "ofc",
}
_CONFEDERATION_LABELS = {"uefa", "conmebol", "caf", "afc", "concacaf", "ofc"}
_INTERNATIONAL_TOURNAMENTS = (
    "champions league", "europa league", "conference league",
    "copa libertadores", "copa sudamericana", "club world cup",
    "intercontinental cup", "world cup", "copa america", "european championship",
    "nations league", "africa cup of nations", "asian cup", "gold cup",
)


def _normalized(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def competition_presentation_group(item: Mapping | None) -> dict:
    """Return a safe country or international grouping for one real competition."""
    item = item if isinstance(item, Mapping) else {}
    country = str(
        item.get("country") or item.get("competition_country")
        or item.get("league_country") or ""
    ).strip()
    region = str(item.get("region") or item.get("confederation") or "").strip()
    scope = _normalized(item.get("scope") or item.get("competition_type") or item.get("type"))
    name = _normalized(" ".join(str(item.get(key) or "") for key in (
        "name", "competition_name", "league_name", "competition", "key", "competition_key"
    )))
    geo = _normalized(country)
    region_key = _normalized(region)
    is_international = (
        scope in _INTERNATIONAL_SCOPES
        or geo in _GEOGRAPHIC_LABELS
        or region_key in _CONFEDERATION_LABELS
        or (not country and region_key in _GEOGRAPHIC_LABELS)
        or any(term in name for term in _INTERNATIONAL_TOURNAMENTS)
        or bool(re.search(r"\buefa\b", name))
    )
    if is_international:
        return {
            "key": "international",
            "label": "Torneos internacionales",
            "kind": "international",
            "country": "",
            "sort": (1, ""),
        }
    localized_country = spanish_country_name(country) or country
    if localized_country:
        normalized_country = _normalized(localized_country)
        country_order = 0 if normalized_country in {"espana", "spain"} else 2
        return {
            "key": "country:" + normalized_country,
            "label": localized_country,
            "kind": "country",
            "country": localized_country,
            "sort": (country_order, normalized_country),
        }
    return {
        "key": "unknown-country",
        "label": "País sin confirmar",
        "kind": "unknown",
        "country": "",
        "sort": (3, ""),
    }


def competition_presentation_sections(items, *, collection_key="competitions") -> list[dict]:
    """Group existing rows for display, preserving every row and its source fields."""
    buckets = {}
    for raw in items or []:
        if not isinstance(raw, Mapping):
            continue
        item = dict(raw)
        group = competition_presentation_group(item)
        item["presentation_group_key"] = group["key"]
        item["presentation_group_label"] = group["label"]
        item["presentation_group_kind"] = group["kind"]
        bucket = buckets.setdefault(group["key"], {
            "key": group["key"],
            "label": group["label"],
            "kind": group["kind"],
            "country": group["country"],
            "sort": group["sort"],
            collection_key: [],
        })
        bucket[collection_key].append(item)

    sections = list(buckets.values())
    for section in sections:
        section[collection_key].sort(key=lambda item: (
            0 if item.get("has_matches") else 1,
            -int(item.get("tier") or item.get("rank") or 0),
            _normalized(item.get("name") or item.get("label") or ""),
        ))
        section["count"] = len(section[collection_key])
    sections.sort(key=lambda section: (*section["sort"], section["label"].casefold()))
    for section in sections:
        section.pop("sort", None)
    return sections
