# V941 / PR92 - read-only GET and Smoke repair

## Continuation 2026-09-27 - current active block

The owner now authorizes coherent commits and normal pushes within existing PR92
to recover CI, without merge, deployment, main changes or production actions.
The 2026-09-26 section below remains historical evidence, not current Git state.

- Actual remote base: 7fa66517f0970b91e375fc1be4bf2b20bea8d605, 19 commits newer than the previous block; PR92 OPEN / DRAFT / mergeable, origin/main unchanged.
- Current Smoke run 36274802578, job 108495355528, step 11 "Run standard full suite": 13 failures / 2772 passes. The fast regression gate and smoke script passed.
- New failures: three raw-Jinja fixtures omit the real CSRF context required by the new POST form; a legacy internal API test expects GET 403 instead of POST-only 405 plus POST 403. Other failures are the read/POST contract cases already corrected locally in the previous block.
- Preserved the previous 20-file source set and report in local commits, pinned by codex/pr92-readonly-preserved-20260927. Continued in the SAME worktree from the actual PR HEAD; no new clone or reconstruction.
- Reconciled commits: 55a26635 (read-only), 31d085b9 (contract coverage), 12b65b13 (PWA/browser). Kept remote Telegram state fields and all remote POST-only endpoints/forms; combined both sets of read-only regressions.
- Reproduced the four newly uncovered cases locally: data/local_dev/pr92-b547d083889647dd9e1d0afc12cd194c/result.xml, 4 FAIL.
- Fixed fixtures with the actual Flask security context and validated the emitted token; no production CSRF relaxation. GET and unauthorized POST are asserted separately.
- Related suite: data/local_dev/pr92-ffce04f01a0d4137b2ecb46839b0a00a/result.xml, 117 PASS / 0 FAIL / 0 ERROR / 0 SKIP; zero external network attempts.
- CI on reconciled 5c876fd6137a56a453f8287ab8cd996ed0de3649: QA PASS; standard suite 2802 PASS; LOCAL SAFE PASS. Smoke then exposed a separate Sentinel boundary failure: run 36275594352 / job 108497583554 / step 13, GET scan matched the dynamic issue-id route and returned 404 instead of action rejection. Deploy Guard still running. This is not all-green CI.
- Previous local preview PID 6856 stopped after exact process identity verification; the old preview URL must not be advertised as current.

### Follow-up: authenticated, plan-scoped SHARK reads

- Reproduced anonymous SHARK context access, global legacy profile disclosure and a real INSERT into shark_context_snapshots on GET. Before evidence: pr92-d8fe46aeb63a4a0d94484f66e25ddbac (6 failures), pr92-49cf4440a9eb403aa88877bbc8833449 (1 write regression), pr92-088fd73b86b8472d92744073bec21987 (3 privacy failures before stopping). All paths are under data/local_dev and use disposable SQLite only.
- Context and briefing now require authentication; both filter draft/premium data using the effective membership. Context no longer persists a snapshot. Explicit question POST retains persistence and usage controls.
- Profile/membership APIs and briefing project the current user's name and effective plan, never the shared legacy profile. Public membership catalogue remains available without personal data. No legacy data was deleted.
- Regression covers anonymous, FREE, PRO, ELITE, ADMIN and expired PRO; adversarial query parameters do not change entitlement. Both briefing collections include synthetic higher-tier and draft canaries. Read checks observe attempted DML as well as row snapshots, including SHARK snapshots/memory.
- Related tests: data/local_dev/pr92-2f23b88e756a4f7ab963d667f95da2a5/result.xml: 142 PASS / 0 FAIL / 0 ERROR / 0 SKIP. A prior command used an incorrect test filename and collected no tests; it is not a product failure or PASS.
- Local checks: data/local_dev/pr92-665829de66f4448199913f7467e2aabe/checks.json: compile PASS, 216 Jinja templates, Madrid winter/summer PASS, 1186 navigation links with zero broken/loops, 39 Sentinel routes with zero open findings. Secret Guard 1301 files / 0 findings; privacy 75 expected fixtures / 0 review or confirmed leaks. Zero external network attempts. These checks are not production certification.
- Current scope is app.py and tests/test_get_business_readonly_v941.py plus this living report. Follow-up CI is required on the committed SHA.

