# NeMeSiS X Implementation Rules

## Executive Summary

**NeMeSiS X is frozen as strategic vision.** These rules define how future work may be converted into execution after `LRM-001`, not before it.

**The default state of every NeMeSiS X idea is design-only.** An idea becomes eligible for implementation only when it has evidence, dependencies, risk controls, roadmap priority and human approval.

---

## 1. Absolute Freeze Rules

Until `LRM-001` is officially completed:

- no NeMeSiS X feature implementation;
- no new sports modules;
- no new engines;
- no new APIs;
- no new routes;
- no Sports Core changes;
- no SHARK architecture changes;
- no Gateway source expansion;
- no production changes;
- no deploy;
- no push;
- no version change.

Allowed work:

- documentation;
- strategy;
- dependency mapping;
- risk analysis;
- read-only evidence gathering;
- QA and release gate certification;
- planning inside the Living Roadmap.

---

## 2. Promotion Rule: From Vision to LRM

An initiative can move from NeMeSiS X vision to LRM execution only when all conditions are true:

1. It has a unique LRM objective.
2. It states the user problem in plain language.
3. It identifies the existing canonical layer it reuses.
4. It explains why existing screens or flows cannot solve the need.
5. It defines required evidence.
6. It classifies dependencies as PASS, PARTIAL, BLOCKED or NOT_REQUIRED.
7. It has a privacy and legal position.
8. It has Browser QA, Sentinel, Privacy Guard and Secret Guard checks.
9. It has a rollback or stop condition.
10. It has explicit human approval.

---

## 3. Initiative Classification Rules

| Classification | Meaning | Can implement now? |
|---|---|---|
| READY_FOR_LRM | Can become a roadmap objective when current gate allows it | Only after `LRM-001` if implementation-related |
| NEEDS_REAL_USERS | Requires beta usage, feedback or behavior evidence | No |
| NEEDS_PRODUCTION | Requires production, Telegram, Stripe, logs or runtime evidence | No unless the task is certification |
| NEEDS_EXTERNAL_DATA | Requires source rights, licensing or provider evidence | No |
| LONG_TERM | Belongs to future strategic horizon | No |

---

## 4. Release Band Rules

### Release 1.x

Release 1.x may include:

- release certification;
- closed beta readiness;
- support and privacy clarity;
- payment safety;
- Telegram certification;
- operational reliability;
- UX polish based on QA;
- metrics needed to learn from beta.

Release 1.x may not include:

- new sports architecture;
- new data sources;
- AI assistant;
- international expansion;
- community launch;
- advanced picks expansion not backed by evidence.

### Release 2.x

Release 2.x may include:

- deeper sports experiences;
- entity center maturity;
- source-aware Live Center;
- SHARK distributed context;
- better sports discovery;
- Telegram preferences and premium value;
- responsible picks clarity.

Release 2.x requires:

- beta evidence;
- production stability;
- Gateway compliance;
- user privacy controls.

### Release 3.x

Release 3.x may include:

- controlled AI evaluation;
- community;
- internationalization;
- partner ecosystem;
- enterprise readiness;
- scale architecture;
- advanced operational automation.

Release 3.x requires:

- retention evidence;
- support maturity;
- legal review;
- cost and performance evidence;
- recovery and observability maturity.

---

## 5. Architecture Protection Rules

1. Do not create parallel sports data models.
2. Do not recalculate metrics inside screens when canonical contracts exist.
3. Do not create a new SHARK engine for a local screen.
4. Do not create Telegram formats outside the communication system.
5. Do not add providers outside the Gateway.
6. Do not store user intelligence without privacy controls.
7. Do not show technical states to customers when a human explanation is needed.
8. Do not hide limitations from customers.
9. Do not make admin actions destructive by default.
10. Do not ship without QA evidence.

---

## 6. Evidence Rules

Every future implementation brief must answer:

- What do we know?
- What do we not know?
- What evidence supports the change?
- What evidence is missing?
- What user behavior justifies it?
- What production signal justifies it?
- What legal or data-rights review is needed?
- How will we know it worked?
- What would make us reverse or stop?

No implementation can claim PASS by absence of errors. PASS requires positive evidence.

---

## 7. Human Approval Rules

Human approval is mandatory for:

- production changes;
- deploy;
- push;
- Telegram real sends;
- Stripe tests or payment changes;
- new data sources;
- privacy-impacting changes;
- betting-adjacent copy or bankroll changes;
- AI/generative behavior;
- security, auth, admin or cron changes;
- version changes.

---

## 8. Final Rule

NeMeSiS X should make the product more intelligent, not more chaotic.

If a proposed implementation adds surface area without improving clarity, evidence, responsibility, user control or commercial trust, it must remain out of the product.
