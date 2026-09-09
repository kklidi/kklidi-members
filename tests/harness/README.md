# Synthetic WordPress behavior harness

Current scope: **the 24 Phase 0 MVP behavior contracts in a disposable synthetic WordPress**. It keeps a separate Core baseline, runs the production Members runtime, and copies the pinned local device-limit 1.1.3 reference into the temporary site for its real PHP hooks. Woo/LMS ownership tests in the disposable runner use synthetic domain rows; KBoard is covered only by the removal-period compatibility smoke/no-fatal contract. A separate fixed MAMP fixture has passed the actual LMS stack, while the complete Woo browser flow remains a deployment gate.

## Run

Requirements: Python 3.12+, PHP with mysqli, native MySQL 5.7 binaries. This first adapter was verified on Windows with Python 3.12.14, PHP 8.3.1 and MySQL 5.7.24. These are harness prerequisites, **not the product's minimum supported versions**. WordPress 7.1/en_US is pinned in `wordpress.lock.json`.

From the project root, using the path to your Python executable:

```powershell
& $Python -m unittest discover -s tests/harness -p test_runner.py -v
& $Python tests/harness/run.py --prepare
& $Python tests/harness/run.py --php 'C:/MAMP/bin/php/php8.3.1/php.exe' --mysqld 'C:/MAMP/bin/mysql/bin/mysqld.exe'
```

Set `$Python` to an installed Python 3.12+ executable first. On this workstation the available executable is `C:/Users/C/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`. PHP/MySQL paths above are the runner defaults. It reads those **binaries only**; it does not load their MAMP configuration or connect to an existing MAMP database.

`--prepare` downloads the two exact official dependencies into `.harness/cache`; it is the only step requiring internet. Both SHA-256 pins and all 3,782 official Core file checksums are checked before execution. A missing or changed dependency fails closed. The behavior run uses the cache offline. Update pins only through a reviewed dependency update, not in response to a mismatch.

The real device-limit contract is pinned to the read-only fixture at
`C:/MAMP/htdocs/kklidi-members-mamp-sandbox/wp-content/plugins/kklidi-device-limit`.
The runner requires version 1.1.3 and manifest SHA-256
`2549b2ecf89008d5719526882c82a46c1978f129ce9225f41d446544db935168` before copying it.
The `ns_0727` development site may contain a newer device-limit build and is not a valid
source for this MVP contract.

