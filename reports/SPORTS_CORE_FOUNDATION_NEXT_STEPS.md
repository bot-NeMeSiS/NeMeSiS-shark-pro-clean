# Sports Core Foundation Next Steps

## Immediate

1. Run full repository QA: py_compile, compileall, full pytest, Jinja, route/link audit, Sentinel, Secret/Privacy Guard and Browser QA.
2. Review Browser QA screenshots for Match Center, Live, Calendar, Picks and SHARK.
3. Confirm no runtime route exposes raw provider JSON or debug-only domain internals.

## Next Sports Core Sprint

Implement the next approved Match Center increment using the canonical domain model as the only input language.

## Team Center Foundation

Use Team Entity and Sports Graph relationships. Do not normalize team names again inside the center.

## Competition Center Foundation

Use Competition Entity and Sports Graph relationships. Do not merge competitions by display name.

## Player Center Foundation

Use Player Entity as partial-first. Missing photo, injury or position data must remain unavailable.

## Future Migration

Move provider adapters toward canonical output gradually while retaining legacy compatibility until consumer scans prove safe removal.

## Human Approval Required

- Any DB schema persistence for canonical entities.
- Any Telegram message generated from the new contract.
- Any provider call added to page render.
- Any removal of legacy adapters.
