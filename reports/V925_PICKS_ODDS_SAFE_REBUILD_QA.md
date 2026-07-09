# V925 Picks and Odds Safe Rebuild QA

## Gate

`get_safe_picks_context()` only exposes a pick when selection, market and real odds are present. `get_safe_odds_context()` is derived from those accepted picks.

Blocked or incomplete entries are not promoted as premium picks. The safe state explains that it is better to publish nothing than a pick without the required real fields.

## UI result

- Compact premium pick cards and market/status chips.
- Visible source and safety state.
- Risk/reason content only when supplied by real data.
- Telegram/plan actions do not promise unavailable picks.

V925 does not invent odds, selection, market, stake, confidence, ROI or a reason. No pick is sent to Telegram during QA.
