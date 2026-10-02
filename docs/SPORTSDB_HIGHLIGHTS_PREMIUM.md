# TheSportsDB premium media — verified 2026-10-03

## Official API capabilities and limits

Sources: [API guide](https://www.thesportsdb.com/docs_api_guide),
[terms updated 2026-09-17](https://www.thesportsdb.com/docs_terms_of_use.php),
[official v2 highlight example](https://www.thesportsdb.com/api/v2/examples/lookup_event_youtube_highlights.json),
[official event response](https://www.thesportsdb.com/api/v1/json/123/lookupevent.php?id=441613).

* V1 `eventshighlights.php?d=YYYY-MM-DD&s=Soccer`, optionally `l=<league ID>`:
  YouTube highlight links by date. Documented premium response limit 50,
  free limit 2. A full 50-row result can truncate coverage; known league
  partitioning helps but does not establish worldwide completeness.
* V1 `lookupevent.php?id=<idEvent>` and V2 `lookup/event/<idEvent>` return
  event details. `strVideo` may be blank; `idEvent` is the provider identity.
* Premium V2 `lookup/event_highlights/<idEvent>` is documented (limit 1).
  Its official example uses the `lookup` envelope and includes `strVideo`,
  `strDescriptionEN`, `strResult`, event/team IDs, date and artwork fields.
  V2 requires `X-API-KEY`; V1 authenticates through the server-side URL.
* Related premium event resources include lineup, timeline, statistics,
  results and TV listings. Their existence does not imply data for every game.
* `strDescriptionEN` can describe a fixture before play; it is not a
  guaranteed postmatch editorial summary. `strResult` and scores are data,
  not an invented narrative. No automatic editorial summary is generated here.
* The guide lists Premium 100 requests/minute and Business 120. These are
  documentation limits, not verification of this account's purchased tier.
  No subscription, billing setting, key or account-wide quota was changed.

## Availability and rights

The API supplies links, not video files or guaranteed playback. The guide
explicitly warns of YouTube geoblocking. Missing, removed, private and
embedding-disabled videos remain possible. Payment provides API access;
the terms retain third-party rights requirements and require source credit.
Artwork licensing is separate and must not be inferred from the subscription.
The existing per-content review, channel, attribution and thumbnail checks
therefore remain active. Receiving a real URL does not automatically authorize
its public display. Pending review is reported separately from no stored link.

## Reused architecture and changes

Existing pipeline: `engines/sportsdb_highlights_engine.py` → persisted
`sportsdb_match_highlights`/`sportsdb_match_enrichment` → read-only
`engines/highlight_read_model.py` → match media, calendar/results badges,
`/resumenes`, highlight detail, Admin center and review.
Provider association uses a qualified SportsDB external ID and validates
the event context; the fallback requires an unambiguous dated team/league pair.

The current date feed remains the acquisition path. V2 per-event highlights
are documented for future targeted acquisition; this release does not add
a second worker or spend additional per-event calls merely to exercise V2.
Already fetched `sportsdb_event_profiles.raw_json` carrying `strVideo` now
feeds the same catalogue, with the feed taking precedence within a run.
Profile payloads never invent URLs or grant rights.

Successful feed responses, including empty results, are persisted by date,
sport and league for six hours. Expired responses are fetched again; force
bypasses this cache. Provider failures and malformed results are not cached.
The cache applies only to media metadata, never to live scores or live clocks.
Provider calls occur outside write transactions. Existing per-operation
12-call/time/item limits remain. Concurrent overlapping executions may still
fetch the same miss; this is not an account-wide quota limiter.

Each run persists external calls, persistent cache hits and profile links
reused. Admin reads these alongside last completion, status and errors, without
HTTP or schema mutations. Historic runs without these fields report unknown
instead of invented zero. Existing authorized client rendering and honest
empty/review/unavailable states are retained.

Schema additions are additive in the configured database. DB_PATH, users,
sessions, memberships, Stripe, Telegram transport/delivery, existing cron
schedule, Madrid timezone, secrets and paid plans are unchanged.
