# V925 Home Reference Rebuild QA

## Result

- One public hero only: `NeMeSiS SHARK PRO`.
- The historical secondary V783 hero is no longer rendered.
- The first viewport contains the product identity, current safe state and direct actions.
- Public navigation now leads to Partidos, Directo, Picks, Planes, login and registration.
- Sections are compact: today/status, product capabilities, plans and trust.
- Plan prices are only shown when configured; otherwise the page says configuration is pending.
- No fabricated matches, picks, odds, ROI or usage metrics were introduced.

## Visual QA

Local desktop and mobile browser smoke showed a single hero, no horizontal body overflow and useful content above the fold. The public floating SHARK control was removed from the unauthenticated shell so it cannot obscure cards.

This is a strong reference-based rebuild, not a pixel-perfect certification. Screenshot artifacts must still be generated and imported by the Browser QA pipeline.
