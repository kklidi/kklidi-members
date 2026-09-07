# 0.5.0 release evidence and deployment gates

## Scope

0.5.0 packages the existing Phase 0 MVP, scoped account/admin UI, Korean gettext
catalogs, and integration verification. It does not enable registration on a site,
migrate production users, or establish retention/access policies. WordPress remains
the only identity/password/auth-cookie owner. User IDs and external domain rows
are not remapped. No PHP-session authentication or optional authentication features
are introduced.

## Verified

The aggregate, credential-free execution evidence is in [evidence/0.5.0.json](evidence/0.5.0.json).

- WordPress 7.1, PHP 8.3.1, MySQL 5.7.24, single-site synthetic harness, two prefixes.
- 24 MVP contracts exercised; detailed PASS/SYNTHETIC_PASS/PARTIAL classifications
  remain in the generated report, not collapsed into a production approval.
- Rate limit: 100 calls from eight PHP workers, exactly 10 allowed per prefix.
  This is a real database concurrency check, not a distributed attack simulation.
- Actual MAMP Woo 11.1.0/WCI 1.0.3: login POST returns to checkout, same-cookie
  Store API cart retains the product, rendered member-order link is present,
  same-email guest order stays unclaimed. Actual Woo login form preserves
  device-limit 1.1.3 allow/deny results. Test orders use no payment gateway.
- Actual LMS 1.1.1: order/enrollment identity, progress, certificate, private-question
  ownership, learner/outsider separation, profile delegation and Members-off fallback.
- Actual KBoard 6.5: list, post and comment HTML, subscriber/anonymous write policy,
  original author IDs, Members on/off no-fatal, comment login link switching between
  Members and Core, no Members CSS. Fixture data removed.
- Korean MO catalog can be loaded and resolves English source strings.

## Open gates before production

| Gate | Remaining work |
| --- | --- |
| D01 | Decide public registration, required phone, email verification and automatic login; existing defaults remain unchanged. |
| D02 | Decide withdrawal recovery, PII treatment and retention by domain; no automatic deletion policy is invented. |
| D06 | Assign the actual service owners of three legacy restriction pages and three menu items; KBoard tests cannot establish protection on these unrelated pages. |
| D07 | Confirm supported minimum versions; plugin header minimums are historical declarations, not a tested multi-version matrix. |
| HTTPS | Validate trusted TLS, Secure cookies and proxy/cache configuration in the actual deployment environment. |
| Browser | Interactive JavaScript execution and browser/device fingerprint generation; HTTP form tests are not browser-JavaScript evidence. |
| Abuse and races | Distributed attacks, persistent-cache/proxy outage matrix, concurrent registration/reset consumption, and enumeration timing distributions. |
| Migration | Production dry run, owner handoff and observation/rollback approval; disabling Members alone does not preserve Members-only withdrawal guards. |

KBoard permission-engine parity and content migration remain out of scope because
KBoard is scheduled for removal. Optional/FUTURE authentication remains deferred.

## Reproduce and install

See `tests/harness/README.md` for the disposable harness. MAMP scripts accept only
the dedicated sandbox path and must not be placed in a live site's web root.

```powershell
& $Python -m unittest discover -s tests/harness -p test_runner.py -v
& $Python tests/harness/run.py
& $Python tests/harness/mamp_kboard_run.py
& $Python tests/harness/mamp_woo_run.py
& $Python tests/harness/build_release.py
```

MAMP Woo verification requires the actual WCI plugin installed in that sandbox.
Fixtures restore original options/activation state and delete their tagged test data.
The ZIP contains only the production allowlist and release documentation; no WordPress,
WooCommerce, LMS, KBoard, device-limit, database, test fixture or cached credentials.
Install `dist/kklidi-members-0.5.0.zip` through WordPress Plugins → Add New → Upload
on a test site. The SHA-256 manifest accompanies the local ZIP.
