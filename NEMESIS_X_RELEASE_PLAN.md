# NeMeSiS X Release Plan

## Executive Summary

**NeMeSiS X is a three-year release direction, not a sprint backlog.** The plan separates what belongs to Release 1.x from what belongs to future NeMeSiS X phases.

**Release 1.x is about trust and commercialization.** It should close production gates, beta readiness, support, privacy, Telegram, Stripe and operational confidence.

**Release 2.x is about sports intelligence depth.** It should improve the existing sports experiences only after beta evidence shows where users need more context.

**Release 3.x is about scale and advanced intelligence.** It should consider controlled AI, community, internationalization and enterprise readiness only after product-market signals and operational maturity exist.

---

## 1. Release 1.x: Trust, Beta and Commercial Readiness

### Purpose

Turn NeMeSiS into a safe, understandable and commercially credible product.

### Eligible Initiatives

| Initiative | Status | Classification | Dependency |
|---|---|---|---|
| Close `LRM-001` | Active | READY_FOR_LRM | Current priority |
| Render/Cron/Master Tick certification | Required | READY_FOR_LRM | Production read-only evidence |
| Restore and backup confidence | Required | READY_FOR_LRM | Safe drill and policy |
| Telegram controlled certification | Required | NEEDS_PRODUCTION | One controlled test and observability |
| Stripe test certification | Required | NEEDS_PRODUCTION | Test mode and webhook evidence |
| Closed beta preparation | Blocked until gates | NEEDS_PRODUCTION | `LRM-001` |
| First-value onboarding validation | Design-ready | NEEDS_REAL_USERS | Closed beta |
| FREE/PRO/ELITE clarity | Design-ready | NEEDS_REAL_USERS | Beta and Stripe test |
| Support, FAQ, cancellation and privacy clarity | Ready | READY_FOR_LRM | Release readiness |
| Browser QA/Sentinel/Privacy as release gate | Ready | READY_FOR_LRM | QA discipline |

### Release 1.x Exit Criteria

- users can enter beta safely;
- production is observable;
- Telegram is proven under control;
- Stripe test mode is proven;
- restore has evidence;
- support is ready;
- no false promises are visible;
- first-value metrics are collected with consent;
- `LRM-001` is closed.

---

## 2. Release 2.x: Sports Intelligence Depth

### Purpose

Make NeMeSiS the best place to understand sports context, not just view results.

### Eligible Initiatives

| Initiative | Status | Classification | Dependency |
|---|---|---|---|
| Match Center maturity | Future | NEEDS_REAL_USERS | Beta usage and Match Intelligence evidence |
| Team Center maturity | Future | NEEDS_REAL_USERS | Entity-follow behavior |
| Competition Center maturity | Future | NEEDS_REAL_USERS | Competition-follow behavior |
| Player Center maturity | Future | NEEDS_REAL_USERS | Player usage evidence |
| Source-aware Live Center | Future | NEEDS_EXTERNAL_DATA | Gateway source compliance |
| Sports Graph discovery | Future | NEEDS_REAL_USERS | Search/navigation evidence |
| Distributed SHARK context | Future | NEEDS_REAL_USERS | SHARK comprehension evidence |
| Premium Telegram preferences | Future | NEEDS_PRODUCTION | Gate 3 PASS and beta feedback |
| Responsible picks methodology | Future | NEEDS_REAL_USERS | Track record, legal review and trust metrics |
| Bankroll education | Future | NEEDS_REAL_USERS | Legal review and responsible betting design |

### Release 2.x Exit Criteria

- users repeatedly return for context, not only scores;
- entity centers have measurable repeat usage;
- SHARK is understood and trusted;
- Telegram messages are perceived as useful;
- source quality and freshness are visible without overwhelming users;
- no new sports source bypasses Gateway compliance.

---

## 3. Release 3.x: Scale, Network and Advanced Intelligence

### Purpose

Turn NeMeSiS into a scalable sports intelligence operating system.

### Eligible Initiatives

| Initiative | Status | Classification | Dependency |
|---|---|---|---|
| Daily companion maturity | Future | NEEDS_REAL_USERS | Retention evidence |
| Community and user programs | Future | LONG_TERM | Support and moderation |
| Public methodology content | Future | LONG_TERM | Legal and editorial guardrails |
| Partner/affiliate ecosystem | Future | LONG_TERM | Commercial readiness and compliance |
| Internationalization | Future | LONG_TERM | Market/legal/source readiness |
| Controlled AI assistant | Future | LONG_TERM | Evidence graph, refusal policy, legal/privacy review |
| Enterprise readiness | Future | LONG_TERM | Operations, auditability and scale proof |
| Platform scale | Future | NEEDS_PRODUCTION | Real usage, cost and load metrics |

### Release 3.x Exit Criteria

- scale bottlenecks are measured and addressed;
- costs per user are visible;
- support and incident response are mature;
- AI, if pursued, is evidence-bound and controlled;
- international and partner expansion has rights and compliance evidence.

---

## 4. Not Before LRM-001

No Release 2.x or Release 3.x implementation may begin before `LRM-001` is completed.

Design-only work may continue if it:

- creates documentation only;
- does not change code;
- does not alter architecture;
- does not add routes, APIs or engines;
- does not change production;
- does not change version;
- does not create a workaround around release gates.

---

## 5. Release Governance

Before an initiative enters implementation, it must have:

1. LRM ID.
2. Release band.
3. User problem.
4. Evidence requirement.
5. Dependency status.
6. Risk classification.
7. QA plan.
8. Rollback or stop condition.
9. Human approval.

If any item is missing, the initiative remains design-only.
