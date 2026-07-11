# V934 Odds Freshness QA

## Freshness gate

- Fresh: up to 15 minutes.
- Recorded: over 15 and up to 60 minutes.
- Stale: over 60 minutes.
- Missing: no complete real odd is available.

Only picks with a real match, market, selection and numeric odd pass normalization. Stale or incomplete values are never presented as fresh recommendations. The client receives plain-language freshness; exact provider/cache diagnostics remain admin-only.

Validated states: fresh, recorded, stale, missing and incomplete-pick rejection. No odds were fabricated.
