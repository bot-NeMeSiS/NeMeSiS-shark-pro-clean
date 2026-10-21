# V960 — Real competition badges in the calendar

Calendar competition headings now use the same safe, read-only badge sources as the Home screen. They prefer a validated real badge already present in a fixture, then look up an unambiguous country-scoped SportsDB badge through the existing asset endpoint. When no real badge exists, the existing local initials fallback remains visible; no image is invented, downloaded, or written to the database.

The calendar grouping reuses a real badge found on any fixture in the competition group, including saved provider payloads, instead of relying only on the first fixture's normalized fields. Asset lookup stays lazy in the browser and does not call a sports provider.