Sources: [WordPress release archive](https://wordpress.org/download/releases/) and [official Core checksum mechanism](https://developer.wordpress.org/reference/functions/get_core_checksums/). Upstream MD5 file checksums are used for consistency with WordPress; local SHA-256 pins additionally bind the exact downloaded archive and manifest.

## What executes

1. Create a new owned OS temporary directory and initialize a fresh MySQL datadir using `--no-defaults`. Launch only hidden child processes, bind to `127.0.0.1` on generated high ports, verify `@@datadir` and the ownership marker **before database writes**, then provision a schema-scoped WordPress DB user with a per-run password.
2. Extract verified Core twice into fresh document roots. Install independent sites under `wp_` and a random `kkh_<run>_` prefix in that disposable DB. Each has exactly three synthetic users: installer admin and two subscribers, one with email=user_login and one with a separate username. All email addresses use `example.invalid`.
3. An explicitly guarded, test-only MU observer sinks mail, blocks WordPress HTTP API egress and records only event type and synthetic user ID. It never modifies authentication or emits auth cookies. Its keyed read-only observation endpoint still uses the request's actual WordPress current user; the key itself grants no WordPress identity. The observer and generated configuration exist only in the temporary site.
4. Run 3 identifier cases × remember on/off × 2 prefixes = **12 HTTP cases** through Core `wp-login.php`. Check session/persistent HttpOnly Core cookie, unchanged ID/role/Unicode display name, local destination, unchanged user count, no active regular plugins, and exactly one Core `wp_login` success event.
5. Fingerprint user, role, usermeta, table and non-identity domain state; activate the copied production plugin; confirm activation preserves identity/domain state and creates exactly the two approved Members tables plus bounded options. Run the same **12 HTTP cases** through Members.
6. Exercise registration, profile, consent, logout, Core lost-password mail/key, password change, withdrawal, rate limiting, audit retention, privilege denial, migration dry-run/import/rerun, redirect and CSRF matrices. The administrator flow must show a pending withdrawal, finalize it without deleting/remapping the Core ID, and remain idempotent on replay. Then inject `wp_mail()` failure for all four approved account events and verify committed state/session revocation, success responses, `failure/wp_mail_failed` audit rows, zero delivery-sink records, and zero retry attempts. Toggle Members off to verify synthetic Woo/LMS/KBoard rows and Core fallback, then reactivate it.
7. Measure three 100-request blocks each with Members off/on after 20 warm-ups, then activate the copied actual device-limit and test allowed, exchange-required, Core, and removed-device paths. Stop all owned processes and delete only the validated temporary tree.

The runner has no option for an existing site URL, existing DB endpoint, existing datadir, or reference-site clone. It reads only the pinned device-limit source directory and records its manifest hash; it does not bootstrap or write the reference site. There are no real email/SMS/provider requests.

## Files and limitations

| File | Responsibility |
| --- | --- |
| `run.py` | Lifecycle, dependency verification, isolated HTTP client, login assertions, redacted reports |
| `test_runner.py` | Destructive-operation boundaries, assertion falsification, and UI route-asset guards |
| `ui_contract.json` | `AUTH-UI-001` screen/state/translation/accessibility/asset contract manifest |
| `ux_strategy_contract.json` | `AUTH-UX-003` approved frontend/admin information architecture and implementation boundaries |
| `mamp_woo_case.php` | CLI-only, fixed-sandbox Woo/WCI fixture with tagged user/product/orders, Members optional-dependency toggles, and exact cleanup |
| `mamp_lms_case.php` | CLI-only, fixed-sandbox LMS fixture for identity/access/domain ownership, Members fallback, mail sink, and exact cleanup |
| `mamp_lms_run.py` | Runs the actual fixed-sandbox LMS identity/access/on-off contract and writes a per-run JSON report |
| `mamp_lifecycle_run.py` | Verifies ZIP install, previous→current update, reinstall, deactivate/reactivate, protected IDs/domain fingerprint, and exact source restoration |
| `wordpress.lock.json` | Exact Core archive and checksum manifest provenance |
| `database.php` | CLI-only, datadir-verified database provisioning |
| `config.php` | Guarded temporary wp-config template; never deployed |
| `fixture.php` | CLI-only synthetic installation/users and sink probes |
| `activate.php` | CLI-only production plugin activation in the owned site |
| `snapshot.php` | Redacted activation/domain state fingerprints |
| `observer.php` | Test-only observation and outbound side-effect guards |
| `router.php` | Loopback/Host restriction and bounded dev server routing |

The `AUTH-UI-001` unit guard verifies that every current Members frontend route and the admin surface are represented in the UI contract. `AUTH-UI-002` additionally verifies the CSS files, responsive/focus rules, server-rendered page shell, route-only frontend asset hook, admin-only asset hook, and the route-scoped authentication enhancement. `AUTH-UX-003` fixes the approved strategy; 0.7.5 implements login/registration, 0.7.6 implements account/reset/navigation UX, 0.7.7 implements the Users-area information architecture, and 0.7.8 implements reasoned withdrawal review and bounded audit operations. Browser acceptance remains a separate MAMP check.

The fixed MAMP LMS fixture exercises actual Woo order reconciliation into KKLIDI LMS enrollment, WordPress ID continuity across progress/certificate/private-question rows, learner/outsider access, route-scoped Members profile delegation, Members-off LMS/Core fallback, and exact cleanup. It creates only tagged synthetic data and sinks notification mail.

0.5.0 adds `concurrency_case.php`: 100 calls across eight PHP workers must allow exactly ten under the same limiter key, under both prefixes. `mamp_woo_run.py` submits actual Members/Woo forms and checks same-session Store API cart, rendered member-order link, guest-order separation and device-limit allow/deny. `mamp_kboard_run.py` checks actual post/comment HTML and KBoard write permissions with Members on/off. Both fixed-sandbox scripts clean up in `finally`; Woo requires WCI files in the sandbox. `build_release.py` packages only the production allowlist and validates the Korean MO catalog.

`mamp_race_run.py` exercises eight simultaneous registration submissions and eight pre-opened Core reset forms against Apache workers. `mamp_timing_run.py` records bounded existing/missing-identifier timing distributions without retaining identifiers. `mamp_https_run.py` places the fixed sandbox behind a per-run local CA/TLS proxy and verifies HSTS, host-only guest cookies, Core Secure cookies and cleanup. `reference_d06_audit.php` reads only structural metadata inside a rolled-back read-only transaction. `deployment_preflight.py` refuses HTTP and credentials, then checks trusted HTTPS, HSTS, private/no-store headers, and guest-cookie flags. `validate_deployment_manifest.py` rejects credentials and incomplete owner, backup, rollback or observation evidence.

With the dedicated MAMP Apache and MySQL sandbox running, the repeatable LMS and plugin lifecycle gates are:

```powershell
& $Python tests/harness/mamp_lms_run.py
& $Python tests/harness/mamp_lifecycle_run.py
```

Both runners accept no alternate site path or URL, use a per-run token, write `.harness/reports/<run-id>.json`, and restore their owned data, plugin state, files, and temporary directories in `finally`. The lifecycle runner probes the fixed plugin parent before mutation and uses same-volume atomic directory moves so a permission failure cannot degrade into a partial copy.

**Remaining environment gates:** local TLS/Core Secure-cookie and object-cache/storage-failure behavior have executable evidence. The actual production certificate/CDN/proxy, multiple application hosts, and production migration still require an explicitly identified staging/production environment, completed deployment manifest and owner handoff. KBoard permission-engine parity and content migration remain out of scope because KBoard is scheduled for removal.

Fixture user IDs 2 and 3 are newly created synthetic identities, never remapped real users. Cookies/passwords/probe keys are not written to the report. Temporary synthetic hashes and data are removed after the run. Failed subprocess diagnostics are redacted; no raw response/cookie/header dump is retained on successful runs. An interrupted OS/process termination outside Python's `finally` may leave a temporary run behind; its `owner` marker and path must be checked before any manual cleanup. Never kill processes by executable name or remove a shared MAMP datadir.

The current source-of-truth execution status is recorded in `docs/HARNESS_PLAN.md`.
