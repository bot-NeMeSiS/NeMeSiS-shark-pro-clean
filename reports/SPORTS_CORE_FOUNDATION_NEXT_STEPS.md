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
- Competition Center Premium League Intelligence: PASS local.`r`n- SHARK Intelligence Platform: PASS local; centro trazable sin IA generativa, sin Telegram, sin Stripe y sin llamadas externas.

## Next Sports Core Sprint

Implement Player Center only after SHARK Intelligence Platform closure is accepted. It must consume Player Entity and Sports Graph relationships without creating a parallel model.

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

## SHARK Intelligence Foundation

Implemented locally as SHARK Intelligence Platform. It consumes Sports Core, Sports Knowledge, Sports Graph, Match Intelligence, Team Center and Competition Center. It must not recalculate context, call providers, use generative AI, send Telegram, mutate picks or invent facts.
## User Intelligence Platform

Estado: PASS local pendiente de cierre Git.

La plataforma de inteligencia de usuario queda preparada para entender uso propio de NeMeSiS con consentimiento y control del usuario. El siguiente paso operativo es cierre Git controlado del sprint actual antes de iniciar Player Center u otro modulo visible.
