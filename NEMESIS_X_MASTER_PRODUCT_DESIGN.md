# NeMeSiS X Master Product Design

## Official Vision Lock

Este documento define la visión estratégica de NeMeSiS para los próximos tres años.

No implica implementación inmediata.

Toda funcionalidad deberá justificarse mediante evidencia, uso real, métricas y priorización del roadmap.

Estado oficial: `VISION_LOCK`.

Objetivo LRM asociado: `LRM-002 - NEMESIS X`.

Prioridad operativa vigente: `LRM-001` continúa siendo la prioridad absoluta hasta completar los gates de Release 1.0 y beta cerrada.

Código autorizado: no.

Producción modificada: no.

Commit, push o deploy autorizados: no.

---

## Executive Summary

**NeMeSiS X is the three-year product design horizon for turning NeMeSiS into the most intelligent sports platform in its market.** It does not authorize implementation, new modules, new engines, new APIs, production changes, commits, pushes or deploys.

**The central bet is not more screens.** The central bet is a product that understands sport through real data, evidence, context, user intent, operational discipline and responsible decision support.

**NeMeSiS must not copy Flashscore, SofaScore, FotMob or any other app.** Those products solve discovery, scores and coverage well. NeMeSiS X must solve a different problem: helping a user understand what matters, why it matters, what changed, what evidence exists, what is missing and what action is reasonable now.

**The immediate governance remains unchanged.** `LRM-001` stays the active operational objective until Release 1.0 and closed beta gates are certified. NeMeSiS X is a strategic north star, not permission to skip release readiness.

---

## 1. Product Vision

### 1.1 The Three-Year Ambition

NeMeSiS X should become the platform a serious sports user opens when they want:

- to discover what matters today;
- to understand a match in seconds;
- to follow teams, competitions and players without losing context;
- to receive fewer but better alerts;
- to distinguish facts from interpretation;
- to see source, freshness, quality and limitations;
- to make responsible decisions, including the decision to wait;
- to trust that the company behind the product operates professionally.

The product should feel like a calm sports intelligence room: fast, clear, dense, evidence-first, beautiful and honest.

### 1.2 The Core Promise

NeMeSiS X does not promise outcomes. It promises better understanding.

The product promise is:

> Open NeMeSiS and understand the sports day faster, with more context and less noise than anywhere else.

### 1.3 What NeMeSiS X Must Become

NeMeSiS X must become:

- a real-time sports context platform;
- a personal sports command center;
- a transparent evidence layer;
- a responsible betting-adjacent intelligence product;
- a premium Telegram companion;
- a company operating system for product quality, release readiness and customer trust;
- a scalable platform that can grow without losing control.

### 1.4 What NeMeSiS X Must Never Become

NeMeSiS X must never become:

- a generic results app;
- a copied sports interface;
- a chatbot pretending to know everything;
- a prediction machine without evidence;
- a volume-based pick factory;
- a spam channel;
- a gambling-pressure product;
- a product that hides uncertainty;
- a product that ships features faster than it can certify them;
- a product that depends on unlicensed data or unclear rights.

---

## 2. Product Principles

### 2.1 Evidence Before Intelligence

No intelligence layer can speak before the evidence layer is clear. Every conclusion must know:

- what data produced it;
- when that data was updated;
- which source or contract supports it;
- what confidence it carries;
- what is missing.

### 2.2 Context Before Quantity

The product should not win by showing more numbers. It should win by making the right number obvious at the right moment.

### 2.3 Calm Before Urgency

NeMeSiS should reduce anxiety, not amplify it. Urgency is valid only when a real event, state change or user-configured alert justifies it.

### 2.4 Continuity Before Navigation

The user should never feel they are jumping between disconnected pages. Match, Team, Competition, Player, SHARK, Telegram and Action Platform must feel like one continuous sports memory.

### 2.5 Responsibility Before Monetization

Revenue matters, but not at the cost of trust. NeMeSiS must never force conversion through fear, opacity or unrealistic expectations.

### 2.6 Human Control Before Automation

Automation can observe, measure, detect, prioritize and propose. It must not silently decide, deploy, send risky messages, change money flows or invent evidence.

---

## 3. Future Architecture

### 3.1 Architectural North Star

NeMeSiS X should evolve into a layered sports intelligence platform:

