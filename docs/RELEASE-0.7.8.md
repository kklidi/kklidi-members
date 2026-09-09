# 0.7.8 release evidence and deployment gates

0.7.8 implements the withdrawal-review and audit-operations slice of
`AUTH-UX-003`. Administrators with `manage_kklidi_members` can finalize a pending
withdrawal as disabled or restore it to active with a required review reason.

Both decisions recheck capability, nonce, current state and target user, preserve the
WordPress user ID and external domain rows, and revoke every existing Core session
and application password. Restoration never revives an old session. Repeated review
submissions do not add another transition or audit event.

The review reason is reduced to the existing audit subject digest; raw text is not
shown in or stored by the audit view. The audit screen exposes only event, result,
reason code, UTC timestamp and WordPress user ID. It supports known-event, result,
UTC-date and user-ID filters with 25 rows per page and at most 100 accessible pages.
Account-notice delivery outcomes are read-only; templates, SMTP and retry queues are
outside this release.

## Local release gate

- 28 unit guards pass, including both withdrawal transitions, reason requirement,
  session revocation, audit data minimization, filters, pagination and
  optional-domain bounds.
- Synthetic WordPress run `d9256bc16d5843e98164623feffb3b03` passes both table
  prefixes: all 24 MVP contracts, the approved notification extension, 12 Core login
  cases and 12 Members login cases. It exercises restoration and finalization,
  replay, translated audit rendering and all prior MVP contracts.
- All 57 production/harness PHP files pass syntax validation. The Korean catalog
  covers all 254 extracted source strings, compiles 266 messages, and the installable
  0.7.8 ZIP contains the 50-file production allowlist.

## Remaining gates

0.7.9 owns MAMP desktop/mobile browser, keyboard, no-JavaScript, route isolation,
Members-off regression and final local release evidence. Production acceptance
remains `PARTIAL` until the trusted HTTPS staging manifest, backup/restore,
applicable multi-node checks and observation window are complete.