### Follow-up: current Smoke Sentinel route collision

- Reproduced locally in data/local_dev/pr92-4059973bb8404dfa91f0640b38b275d0/result.xml: GET /api/admin/sentinel/issues/scan returned 404 because Werkzeug selected /issues/<issue_id> when the concrete action was POST-only.
- The issue reader now rejects reserved action names with 405 and Allow: POST before reading issue storage. Existing POST decorators, admin guard, CSRF and LOCAL SAFE are unchanged.
- Tests assert GET/HEAD do not scan or read an action as an issue; existing IDs still read, unknown IDs remain 404, visitors/clients remain 403. LOCAL SAFE sync guards retain their separate 403 contract; the normal HTTP test asserts 405 for all three actions. No test was disabled or broadened to accept 404.
- data/local_dev/pr92-951abd7083ed4707ac799a5133c78a6e/result.xml: 14 PASS / 0 FAIL / 0 ERROR / 0 SKIP, zero external-network attempts. Exact-SHA CI remains required after push.

## Historical local close - 2026-09-26

Date: 2026-09-26 (Europe/Madrid)
Status: PARTIAL / LOCAL_ONLY / NOT_READY_TO_PUSH

## Revision and preservation

- Repository: bot-NeMeSiS/NeMeSiS-shark-pro-clean.
- Existing PR: #92, OPEN, DRAFT; no additional PR created.
- Remote branch: integration/admin-master-control-v941.
- Initial and final HEAD: 754448bf8c0887bed3f17bb1461fd9bc48c7561f.
- Tested candidate: that HEAD plus the 20 uncommitted source/test/tool files listed below.
- origin/main observed: 2b59d3fca4f2982652279004ecffc3ea56617807.
- Local main remains 454c3ca1abb79af6a8525f65daecc57c0958c0c1, last reflog change 2026-09-22. It was not aligned or changed.
- Official checkout remains on codex/admin-pc-master-v941 at ebefbe666bf4b18160c7135b6bd0751350aa5cf5, clean.
- The existing admin-master-integration checkout remains on local integration/admin-master-control-v941 at 2589c0df745042f180c2efaeb603919ebe1ede44. All 26 preexisting changed/untracked files were preserved by HEAD/status/SHA256 comparisons.
- Implementation uses a proper detached Git worktree at data/local_dev/pr92-readonly-repair inside the official repository. No other mission's changes were copied.
- No staging, commit, push, merge, deploy, remote write, production DB access, real Telegram, real payments or real provider calls.

Remote CI observed on 754448bf, NOT on this dirty candidate:
Smoke FAILURE; QA SUCCESS; Render Deploy Guard SUCCESS.
The red remote Smoke is not declared resolved by local evidence.

## Reproduced failures and minimal corrections

1. The two reported Smoke cases changed users.telegram_link_code and its expiry while rendering Telegram. The effective expired membership reader was not the writer. telegram_user_state now only reads an existing unexpired code. Code creation/renewal uses the existing explicit POST, with session and CSRF checks. GET on the regeneration endpoint is 405.
2. default_profile could insert a synthetic PRO profile and favorite teams during context construction. A missing legacy profile now returns a transient neutral FREE profile with no saved favorites. Existing persisted profiles are unchanged.
3. Payment readiness could create schema and upsert payment_readiness_daily during GET. Read paths now use a read-only SQLite connection and do not initialize schema; explicit POST persistence remains. Subscription summary and Stripe status read paths no longer call schema writers.
4. Two real browser links to AutoPilot timed out because GET ran diagnostics instead of reading stored evidence. Five AutoPilot readers now use persisted evidence without scanning. Explicit run is POST-only. The existing Incidences review UI remains the action entry. Unknown evaluation/alignment is not displayed as zero/success; recorded evidence is not current certification.
5. A rejected async PWA prompt escaped the error state. Awaiting prompt() catches that rejection. Accepted remains different from installed; appinstalled is required to confirm installation.