```text
Licensed / approved sources
-> Sports Intelligence Gateway
-> Unified Sports Domain Model
-> Sports Knowledge Layer
-> Sports Graph
-> Match / Team / Competition / Player Intelligence
-> Decision Engine
-> SHARK Intelligence
-> User Intelligence
-> Action Platform
-> Telegram / Product UI / Company OS
-> QA / Sentinel / Executive Board
```

The architecture must remain evidence-first and contract-driven. No visible product layer should recalculate its own truth when a canonical layer exists.

### 3.2 Future Core Layers

| Layer | Future role | Product value | Guardrail |
|---|---|---|---|
| Sports Intelligence Gateway | Registry and compliance gate for every source | Safer coverage expansion | No source used before approval |
| Unified Sports Domain Model | Canonical representation of sports entities | One language across the app | No parallel entity models |
| Sports Knowledge Layer | Reusable context for teams, matches, competitions and seasons | Better explanations without duplication | Read-only, provenance required |
| Sports Graph | Relationship map between entities and evidence | Fluid navigation and discovery | No artificial relationships |
| Match Intelligence | Structured understanding of match state | Match Center becomes a real intelligence surface | No unsupported conclusions |
| SHARK Intelligence | Opinion-free sports criterion based on evidence | Differentiation and premium trust | SHARK must stay silent when evidence is weak |
| User Intelligence | Transparent personal sports profile | Relevance and continuity | Consent, deletion and opt-out |
| Decision Engine | Organizes what is known, unknown and changed | Prevents false certainty | Every answer needs limitations |
| Action Platform | Daily entry point and operational user memory | Retention and habit | Helps the user, never decides for them |
| Company OS | Product, operations, release and business control | Scaling the company | Read-only by default, human approval |

### 3.3 Future Experience Model

NeMeSiS X should be organized around experiences, not screens:

| Experience | User question | Future answer |
|---|---|---|
| Discover the day | What matters today? | Personalized sports briefing with evidence and freshness |
| Follow a match | What is happening and why? | Match Center with live story, timeline, context and confidence |
| Follow a team | What is the team becoming? | Team Center with form, schedule, rivals, strengths and uncertainty |
| Follow a competition | What is the season story? | Competition Center with table, objectives, phases and momentum |
| Follow a player | What is the player context? | Player Center with role, events, availability and team relation |
| Decide responsibly | Should I act, wait or ignore? | Decision Engine and SHARK explain evidence, risk and limits |
| Return later | What changed since I left? | Action Platform, Telegram and Watchlist summarize only meaningful change |
| Operate the company | Is the product safe to run? | Founder, Operations, Developer and Executive Board with evidence |

---

## 4. Three-Year Roadmap

### Year 1: Trust, Beta and Release Discipline

**Goal:** turn the existing product into a reliable commercial product with real users, support, operations and evidence.

Primary outcomes:

- close `LRM-001`;
- certify Render, Cron, Master Tick, Telegram, Stripe, persistence, restore and observability;
- launch a closed beta with measurable first value;
- validate whether users understand SHARK;
- validate whether Telegram feels useful rather than noisy;
- validate whether FREE, PRO and ELITE value is clear;
- reduce onboarding friction;
- build release habits before scaling.

What must not happen:

- do not expand sports scope before operations are certified;
- do not add unapproved data sources;
- do not sell promises that are not supported by evidence;
- do not overbuild AI before user behavior is understood.

### Year 2: Sports Intelligence Depth

**Goal:** make NeMeSiS meaningfully better than a generic sports app for understanding matches, teams, competitions and players.

Primary outcomes:

- deepen Match Center into the product reference surface;
- mature Team Center, Competition Center and Player Center through real usage;
- make Sports Graph central to navigation and discovery;
- build source-aware Live Center;
- make SHARK context available where it adds clarity;
- expand Telegram into a precise companion for meaningful changes;
- introduce richer sports coverage only through the Gateway and licensing/compliance process;
- evolve user profiles with transparent control.

What must not happen:

- do not imitate sports apps feature by feature;
- do not show more data without better hierarchy;
- do not present weak evidence as strong insight;
- do not turn Telegram into a volume channel.

### Year 3: Intelligent Sports Operating System

**Goal:** make NeMeSiS the daily sports intelligence layer for users and the operational system for the company.

Primary outcomes:

