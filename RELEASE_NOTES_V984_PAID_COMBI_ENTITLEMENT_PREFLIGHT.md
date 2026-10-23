# V984 — paid combinada access preflight

V984 checks a persisted account's combinada entitlement before resolving any submitted pick identifiers. FREE accounts receive the existing plan-required response immediately, and PRO accounts cannot use the preview path to retrieve ELITE-only selections.

The compatibility API continues to expose only the signed-in account's private saved drafts and plan-filtered eligible candidates. Regression coverage verifies that legacy global draft rows are not returned to customers.

This release changes no account plans, payment state, provider calls, odds, stored predictions, or production data. Combinadas remain previews; they do not place bets.
