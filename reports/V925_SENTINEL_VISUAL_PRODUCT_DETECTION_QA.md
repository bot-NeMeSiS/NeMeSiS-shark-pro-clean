# V925 Sentinel Visual Product Detection QA

## New product rules

Continuous Sentinel now reports `V925_REFERENCE_PRODUCT_RULES` for:

- one public hero;
- no excessive top gap;
- compact cards and readable values;
- admin/client navigation isolation;
- visible mojibake and broken copy;
- useful empty states;
- client/sports route 500s;
- cache-first sports rendering;
- missing Browser QA screenshots;
- sports data without an explicit source.

## Safe snapshot

`build_v925_visual_product_snapshot()` uses the Flask test client and static/runtime evidence. It does not mutate production data, call paid APIs, send Telegram or mark visual queue items resolved.

Browser QA remains required and `pixel_perfect_claim_allowed` remains false without valid screenshots.
