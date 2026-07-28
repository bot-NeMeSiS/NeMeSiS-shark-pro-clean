# Sports Core Foundation Next Steps

## Immediate

1. Run full repository QA: py_compile, compileall, full pytest, Jinja, route/link audit, Sentinel, Secret/Privacy Guard and Browser QA.
2. Review Browser QA screenshots for Match Center, Team Center, Competition Center, Live, Calendar, Picks and SHARK.
3. Confirm no runtime route exposes raw provider JSON or debug-only domain internals.

## Current Sports Core State

- Match Center 2.0: PASS local, not production certified in this sprint.
- Sports Knowledge Layer: PASS local.
- Sports Graph Foundation: PASS local.
- Team Center Premium Experience: PASS local.
- Competition Center Premium League Intelligence: PASS local.

## Next Sports Core Sprint

Implement Player Center only after Competition Center closure is accepted. It must consume Player Entity and Sports Graph relationships without creating a parallel model.

## Team Center Foundation

Use Team Entity and Sports Graph relationships. Do not normalize team names again inside the center.

## Competition Center Foundation

Implemented locally as Competition Center Premium League Intelligence. It consumes Competition Entity, Team Entity, Match Entity, Sports Knowledge and Sports Graph; it does not merge competitions by display name and does not invent standings.

## Player Center Foundation

Use Player Entity as partial-first. Missing photo, injury or position data must remain unavailable.

## Future Migration

Move provider adapters toward canonical output gradually while retaining legacy compatibility until consumer scans prove safe removal.

## Human Approval Required

- Any DB schema persistence for canonical entities.
- Any Telegram message generated from the new contract.
- Any provider call added to page render.
- Any removal of legacy adapters.
