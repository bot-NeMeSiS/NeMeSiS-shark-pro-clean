# NeMeSiS Sports Media & Editorial Rights Policy

## Decision

NeMeSiS treats provider discovery and client publication as separate decisions.
A URL returned by an API is metadata, not proof of commercial display rights.
When the evidence is incomplete, the content is hidden and the state is
`REVIEW_REQUIRED` or `BLOCKED`.

This policy is an engineering and editorial control. It is not legal advice and
does not replace a current review of provider terms, competition rights or the
law applicable to each country and channel.

## Canonical Decisions

| Decision | Client use |
|---|---|
| `OFFICIAL_EMBED` | Embed only after official-source, channel and attribution checks pass. |
| `LICENSED_PROVIDER` | Display according to the documented provider licence and allowed channels. |
| `AUTHORIZED_LINK` | Link to the official/authorized destination; do not embed or rehost. |
| `OWN_GENERATED` | Display only when every input asset is owned or separately authorized. |
| `REVIEW_REQUIRED` | Do not display to clients. Preserve metadata for human review. |
| `BLOCKED` | Do not display, link, embed, download, cache or publish. |

`UNKNOWN_RIGHTS` always resolves to `REVIEW_REQUIRED` and is not client-visible.

## Required Metadata

Every client-visible media asset must retain:

- source and original URL;
- rights status and commercial-use status;
- allowed channel(s);
- attribution text and whether it is required;
- last rights verification date;
- official-source verification where applicable;
- known geographic restriction state;
- evidence origin: `REAL_PRODUCTION_OBSERVATION`, `LOCAL_QA` or `SIMULATED_TEST`.

Rights for a video and its thumbnail are evaluated separately.

## Content Rules

### Logos and crests

- Use only through an approved source and for the channels permitted by its
  contract and by the relevant rights holder.
- Do not assume that technical API access grants trademark or commercial reuse.
- If the source or channel authorization is unclear, use the local neutral crest
  fallback.

### Player photos

- A returned photo URL is not sufficient evidence.
- `OWNED`, `LICENSED`, `PROVIDER_ALLOWED`, `OPEN_LICENSE_ALLOWED` and
  `ATTRIBUTION_REQUIRED` may be shown only when commercial use and the `APP`
  channel are also allowed.
- Missing rights, missing mandatory attribution or a disallowed channel uses the
  NeMeSiS initials/silhouette fallback.

### Videos and highlights

- Never download, rehost, strip branding or search for unofficial streams.
- Prefer official privacy-enhanced embeds when embedding is explicitly allowed.
- If embedding is not allowed or a known geo restriction applies, use an
  `AUTHORIZED_LINK` when linking remains permitted.
- Hide broken, unknown-rights and unverified videos. Do not render an empty tab.
- Provider synchronization stores metadata for review; it does not approve
  publication.

### Thumbnails

- Evaluate independently from the video.
- Unknown or blocked thumbnails are hidden even when the video link is allowed.
- Do not derive, capture or mirror a frame unless that use is separately allowed.

### Statistics, lineups and event data

- Display only data supplied under an approved provider contract or generated
  from NeMeSiS-owned facts.
- Preserve source, freshness and limitations.
- Do not resell a provider dataset or expose a bulk substitute for its service.

### Deterministic summaries

- Facts may come only from confirmed score, events, statistics, lineups,
  standings/context and SHARK evidence.
- No generative AI fills gaps. Unsupported claims are blocked.
- Editorial wording created by NeMeSiS does not transfer rights in underlying
  footage, photos, logos or third-party data.

### Social and commercial publication

- App display does not automatically authorize social publishing, paid ads,
  Telegram commercial sends or redistribution.
- Each channel needs an explicit allowed-channel decision and human approval.
- Never publish third-party footage or player imagery from an unknown licence.

## Current Provider Interpretation

### TheSportsDB

Official documentation exposes event highlight lookups and YouTube links, but
the current NeMeSiS plan/capability is not observable from the repository. The
provider terms also state that third-party content requires permission or another
legal basis. Therefore discovered URLs remain `REVIEW_REQUIRED` until the source,
commercial use, channel and attribution are verified.

Sources reviewed 2026-08-30:

- https://www.thesportsdb.com/documentation
- https://www.thesportsdb.com/docs_api_guide
- https://www.thesportsdb.com/docs_api
- https://www.thesportsdb.com/docs_terms_of_use.php

### API-Sports / API-Football

The official capability page documents fixtures, events, lineups, statistics,
players, standings and odds, with coverage varying by competition. Its terms say
that logos and images are for identification and may require additional
authorization. NeMeSiS therefore treats data capability and media rights as
separate gates.

Sources reviewed 2026-08-30:

- https://api-sports.io/sports/football
- https://api-sports.io/terms

### The Odds API

Use is limited to approved odds consumption inside the product. NeMeSiS does not
resell or expose the feed as a standalone dataset.

Sources reviewed 2026-08-30:

- https://the-odds-api.com/liveapi/guides/v4/index.html
- https://the-odds-api.com/terms-and-conditions.html

## Future Own-Video Gate

Own video generation remains `LATER`. Before implementation, the founder must
approve a documented cost and rights gate covering rendering, object storage,
CDN, voice, music, volume, retention and every visual input. Broadcast footage
is never an implicit input.

## Enforcement

- Canonical rights gate: `engines/content_rights_engine.py`.
- Match video classification: `engines/video_highlights_engine.py`.
- Persisted provider metadata: `engines/sportsdb_highlights_engine.py`.
- Automated checks: `sports_knowledge_qa`, `summary_truth_qa` and
  `media_rights_qa`.
- Human founder review remains the final authority over publication decisions.

