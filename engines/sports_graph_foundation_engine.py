"""Read-only Sports Graph relationship foundation.

This module builds relationship edges from canonical Sports Core entities. It
does not store a graph, open a database, call a provider, send Telegram,
trigger SHARK, touch Stripe, or create missing sports facts.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from engines.sports_platform_contracts import (
    EvidenceReference,
    build_entity_reference,
    build_sports_graph_edge,
)


SPORTS_GRAPH_FOUNDATION_CONTRACT = "SPORTS-GRAPH-FOUNDATION-RELATIONSHIPS-V1"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _text(value: Any, limit: int = 240) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()[:limit]


def _evidence(
    *,
    source: Any,
    source_type: str,
    observed_at_madrid: Any,
    state: Any = "PARTIALLY_VERIFIED",
    reference: Any = "",
    limitations: Iterable[Any] = (),
) -> EvidenceReference:
    return EvidenceReference(
        source=_text(source, 120) or "canonical_snapshot",
        source_type=_text(source_type, 80) or "sports_core",
        observed_at_madrid=_text(observed_at_madrid, 80),
        state=_text(state, 40).upper() or "PARTIALLY_VERIFIED",
        reference=_text(reference, 160) or "sports_core_entity",
        limitations=tuple(_text(item, 180) for item in limitations if _text(item, 180)),
    )


def _entity(entity_type: str, entity_id: Any, label: Any, *, source: Any, state: Any = "PARTIALLY_VERIFIED"):
    return build_entity_reference(
        entity_type,
        entity_id,
        label,
        source=source or "canonical_snapshot",
        evidence_state=state or "PARTIALLY_VERIFIED",
    )


def build_sports_graph_relationships(
    *,
    team_entity: Mapping[str, Any] | None = None,
    team_entities: Iterable[Mapping[str, Any]] | None = None,
    player_entity: Mapping[str, Any] | None = None,
    player_entities: Iterable[Mapping[str, Any]] | None = None,
    match_entities: Iterable[Mapping[str, Any]] | None = None,
    competition_entities: Iterable[Mapping[str, Any]] | None = None,
    timeline_events: Iterable[Mapping[str, Any]] | None = None,
    evidence_items: Iterable[Mapping[str, Any]] | None = None,
    match_intelligence: Mapping[str, Any] | None = None,
    picks: Iterable[Mapping[str, Any]] | None = None,
    odds: Iterable[Mapping[str, Any]] | None = None,
    telegram_context: Mapping[str, Any] | None = None,
    shark_context: Mapping[str, Any] | None = None,
    user_intelligence_context: Mapping[str, Any] | None = None,
    observed_at_madrid: Any = "",
    center: str = "team_center",
) -> dict[str, Any]:
    """Build canonical relationship edges without persistence."""

    team = _mapping(team_entity)
    team_items = _items(team_entities)
    player = _mapping(player_entity)
    player_items = _items(player_entities)
    if team:
        team_items.insert(0, team)
    if player:
        player_items.insert(0, player)
    matches = _items(match_entities)
    competitions = _items(competition_entities)
    events = _items(timeline_events)
    evidence = _items(evidence_items)
    intelligence = _mapping(match_intelligence)
    pick_items = _items(picks)
    odd_items = _items(odds)
    telegram = _mapping(telegram_context)
    shark = _mapping(shark_context)
    user_intelligence = _mapping(user_intelligence_context)
    source = team.get("source") or player.get("source") or (team_items[0].get("source") if team_items else "") or (player_items[0].get("source") if player_items else "") or "sports_core"
    edges: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    def add(source_ref, relationship: str, target_ref, ev: EvidenceReference) -> None:
        try:
            edges.append(
                build_sports_graph_edge(
                    source_ref,
                    relationship,
                    target_ref,
                    ev,
                ).to_dict()
            )
        except ValueError as exc:
            skipped.append({
                "relationship": relationship,
                "reason": str(exc),
                "source": getattr(source_ref, "entity_id", ""),
                "target": getattr(target_ref, "entity_id", ""),
            })

    team_refs: dict[str, Any] = {}
    for item in team_items:
        team_ref_item = _entity(
            "team",
            item.get("canonical_team_id") or item.get("id") or item.get("key"),
            item.get("display_name") or item.get("official_name") or item.get("name"),
            source=item.get("source") or source,
            state=item.get("data_quality") or "PARTIALLY_VERIFIED",
        )
        for alias in (
            team_ref_item.entity_id,
            item.get("canonical_team_id"),
            item.get("id"),
            item.get("key"),
            item.get("display_name"),
            item.get("official_name"),
            item.get("name"),
        ):
            normalized_alias = _text(alias, 160)
            if normalized_alias:
                team_refs[normalized_alias] = team_ref_item
                team_refs[normalized_alias.casefold()] = team_ref_item
                if ":" in normalized_alias:
                    team_refs[normalized_alias.rsplit(":", 1)[-1]] = team_ref_item
    player_refs: dict[str, Any] = {}
    for item in player_items:
        player_ref_item = _entity(
            "player",
            item.get("canonical_player_id") or item.get("id") or item.get("player_id"),
            item.get("display_name") or item.get("official_name") or item.get("player_name") or item.get("name"),
            source=item.get("source") or source,
            state=item.get("data_quality") or "PARTIALLY_VERIFIED",
        )
        for alias in (
            player_ref_item.entity_id,
            item.get("canonical_player_id"),
            item.get("id"),
            item.get("player_id"),
            item.get("display_name"),
            item.get("official_name"),
            item.get("player_name"),
            item.get("name"),
        ):
            normalized_alias = _text(alias, 180)
            if normalized_alias:
                player_refs[normalized_alias] = player_ref_item
                player_refs[normalized_alias.casefold()] = player_ref_item
                if ":" in normalized_alias:
                    player_refs[normalized_alias.rsplit(":", 1)[-1]] = player_ref_item
    player_ref = next(iter(player_refs.values()), None)
    team_ref = next(iter(team_refs.values()), None)
    match_refs = []
    match_ref_aliases: dict[str, Any] = {}
    competition_refs: dict[str, Any] = {}
    season_refs: dict[str, Any] = {}
    for competition in competitions:
        comp_id = competition.get("canonical_competition_id") or competition.get("id") or competition.get("competition_id")
        if not comp_id:
            continue
        competition_refs[str(comp_id)] = _entity(
            "competition",
            comp_id,
            competition.get("display_name") or competition.get("name") or competition.get("competition_name"),
            source=competition.get("source") or source,
            state=competition.get("data_quality") or "PARTIALLY_VERIFIED",
        )
    for match in matches:
        match_id = match.get("canonical_match_id") or match.get("id") or match.get("match_id")
        match_ref = _entity(
            "match",
            match_id,
            " vs ".join(
                item
                for item in (
                    _text(_mapping(match.get("home_team")).get("display_name") or match.get("home_team"), 80),
                    _text(_mapping(match.get("away_team")).get("display_name") or match.get("away_team"), 80),
                )
                if item
            ) or match_id,
            source=match.get("source") or source,
            state=match.get("data_quality") or "PARTIALLY_VERIFIED",
        )
        match_refs.append(match_ref)
        for alias in (
            match_id,
            match.get("id"),
            match.get("match_id"),
            match.get("external_id"),
            match.get("canonical_match_id"),
        ):
            normalized_alias = _text(alias, 120)
            if normalized_alias:
                match_ref_aliases[normalized_alias] = match_ref
                if ":" in normalized_alias:
                    match_ref_aliases[normalized_alias.rsplit(":", 1)[-1]] = match_ref
        ev = _evidence(
            source=match.get("source") or source,
            source_type="match_entity",
            observed_at_madrid=observed_at_madrid or match.get("source_timestamp"),
            state=match.get("data_quality") or "PARTIALLY_VERIFIED",
            reference=match_id,
        )
        match_teams = [
            _mapping(match.get("home_team")),
            _mapping(match.get("away_team")),
        ]
        related_team_refs = []
        for match_team in match_teams:
            for alias in (
                match_team.get("canonical_team_id"),
                match_team.get("display_name"),
                match_team.get("official_name"),
            ):
                normalized_alias = _text(alias, 160)
                related_ref = team_refs.get(normalized_alias) or team_refs.get(normalized_alias.casefold())
                if related_ref and related_ref not in related_team_refs:
                    related_team_refs.append(related_ref)
        if not related_team_refs and team_ref is not None:
            related_team_refs.append(team_ref)
        for related_team_ref in related_team_refs:
            add(match_ref, "match_has_team", related_team_ref, ev)
            add(related_team_ref, "team_has_match", match_ref, ev)
            if player_ref is not None:
                add(player_ref, "player_linked_to_team", related_team_ref, ev)
                add(related_team_ref, "team_has_player", player_ref, ev)
        if player_ref is not None:
            add(player_ref, "player_has_match", match_ref, ev)
            add(match_ref, "match_has_player", player_ref, ev)
        comp = _mapping(match.get("competition"))
        comp_id = comp.get("canonical_competition_id") or match.get("competition_id")
        if comp_id and str(comp_id) not in competition_refs:
            competition_refs[str(comp_id)] = _entity(
                "competition",
                comp_id,
                comp.get("display_name") or match.get("competition_name") or match.get("league_name"),
                source=comp.get("source") or match.get("source") or source,
                state=comp.get("data_quality") or "PARTIALLY_VERIFIED",
            )
        comp_ref = competition_refs.get(str(comp_id)) if comp_id else None
        if comp_ref:
            add(match_ref, "match_belongs_to_competition", comp_ref, ev)
            add(comp_ref, "competition_has_match", match_ref, ev)
            for related_team_ref in related_team_refs:
                add(related_team_ref, "team_competes_in_competition", comp_ref, ev)
                add(comp_ref, "competition_has_team", related_team_ref, ev)
            if player_ref is not None:
                add(player_ref, "player_competes_in_competition", comp_ref, ev)
                add(comp_ref, "competition_has_player", player_ref, ev)
        season = match.get("season") or comp.get("season")
        if season:
            season_ref = season_refs.setdefault(
                str(season),
                _entity("season", season, f"Temporada {season}", source=match.get("source") or source),
            )
            add(match_ref, "match_belongs_to_season", season_ref, ev)
            add(season_ref, "season_has_match", match_ref, ev)

    match_ref_by_id = {ref.entity_id: ref for ref in match_refs}
    match_ref_by_id.update(match_ref_aliases)
    for event in events:
        event_id = event.get("canonical_event_id") or event.get("id")
        match_id = event.get("match_id") or event.get("canonical_match_id")
        match_ref = match_ref_by_id.get(str(match_id)) or (match_refs[0] if len(match_refs) == 1 else None)
        if not event_id or not match_ref:
            skipped.append({"relationship": "timeline_event", "reason": "event_or_match_identity_missing"})
            continue
        event_ref = _entity(
            "timeline_event",
            event_id,
            event.get("event_type") or event.get("type") or event.get("label") or "Evento",
            source=event.get("source") or source,
            state="VERIFIED",
        )
        ev = _evidence(
            source=event.get("source") or source,
            source_type="timeline_event",
            observed_at_madrid=observed_at_madrid or event.get("captured_at"),
            state="VERIFIED",
            reference=event_id,
        )
        add(match_ref, "match_has_timeline_event", event_ref, ev)
        add(event_ref, "timeline_event_belongs_to_match", match_ref, ev)
        player_id = event.get("player_id")
        if player_id:
            event_player_key = _text(player_id, 180)
            event_player_ref = player_refs.get(event_player_key) or player_refs.get(event_player_key.casefold()) or _entity(
                "player",
                player_id,
                event.get("player_name") or event.get("player") or "Jugador",
                source=event.get("source") or source,
                state="PARTIALLY_VERIFIED",
            )
            add(event_player_ref, "player_appears_in_event", event_ref, ev)
            add(event_ref, "event_has_player", event_player_ref, ev)
            if team_ref is not None:
                add(event_player_ref, "player_linked_to_team", team_ref, ev)

    for item in evidence:
        evidence_id = item.get("evidence_id") or item.get("id")
        if not evidence_id:
            continue
        evidence_ref = _entity("evidence", evidence_id, item.get("claim") or item.get("kind") or "Evidencia", source=item.get("source") or source, state=item.get("state") or item.get("evidence_state") or "PARTIALLY_VERIFIED")
        for match_ref in match_refs[:1]:
            add(match_ref, "match_has_evidence", evidence_ref, _evidence(source=item.get("source") or source, source_type="evidence", observed_at_madrid=observed_at_madrid, state=item.get("state") or "PARTIALLY_VERIFIED", reference=evidence_id))

    if intelligence.get("contract") and match_refs:
        intelligence_ref = _entity(
            "match_intelligence",
            intelligence.get("match_id") or f"intelligence:{match_refs[0].entity_id}",
            intelligence.get("title") or "Match Intelligence",
            source="match_intelligence_engine",
            state=intelligence.get("certification_state") or "PARTIALLY_VERIFIED",
        )
        ev = _evidence(source="match_intelligence_engine", source_type="match_intelligence", observed_at_madrid=observed_at_madrid or intelligence.get("observed_at_madrid"), state=intelligence.get("certification_state") or "PARTIALLY_VERIFIED", reference=intelligence.get("contract"))
        for match_ref in match_refs[:1]:
            add(match_ref, "match_has_match_intelligence", intelligence_ref, ev)
            add(intelligence_ref, "match_intelligence_describes_match", match_ref, ev)
        if player_ref is not None:
            add(player_ref, "player_context_uses_match_intelligence", intelligence_ref, ev)
            add(intelligence_ref, "match_intelligence_has_player_context", player_ref, ev)

    for pick in pick_items:
        match_id = _text(pick.get("match_id"), 120)
        match_ref = match_ref_by_id.get(match_id) or (match_refs[0] if len(match_refs) == 1 and match_id else None)
        pick_id = pick.get("id") or pick.get("pick_id")
        if not pick_id or not match_ref:
            continue
        pick_ref = _entity("pick", pick_id, pick.get("selection_display") or pick.get("selection") or "Pick", source=pick.get("source") or "picks", state="PARTIALLY_VERIFIED")
        add(pick_ref, "pick_references_match", match_ref, _evidence(source=pick.get("source") or "picks", source_type="pick", observed_at_madrid=observed_at_madrid, state="PARTIALLY_VERIFIED", reference=pick_id))

    for odd in odd_items:
        match_id = _text(odd.get("match_id"), 120)
        match_ref = match_ref_by_id.get(match_id) or (match_refs[0] if len(match_refs) == 1 and match_id else None)
        odd_id = odd.get("id") or odd.get("market_id")
        if not odd_id or not match_ref:
            continue
        odd_ref = _entity("odds", odd_id, odd.get("market") or "Cuota", source=odd.get("source") or "odds", state="PARTIALLY_VERIFIED")
        add(odd_ref, "odds_prices_match", match_ref, _evidence(source=odd.get("source") or "odds", source_type="odds", observed_at_madrid=observed_at_madrid, state="PARTIALLY_VERIFIED", reference=odd_id))

    if telegram and match_refs:
        telegram_ref = _entity("telegram_context", telegram.get("id") or "telegram-context", "Telegram Context", source="telegram", state=telegram.get("certification_state") or "PARTIALLY_VERIFIED")
        add(telegram_ref, "telegram_context_mentions_match", match_refs[0], _evidence(source="telegram", source_type="telegram_context", observed_at_madrid=observed_at_madrid, state=telegram.get("certification_state") or "PARTIALLY_VERIFIED", reference=telegram.get("contract") or "telegram_context"))
    if shark and match_refs:
        shark_ref = _entity("shark_context", shark.get("id") or "shark-context", "SHARK Context", source="shark", state=shark.get("certification_state") or "PARTIALLY_VERIFIED")
        add(shark_ref, "shark_context_analyzes_match", match_refs[0], _evidence(source="shark", source_type="shark_context", observed_at_madrid=observed_at_madrid, state=shark.get("certification_state") or "PARTIALLY_VERIFIED", reference=shark.get("contract") or "shark_context"))
        if player_ref is not None:
            add(shark_ref, "shark_context_mentions_player", player_ref, _evidence(source="shark", source_type="shark_context", observed_at_madrid=observed_at_madrid, state=shark.get("certification_state") or "PARTIALLY_VERIFIED", reference=shark.get("contract") or "shark_context"))
    if user_intelligence and player_ref is not None:
        user_ref = _entity("user_intelligence_context", user_intelligence.get("id") or "user-intelligence-context", "User Intelligence Context", source="user_intelligence", state=user_intelligence.get("certification_state") or "NOT_CONFIGURED")
        add(user_ref, "user_intelligence_observes_player", player_ref, _evidence(source="user_intelligence", source_type="user_intelligence_context", observed_at_madrid=observed_at_madrid, state=user_intelligence.get("certification_state") or "NOT_CONFIGURED", reference=user_intelligence.get("contract") or "USER-INTELLIGENCE-PLATFORM-V1"))

    relations = sorted({edge["relationship"] for edge in edges})
    return {
        "ok": True,
        "contract": SPORTS_GRAPH_FOUNDATION_CONTRACT,
        "center": _text(center, 80) or "team_center",
        "edge_count": len(edges),
        "edges": edges,
        "relationships": relations,
        "skipped": skipped,
        "future_centers_ready": ["Team Center", "Competition Center", "Player Center"],
        "persistence_authorized": False,
        "diagnostics": {
            "database_queries": 0,
            "database_writes": 0,
            "external_calls": 0,
            "telegram_sends": 0,
            "stripe_calls": 0,
            "new_dependencies": 0,
        },
    }