- SHARK becomes a distributed intelligence layer, not a single page;
- Decision Engine becomes the shared explanation contract across product, Telegram and admin;
- Action Platform becomes the user's daily sports command center;
- Company OS becomes the internal operating system for product, quality, support, risk and growth;
- controlled AI assistance can be evaluated only if evidence, privacy and legal guardrails are mature;
- platform scale becomes real: cost, latency, reliability, recovery and observability are measured continuously.

What must not happen:

- do not introduce AI that cannot cite evidence;
- do not automate financial or betting decisions;
- do not scale acquisition before support and reliability can hold;
- do not add integrations without compliance, monitoring and rollback.

---

## 5. Phased Product Plan

### Phase 0: Release Gate Completion

Status: current immediate constraint.

Purpose:

- finish production certification;
- unblock closed beta safely;
- avoid future product work before operational confidence exists.

Exit criteria:

- Git clean and aligned;
- Render PASS;
- Cron PASS;
- Master Tick resolved;
- restore drill certified;
- Telegram controlled certification PASS;
- Stripe test certification PASS;
- observability and logs accessible read-only;
- Privacy and Secret Guard PASS;
- Browser QA PASS;
- Sentinel PASS.

### Phase 1: Closed Beta Learning Loop

Purpose:

- learn from real users;
- measure first value;
- identify confusion and repeated use;
- validate premium willingness without pressure.

Key design questions:

- can a new user understand NeMeSiS in under one minute?
- does SHARK feel valuable or confusing?
- does Telegram create return behavior?
- which sports entities are followed repeatedly?
- what makes a user trust or distrust a pick?

### Phase 2: Release 1.0 Commercial Readiness

Purpose:

- convert beta evidence into a controlled commercial launch;
- clarify FREE, PRO and ELITE;
- make support, cancellation, privacy and responsible usage visible.

Key design questions:

- what exactly does PRO save the user?
- what exactly does ELITE deepen?
- what proof can be shown without overpromising?
- what must remain free to build trust?

### Phase 3: Sports Intelligence Expansion

Purpose:

- deepen the sports product around real user needs;
- improve entity centers and live experiences;
- connect discovery, understanding and return loops.

Key design questions:

- where does the user lose context?
- what information should be summarized versus opened on demand?
- what does SHARK add that raw data cannot?
- how does a user compare matches, teams and competitions without overload?

### Phase 4: Daily Sports Companion

Purpose:

- make NeMeSiS worth opening every day;
- reduce manual searching;
- provide briefings, recaps, watchlists and meaningful alerts.

Key design questions:

- what should the user see first at 9:00, 15:00 and 22:00?
- what deserves an alert?
- when should Telegram stay silent?
- how much personalization is useful before it feels invasive?

### Phase 5: Market Differentiation and Network Effects

Purpose:

- turn trust, intelligence and continuity into defensible product advantage;
- grow community, content, partnerships and deeper premium experiences responsibly.

Key design questions:

- what would make users recommend NeMeSiS?
- what insight cannot be found in generic sports apps?
- what expert workflows deserve ELITE?
- what public content can educate without copying sources?

### Phase 6: Scale Platform

Purpose:

- prepare the product and company for tens of thousands of users;
- make operations, cost, support and data compliance scalable.

Key design questions:

- what breaks first under load?
- which costs scale with usage?
- what must be asynchronous?
- what needs stronger storage or queueing?
- what can be automated safely?

---

## 6. Dependencies

### 6.1 Strategic Dependencies

| Dependency | Why it matters | Blocks |
|---|---|---|
| LRM-001 completion | Product cannot enter real beta with open operational gates | Closed beta, Release 1.0, public launch |
| Real user feedback | Future strategy must be based on behavior, not imagination | Year 2 prioritization |
| Source compliance | Sports intelligence requires legal and reliable data | Coverage expansion, deeper Live Center |
| Telegram certification | Premium communication depends on delivery trust | Alerts, briefings, recaps |
| Stripe certification | Monetization cannot scale without safe payments | PRO/ELITE launch |
| Restore and backups | User trust requires recoverability | Beta, scale, enterprise readiness |
| Observability | Scaling needs real diagnostics | Reliability, support, automation |
| Privacy controls | Personalization cannot grow without user control | User Intelligence, Action Platform |
| Responsible betting guardrails | Picks and bankroll create reputational/legal exposure | Commercial growth |

### 6.2 Product Dependencies

