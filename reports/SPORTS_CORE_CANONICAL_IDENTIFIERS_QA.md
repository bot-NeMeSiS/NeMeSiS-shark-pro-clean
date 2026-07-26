# Sports Core Canonical Identifiers QA

## Strategy

Priority order:

1. Existing explicit canonical id.
2. Namespaced provider id.
3. Explicit verified mapping.
4. Stable fallback key documented as partial.
5. Unresolved state when identity is unsafe.

## Namespaces

Examples:

- api_football:match:4242
- api_football:team:10
- api_football:competition:140
- api_football:event:goal-1
- odds_api:event:abc123

## Collision Protection

The model does not merge two entities only because names look similar. If multiple provider identifiers exist without a verified mapping, identity_state becomes REQUIRES_REVIEW and collision_risk becomes medium.

## QA Covered

- Provider id generates canonical id.
- Fallback id is partial, not official.
- Ambiguous provider ids do not auto-merge.
- Competition names from different providers remain separate unless mapped.
- Event ids and fact signatures dedupe duplicate events safely.

## Limitation

No persistent cross-provider mapping table was created in this sprint. That remains a future approved migration step.
