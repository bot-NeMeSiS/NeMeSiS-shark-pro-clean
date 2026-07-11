# V934 Browser Reference Comparison

- Version: `V934_REFERENCE_EXACTNESS_REALTIME_SPORTS_PRODUCTION_PERFECTION_FINAL`
- Canonical references: 16.
- Final evidence: 231 route/viewport combinations.
- Total captures generated: 561.
- Desktop evidence: 132 captures from `reports/V934_browser_qa_second`.
- Mobile evidence: 99 captures from `reports/V934_browser_qa_mobile_final`.
- Routes per final matrix: 33.
- Capture errors: 0.
- Authentication redirects: 0.
- Horizontal overflow: 0.

## Gap matrix

| Area | Before | After | Result |
| --- | ---: | ---: | --- |
| Correctable MAJOR | 0 | 0 | MATCH/MINOR only |
| Correctable MEDIUM | 2 | 0 | Corrected in second pass |
| Real match detail | 1 blocked | 1 blocked | BLOCKED_BY_REAL_DATA |
| Production authentication | Pending | Pending | BLOCKED_BY_AUTH |

The final desktop set uses 1366x768, 1440x900, 1600x900 and 1920x1080. The final mobile set uses 360x800, 390x844 and 430x932.

No pixel-perfect claim is made without Damian's human review and authenticated Render captures.
