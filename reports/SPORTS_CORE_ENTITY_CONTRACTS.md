# Sports Core Entity Contracts

## Match Entity

Contract: SPORTS-CORE-MATCH-ENTITY-V1

Canonical fields include: canonical_match_id, provider_match_ids, sport, competition, season, round, stage, home_team, away_team, kickoff_at, timezone, status, phase, minute, added_time, score, period_scores, venue, officials, events, freshness, source, source_timestamp, data_quality and limitations.

Allowed status/phase language: scheduled, pre_match, live, halftime, second_half, extra_time, penalties, postponed, suspended, cancelled, finished, unknown.

Rule: a generic LIVE status can use a confirmed minute to identify second_half. Minute 68 remains second_half.

## Team Entity

Contract: SPORTS-CORE-TEAM-ENTITY-V1

Represents canonical_team_id, provider_team_ids, official/display names, aliases, slug, country, city, competition_ids, crest, crest_source, venue, founded, gender, category, data_quality, source and limitations.

Rule: a crest may be official, provider URL, cached, fallback or unavailable. It is never invented.

## Competition Entity

Contract: SPORTS-CORE-COMPETITION-ENTITY-V1

Represents canonical_competition_id, provider_competition_ids, official/display names, aliases, country, level, type, season, stage, logo, logo_source, standings/fixtures availability, data_quality, source and limitations.

Rule: different providers or ambiguous names are not auto-merged.

## Player Entity

Contract: SPORTS-CORE-PLAYER-ENTITY-V1

Prepared for partial data. Represents canonical_player_id, provider_player_ids, official/display names, aliases, team_id, position, shirt number, nationality, birth date, status, injury status, photo, photo_source, data_quality, source and limitations.

Rule: missing photo or injury information stays unavailable.

## Timeline Event Entity

Contract: SPORTS-CORE-TIMELINE-EVENT-V1

Types include: goal, own_goal, penalty_goal, missed_penalty, var, yellow_card, second_yellow, red_card, substitution, injury, period_start, period_end, added_time, score_change, suspension, restart, unknown.

Fields include canonical_event_id, provider_event_id, match_id, event_type, subtype, period, minute, added_time, timestamp, team_id, player_id, related_player_id, score_after, description, source, source_timestamp, confidence, data_quality and limitations.

Rule: duplicate events are deduped by identity and fact signature.

## Evidence Entity

Contract: SPORTS-CORE-EVIDENCE-V1

Fields include evidence_id, match_id, category, claim, raw_value, normalized_value, source, method, observed_at, freshness, confidence, limitations, missing_information, stale and usable_for_intelligence.

Rule: every conclusion must remain traceable to evidence or mark missing information.

## Freshness Entity

Contract: SPORTS-CORE-FRESHNESS-V1

States: fresh, aging, stale, unknown, unavailable.

Rule: stale data cannot become apparent live intelligence.

## SHARK Intelligence Platform Contract

Contract: SHARK-INTELLIGENCE-PLATFORM-V1

Consumes: SPORTS-CORE-UNIFIED-DOMAIN-MODEL-V1, SPORTS-KNOWLEDGE-LAYER-V1, SPORTS-GRAPH-FOUNDATION-RELATIONSHIPS-V1, MATCH-INTELLIGENCE-EVIDENCE-V1, Team Center and Competition Center contracts.

Rule: each SHARK claim must expose source, evidence, freshness, quality and limitations. The platform is read-only in this phase: no generative AI, no Telegram sends, no Stripe calls, no DB writes, no provider calls and no automatic actions.
## USER-INTELLIGENCE-PLATFORM-V1

Contrato de perfil deportivo interno basado solo en senales first-party: actividad propia, favoritos, filtros, modulos usados, idioma/preferencia visual y contexto deportivo ya validado por Sports Core.

Guardrails:

- consentimiento explicito para aplicar personalizacion;
- exportacion de preferencias;
- reset de preferencias;
- borrado de perfil e historial de personalizacion;
- desactivacion completa;
- cero venta de datos;
- cero terceros;
- cero IA generativa;
- cero personalizacion automatica de Home en esta fase.
