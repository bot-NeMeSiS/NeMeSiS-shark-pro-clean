# V934 Client Reference QA

## Updated routes

- `/`: shared realtime summary and honest next refresh state.
- `/app`: realtime match/live/pick counts integrated into the sports dashboard.
- `/calendar`: complete matches only, grouped through the existing safe context.
- `/live`: confirmed scores, minutes and events only; safe empty alternative retained.
- `/picks`: complete picks only and visible odds freshness.
- Match detail: cache-only refresh context; provider calls removed from page rendering.

## Reference result

- Existing V933 navigation, card hierarchy, actions and premium empty states remain intact.
- Technical cache labels were removed from client copy in the second pass.
- The realtime bar uses one component and one endpoint per page.
- Local authenticated mock routes returned 200 with no overflow or auth redirect.
- A real match-detail comparison is pending because the isolated QA database contained no real match.

No invented data was introduced. Pixel-perfect claim allowed: false.
