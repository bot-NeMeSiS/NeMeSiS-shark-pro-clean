# Sports Core Migration And Compatibility

## Compatibility Kept

- Existing routes remain unchanged.
- MatchContext still exposes legacy display fields.
- Live Story still exposes `timeline`, `cycles`, `key_events` and safe messages.
- Match Intelligence still exposes MATCH-INTELLIGENCE-EVIDENCE-V1.
- SHARK still consumes the same Match Intelligence snapshot.
- Telegram remains read-only for this integration.

## New Canonical Layer

The canonical model is additive:

- MatchContext.domain_model
- MatchContext.sports_graph
- MatchContext.telegram_readonly_contract
- Match Intelligence domain_model metadata
- Live Story canonical_timeline

## Temporary Legacy Areas

- API-Football cache tables and mirror-to-matches behavior remain legacy provider sync infrastructure.
- Existing UI templates still render legacy fields where stable.
- Product modules that are not Sports Core centers may still use older helper names.

## Removal Policy

No duplicate helper or legacy structure should be removed until:

1. consumer search finds no active use;
2. a canonical replacement exists;
3. tests cover the replacement;
4. Browser QA and Sentinel remain clean.

No files were removed in this sprint.