| Future capability | Required foundation |
|---|---|
| Better Live Center | Gateway health, Timeline events, freshness, source quality |
| Smarter SHARK | Decision Engine, evidence contracts, Sports Graph |
| Personalized Home | User Intelligence, consent, Action Platform |
| Premium Telegram | Telegram PASS, dedupe, preferences, message quality |
| Advanced picks | Track record, odds freshness, responsible bankroll, legal review |
| Community | Support operations, moderation rules, legal posture |
| AI assistant | Evidence graph, privacy policy, source attribution, refusal behavior |
| International expansion | localization, timezone model, rights and compliance per market |

---

## 7. Risks

### 7.1 Critical Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Launching before operational gates PASS | Users experience outages, broken payments or unreliable messaging | Keep `LRM-001` as active gate until certified |
| Unlicensed or unclear sports data | Legal exposure and forced removal of product value | Gateway approval before any new source |
| SHARK appearing to invent or predict without evidence | Trust collapse and regulatory/reputation risk | Evidence-first claims and silence when uncertain |
| Telegram becoming noisy | Users mute or leave premium channel | Dedupe, frequency caps, user preferences and value scoring |
| Payment/support mismatch | Users pay but do not receive clear value or help | Stripe test certification and support runbooks before sale |
| No restore confidence | Data loss risk | Isolated restore drills and backup policy before scale |

### 7.2 High Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Too many internal dashboards | Operators lose clarity | Executive Board must prioritize, not multiply panels |
| Feature expansion before beta learning | Work drifts away from user value | Closed beta metrics decide Year 2 sequence |
| Data transparency overwhelming users | Product feels technical | Client/admin separation and progressive disclosure |
| Mobile density becoming heavy | Product feels less native | Mobile-first QA and route-level density budgets |
| Cost growth through APIs and automation | Margin erosion | Gateway cost guardrails and rate budgets |

### 7.3 Medium Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Users compare only to score apps | Value proposition misunderstood | Position around context, not scores |
| Empty states feel like missing product | Lower trust | Honest empty states with next useful action |
| Overpersonalization | Privacy concern | Explicit opt-out, export and deletion |
| Community moderation load | Support burden | Start small with clear rules |

---

## 8. Opportunities

### 8.1 Product Opportunities

| Opportunity | Value for user | Value for business |
|---|---|---|
| Daily sports briefing | Saves time immediately | Creates habit and retention |
| Match context in seconds | Reduces need for multiple apps | Strong differentiation |
| Evidence-backed SHARK | Builds trust | Premium reason to pay |
| Transparent picks methodology | Reduces unrealistic expectations | Responsible monetization |
| Smart Telegram | Returns user to product at the right moment | Retention and premium value |
| Followable entities | Creates long-term user memory | Recurring engagement |
| Decision history | Helps users learn from their own behavior | Differentiated trust layer |

### 8.2 Business Opportunities

| Opportunity | Why it matters |
|---|---|
| Closed beta as evidence engine | Real users decide the roadmap |
| PRO as time-saving product | Easier value communication |
| ELITE as depth and control | Higher willingness to pay without overpromising |
| Partnerships after compliance | Safer growth channels |
| Public methodology content | Trust-building marketing without copying sources |
| Enterprise/investor readiness | Operational discipline increases company value |

### 8.3 Strategic Differentiation

NeMeSiS X can differentiate on five axes:

1. **Contextual intelligence:** not just what happened, but why it matters.
2. **Transparent evidence:** every claim has source, freshness, quality and limitations.
3. **Responsible decision support:** the product can recommend waiting.
4. **Personal continuity:** the app remembers the user's sports world with consent.
5. **Operational trust:** the company can prove product health, quality and release readiness.

---

## 9. Experience Design North Star

### 9.1 The Ideal First Minute

In the first minute, a new user should understand:

1. what NeMeSiS is;
2. what is worth looking at today;
3. how to open a match;
4. how SHARK helps;
5. how to follow a team or competition;
6. what is free;
7. why PRO or ELITE may matter later;
8. how NeMeSiS handles uncertainty.

### 9.2 The Ideal Daily Session

A returning user should be able to:

1. see what changed since last visit;
2. review favorite teams, competitions and matches;
3. open one relevant Match Center;
4. understand SHARK context;
5. decide to follow, ignore, wait or inspect deeper;
6. leave with confidence that nothing important was hidden.

### 9.3 The Ideal Premium Moment

A PRO or ELITE moment should feel like:

