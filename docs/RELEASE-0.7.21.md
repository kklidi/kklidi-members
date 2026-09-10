# 0.7.21 page-free route management

0.7.21 implements `AUTH-ROUTE-MAP-001` as an opt-in URL adapter for the nine existing Members screens. It does not create WordPress pages, shortcodes, blocks, menu items, authentication state, or external-domain records.

## Behavior

- Fresh installs and upgrades keep clean routes disabled.
- A capability and nonce protected administrator action may enable the fixed `/members/` route family only when pretty permalinks are active and the namespace has no page, specific rewrite-rule, or reserved-endpoint conflict.
- The persisted non-autoload option contains only schema version 1 and `clean_routes_enabled`.
- The route rules dispatch to the same query keys, controllers, templates, no-store behavior, authorization checks, and route-scoped assets as the existing query URLs.
- Query routes remain available while clean routes are enabled and become the effective helper URLs again when disabled or when the setting schema is unreadable.
- WordPress login and registration URL ownership remain separate opt-ins. Core force-reauth and direct `wp-login.php` access are not intercepted.
- Rewrite rules are flushed only for plugin lifecycle events and real setting transitions. A failed persisted-rule check restores the previous option state.

## Verification status

PHP lint and 37 unit/design guards pass. Disposable WordPress run `8c6ea0415d3d4e208ed79dbc7727886b` passes the 24 MVP and six extension contracts across both database prefixes, including the complete route contract and cleanup. Its paired general-page measurement stays within the median and p95 budgets; the route option adds one median query while memory and global assets remain unchanged.

The fixed-MAMP lifecycle gate covers fresh installation, 0.7.20 update, current-version reinstall, deactivation fallback, reactivation, protected WordPress IDs/domain fingerprints, and exact source restoration. The candidate runner temporarily mounts the same ZIP and requires route, local TLS/Core-cookie, LMS, WooCommerce, KBoard on/off, registration/reset race, and login-timing gates to pass before it restores the original plugin tree. The final evidence export binds those run IDs to the final archive SHA-256.

The actual production certificate/CDN/proxy, mailbox delivery, backup restore drill, and observation window remain deployment acceptance gates. Authoritative dynamic evidence is stored outside the installable ZIP under `.harness/reports` and `docs/evidence`.