No new scheduler, no recurring worker, no production configuration changes.
The protected daily expiry owner remains v818_daily_close_previous_day -> expire_user_memberships_if_needed.
Spanish labels, SHARK authentication/limits/CSRF, and legacy schedulers disabled by default remain covered by existing tests.

## Regression contract

- GET business tables: exact row snapshots plus SQLite authorizer observation of attempted writes, without suppressing them.
- Watched tables: users, matches, picks, favorites, telegram_queue, subscription_accounts, stripe_subscriptions, revenue_daily_metrics, client_profiles, payment_readiness_daily, settings, telegram_subscribers, payment_webhook_events, subscription_events.
- Canonical client pages tested for FREE/PRO/ELITE; canonical admin pages tested with isolated admin identity.
- Telegram missing/expired/valid/already-linked states, repeated reads, explicit regeneration, CSRF rejection and user isolation.
- Cold payment/subscription/Stripe reads create no tables; explicit payment snapshot persistence remains tested.
- AutoPilot reads do not execute diagnostics or rewrite memory. Stored zero is retained; absent evidence is not zero. Run checks method/admin/CSRF.
- Existing tests expecting GET expiry persistence, GET SHARK submission or secret-in-query GET cron execution were brought into line with the current explicit POST/header/CSRF contract. Positive and negative assertions remain.
- Windows WebP fixture MIME was corrected to the generated media type. Cache security expectations were not weakened.
- Browser tests use the already installed Chromium through NEMESIS_QA_CHROMIUM. No browser/dependency installer was run.
- The two Gunicorn cases were not skipped, suppressed or reclassified as PASS in JUnit.

## Final validation

Standard suite: 2791 total, 2789 PASS, 2 FAIL in JUnit, 0 ERROR, 0 SKIP; 507.146 seconds.
Both failures are ENVIRONMENT_BLOCKED / NOT_CERTIFIED:
- tests/test_server_queue_isolation.py::test_ordinary_navigation_order_during_synthetic_sports_task[serial-gunicorn]
- tests/test_server_queue_isolation.py::test_ordinary_navigation_order_during_synthetic_sports_task[concurrent-gunicorn]

Both stop while importing Gunicorn because Windows has no fcntl. WSL is not installed; no Linux environment was installed or system policy changed. This is not a global suite PASS.

LOCAL SAFE split: 315 PASS, 0 FAIL/ERROR/SKIP.
Sentinel/project-control boundary split: 18 PASS, 0 FAIL/ERROR/SKIP.
Combined disjoint pytest groups: 3124 total, 3122 PASS, 2 environment-blocked failures, 0 ERROR/SKIP. Focal reruns are not added again.

Requested focal files in the final standard suite:
- GET business read-only: 19/19.
- Revenue read-only: 6/6.
- Subscription/revenue truth: 5/5.
- SHARK membership limits: 10/10.
- Automation schedule minimal: 6/6.
- Product language: 19/19.
- Privacy classification: 2/2.
- Admin browser: 100/100 in its LOCAL SAFE split, including three new PWA cases.

Real Flask + Chromium matrix: 552/552 checks.
- 87 direct screens: 9 client surfaces x 3 plans x 2 viewports, 15 admin areas x 2 viewports, 3 public surfaces.
- 465 deduplicated internal link clicks.
- Viewports 390x844 and 1440x900.
- Zero failed checks, page errors, relevant console errors or horizontal overflows.
- Temporary SQLite, synthetic local sessions, external browser resources blocked.
- No dangerous form actions were executed by this navigation matrix.
- Service workers blocked for this matrix; native Chrome/Edge installed-PWA behavior is NOT_CERTIFIED.
- Synthetic browser install events verify the JS state machine, not an actual OS installation.