- time saved;
- uncertainty reduced;
- context clarified;
- risk made visible;
- evidence explained;
- control preserved.

It should never feel like:

- pressure;
- guaranteed profit;
- hidden free value;
- spam;
- artificial urgency.

---

## 10. Future Architecture Decisions

### 10.1 Product Surface Strategy

Future surfaces should be created only when they answer a distinct user job. If a new idea can be solved inside an existing surface, the existing surface should evolve.

Preferred evolution order:

1. improve Home as daily command point;
2. deepen entity centers;
3. connect entity centers through Sports Graph;
4. make SHARK contextual everywhere;
5. make Telegram a return channel;
6. make Company OS evidence-led;
7. introduce new surfaces only after repeated beta evidence.

### 10.2 Data Strategy

Future data expansion must pass:

1. source registration;
2. license/commercial-use check;
3. attribution requirement;
4. latency and freshness model;
5. quality scoring;
6. cost guardrail;
7. fallback behavior;
8. user-facing limitation copy;
9. rollback plan.

### 10.3 Intelligence Strategy

No future intelligence feature should output unsupported text. Every insight must be traceable to:

- source;
- entity;
- event;
- timestamp;
- confidence;
- missing evidence;
- affected user action.

Generative AI, if ever introduced, must be constrained by retrieval, citations, refusal behavior and human review.

### 10.4 Monetization Strategy

FREE should create trust.

PRO should save time.

ELITE should create depth and control.

No tier should manipulate, hide essential safety information or create pressure to bet.

---

## 11. Governance Model

### 11.1 What NeMeSiS X Authorizes

This document authorizes:

- strategic planning;
- future design decisions;
- product prioritization;
- risk framing;
- dependency mapping;
- long-term roadmap discussion.

### 11.2 What NeMeSiS X Does Not Authorize

This document does not authorize:

- implementation;
- version change;
- production change;
- deploy;
- push;
- new APIs;
- new engines;
- new sports modules;
- new data sources;
- real Telegram sends;
- Stripe tests;
- AI generation;
- skipping `LRM-001`.

### 11.3 Decision Rule

Before any future sprint begins, it must answer:

1. Which LRM objective does this close?
2. Which user problem does it solve?
3. What evidence justifies it?
4. Which canonical layer does it reuse?
5. What risk does it introduce?
6. How will Browser QA, Sentinel, Privacy and Secret Guard validate it?
7. What would make us stop?

---

## 12. Three-Year Success Measures

### Year 1 Success

NeMeSiS is ready when:

- closed beta users can use it for weeks;
- first value is clear;
- Telegram is trusted;
- payments are safe;
- support is operational;
- SHARK is understood;
- production gates are certified;
- product quality is maintained without heroics.

### Year 2 Success

NeMeSiS is winning when:

- users open it instead of generic score apps for context;
- entity centers become repeated-use destinations;
- Live Center explains change better than a raw timeline;
- SHARK becomes trusted because it knows when to be quiet;
- PRO retention is based on time saved and clarity.

### Year 3 Success

NeMeSiS becomes a category-defining platform when:

- sports intelligence is consistent across app, Telegram and company operations;
- users trust the product to show what is known and unknown;
- operations can scale to tens of thousands of users;
- revenue grows through trust, retention and responsible premium value;
- the company can defend its data, architecture, safety and product quality.

---

## 13. Final Strategic Position

NeMeSiS X should not be designed as a better scoreboard.

It should be designed as the sports intelligence layer between raw data and human judgment.

The winning product is not the one with the most information. It is the one that helps the user understand the right information fastest, trust it, act responsibly and come back tomorrow because the product made sport clearer.

Current mandatory next step remains:

> Finish `LRM-001` before starting any implementation from NeMeSiS X.



## Automation Phase 01 Status

Continuous Evolution OS queda scheduler-ready de forma local y segura.

Esto no autoriza nuevas funciones de producto ni activacion automatica en produccion. Cualquier ejecucion productiva recurrente debe mantenerse dentro de LRM-001 hasta cerrar Release 1.0 y requiere evidencia real de tres dias consecutivos sin intervencion humana.

Estado permitido: observe, analyze, simulate QA, compare, detect, remember, calibrate, prioritize, propose, prepare Codex brief y generate Founder Brief.

Estado prohibido: code change, commit, push, deploy, Telegram send, Stripe action, user mutation, membership change, price change, delete, secret change, production mutation y new source activation.
