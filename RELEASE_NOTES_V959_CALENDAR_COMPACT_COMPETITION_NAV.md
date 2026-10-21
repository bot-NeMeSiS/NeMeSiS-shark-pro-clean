# V959 — Compact calendar competition navigation

Calendar days with more than 12 competitions now show the six most relevant competition shortcuts first and place the remaining links inside a native, keyboard-accessible “show more” disclosure. Short lists keep their existing layout, and every real match and competition destination remains available without JavaScript. The compact navigation is also visible on mobile, where the previous stylesheet hid the competition shortcuts entirely.

No sports data, ranking, provider calls, permissions, persistence, or match cards were changed.

Validation: added template regressions for large and short competition lists, checked the generated CSS bundle, and ran the calendar presentation tests.