Other checks:
- py_compile / compileall app.py, engines, tools, automation_workforce: PASS.
- Jinja: 216 templates parsed.
- Madrid winter/summer checks: PASS.
- Navigation Integrity: 1185 links, 0 broken links, 0 loops, 0 statically unrecognized button actions. 278 static warnings remain; not a certification of every dynamic action.
- Route/import audit: PASS; 26 smoke routes, 0 unsafe responses in that controlled audit.
- Continuous Sentinel: 39 routes, 0 open/critical findings, completed_diagnostic_only.
- Secret Guard: 1300 source files initially, 1301 in the final recheck including this report; 0 findings, values not printed.
- Privacy: 0 confirmed secrets, 0 secret/privacy review candidates, 75 EXPECTED_FIXTURE findings.
- Final validation runners recorded 0 blocked external-network attempts.
- git diff --check: PASS.

## Evidence (paths relative to this worktree)

- Initial reproduced Smoke: data/local_dev/candidate-8ac780dd8e584202aab2f600e49b765d/result.xml.
- Final standard suite: data/local_dev/pr92-8fa7fa8a4f324db4b7768cfea48f82cc/result.xml.
- Final browser report: data/local_dev/pr92-a95505a073754cfd833f906b4023998c/browser.json.
- Final browser screenshots: data/local_dev/pr92-a95505a073754cfd833f906b4023998c/browser/verified/.
- Initial browser failures: data/local_dev/pr92-b64f58d1b5524220b88fd68416abbdf2/browser/failures/.
- Compile, Jinja, routes, Madrid, privacy, secrets, Sentinel: data/local_dev/pr92-4f57849b0d0d4283ad3b118e7f66a9b6/checks.json.
- Navigation warning details: data/local_dev/pr92-4f57849b0d0d4283ad3b118e7f66a9b6/navigation.json.
- LOCAL SAFE results (each contains result.xml):
  candidate-6831361e7cff431f980b3b838c8f60fd (10);
  candidate-5b8f1fdf5b3c42c3afb6626257344881 (11);
  candidate-3079a63736784f328810f40d17e35500 (1);
  candidate-5b46cc99ceea42b58160586d35862c0b (13);
  candidate-6f7931fe7a704614a343d6a362957e58 (106);
  candidate-5716e1d2daf645a5a1017d6fc0784b41 (100);
  candidate-6c9f59d94c164facb267fa776a7c1031 (74).
- Boundary results (each under data/local_dev with result.xml):
  pr92-df9eeaf0a6b349ec9c1d53d246063f06 (8);
  pr92-a1697cffdc1445109e689c8af68d2fe1 (9);
  pr92-bc85321a17df4d1e8b16393926b942e1 (1).

QA databases, generated logs, screenshots and ephemeral launchers remain ignored local evidence, not release inputs.
Only this new worktree's own generated data/runtime/not_found_events.json diff was reversed after a byte-identical copy was preserved at data/local_dev/pr92-4f57849b0d0d4283ad3b118e7f66a9b6/not_found_events_qa.json.
Temporary diagnosis instrumentation was removed; permanent negative regression tests remain.

## Local preview and limits

An isolated preview was started on 127.0.0.1:54919, without scheduler or worker execution.
GET /local-safe/status returned 200. /app returned the expected login redirect and then 200 /cliente-login.
Local entry tokens are not included in this report. Browser auto-opening was blocked by the execution policy and was not bypassed.
The attempted nonexistent /api/local-safe/status route hit the existing write boundary through its 404 logger; the valid route is /local-safe/status. No protection was disabled to permit that log write.
The server is loopback-only, separate from existing desktop launchers and production.

This does not certify production, real payments, Telegram delivery, a native mobile device, installed PWA behavior or all historical navigation warnings.

## Publication gate and exact resumption

