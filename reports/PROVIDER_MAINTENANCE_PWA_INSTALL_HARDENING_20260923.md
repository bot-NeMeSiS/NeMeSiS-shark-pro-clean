# Provider Maintenance + PWA Install hardening · 23/09/2026

- Admin distinguishes configured, enabled, direct connection, plan/payment evidence and quota.
- Plan evidence older than 24h is shown as stale, never as a current paid-plan claim.
- Explicit one-call provider tests persist sanitized results so Admin keeps the latest evidence after refresh/restart.
- API-Football direct status can verify plan/active/end/quota. The Odds API verifies auth/quota but does not invent a paid-plan label. TheSportsDB verifies access only.
- Page render remains zero provider calls.
- /instalar, /install-app and /anadir-a-inicio provide a shareable install guide.
- The global install prompt uses the same official icon family as Founder Control.
- Manifest URL and dismissal state are keyed by app_icon_version so identity changes invalidate stale install metadata/prompts.
- Footer exposes “Instalar app” on public/client surfaces.
- No production providers were called by these changes.