NO_COMMIT / NO_PUSH / NO_MERGE / NO_DEPLOY.
The user's condition was all gates green before committing/pushing. The two Linux-only cases remain unverified; no exception was assumed.

Next: run the two preserved Gunicorn cases and the complete required pipeline in an authorized Linux environment on this exact source set. A push merely to obtain CI needs explicit authorization to relax the all-green-before-push condition; it was not attempted.
When those gates and the final exact revision are green, reconcile without overwriting the stale dirty PR92 checkout, then commit selectively and push normally only to the existing PR92 branch. No new PR, merge or deploy is authorized.
Keep all 26 unrelated preexisting changes and main untouched.

## Source fingerprint and modified-file scope

20 intentional source/test/tool files: 7 product, 11 tests, 2 QA tools. This report is the only additional documentation file.
SHA256 of UTF-8, no BOM, rows in the following order, each "path<TAB>sha256", joined with LF and no trailing LF:
a8684602a2964afed0a9fa676fdcb1be688fa8e01a82a61a1240a241686f098a

```text
app.py	c1bfd658078069f3a903b782cce89b980c5e597675473ef8541f935fab2e6289
engines/payment_readiness_engine.py	07214d7b12b9e841d7d852f96e3252fad2581ca90a1632042d3bcf1d6b0ce8d1
engines/sentinel_autopilot_engine.py	379c2f67d72c87b49a08b9f045bb8ee8dba620cac339319b251018033cc73665
engines/stripe_payments_engine.py	84fa7014e9d5d74d1b3b7a594aaa9441e39628fbee54d8c029b8c2def94ffa2b
engines/subscription_control_engine.py	b76b20c2457dabbd9ee464d1691699a771945801bc3d70e45ecb520b801a6744
static/pwa-install.js	3198ef386f96ea7aff1d64cdfb5e4d24529795b77b2b2e31346ef5323dc3577a
templates/admin_sentinel_autopilot.html	b7788a144e5536fad33e1c6fa508cc1e09d5323af7409b9f034c7bb3e0eef441
tests/test_admin_master_browser.py	558c191f6f2fa732f1ffe7fdadef3e898b19e28cd1f41d2da454df550a97aad7
tests/test_consolidated_visual_review.py	3fbb54145501bfb018c9a8b45b0495d92e5e8e1144ba827dda906d49bc9cb87b
tests/test_coord_sports_evidence.py	7992a4b8829e78d78f7cccd77ac72b1a023c9e59f0e61e5e424c07e3801bbde9
tests/test_dashboard_runtime_sports_diagnostics_repair.py	ee0729d31bf6aa8b5bff5d5e61f0a26b3c79b638569bb07de19b36d338af4563
tests/test_decorative_cache_browser.py	9df2de3867a974197a831217f381747752abeb9f409a11db9f90b6e72c281c76
tests/test_get_business_readonly_v941.py	9e69df6b15ec0dffc5c5426647428be7625a74cca80fa57d44ed1e9743333052
tests/test_platform_video_customer_experience.py	f46866f0fd55a78d39914e719b6ef5ec61d6bf0863b8fb726e0a4ce060507eb5
tests/test_revenue_readonly_safety.py	9177215c183dbec06717352121bb6f080358cd2f5412e29bc9fe785d31f249cc
tests/test_server_queue_isolation.py	5d5d7092b2ca0a8150812e246a1bead66c2bd6a9a99a340f729fe2a9c8a91b1b
tests/test_sports_data_pipeline_reality.py	53afee72e6f890f3a5c9c59902697f284085c07b1f6a73ea695071836a019b27
tests/test_v716_release_validation.py	76377bcd514a423bc8cc8c6a325fb551666d6cf3d92bebd7829a0a085e3972c8
tools/check_v888_sentinel_autopilot.py	653119c40e11c211a41bb445ef490737fbddd4aa75821046bf87fa8f53d83965
tools/run_v929_click_navigation_qa.py	f6b5c43c9155e8e25f0a78fccb99dc3d775d565b419e8e98a61a565c172346a6
```
