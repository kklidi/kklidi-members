# 0.7.18 bounded registration fields

0.7.18 implements `AUTH-REGISTER-FIELDS-001` without adding a generic form builder.

## Behavior

- `Users → KKLIDI Members → Registration fields` controls only first name, last name, and phone.
- Each configurable field can be required, optional, or hidden.
- The default remains first name required, last name optional, and phone optional.
- Email, password, password confirmation, display name, service consent, and privacy consent remain required and locked.
- Hidden fields are absent from the registration form and ignored by the server if injected into POST data.
- Changes affect subsequent registration requests only. Existing users, profile values, WooCommerce orders, and LMS records are not rewritten.

## Storage and security

- The WordPress Settings API stores schema version 1 in the non-autoload `kklidi_members_registration_fields` option.
- Settings require `manage_kklidi_members` and a WordPress Settings API nonce.
- Unsupported fields, missing fields, schema changes, and unknown states reject the whole update and retain the last valid value.
- Registration still fixes the new role to `subscriber`, uses WordPress Core users/passwords, creates no auth cookie, and requires current service/privacy documents.
- Settings audit stores no member field values. It records the event and a keyed digest of the approved field-state metadata.

## Verification scope

The unit guard validates the manifest and implementation boundary. Synthetic WordPress run `10c0655fedec48139a72e44264503bc5` passed default compatibility, Settings API capability/nonce, non-autoload storage, atomic rejection, required-field validation, hidden-field POST rejection, fixed role and ID injection rejection under `wp_` and an arbitrary prefix. Its owned filesystem, database, processes, and field-test user were removed.

MAMP lifecycle and final release evidence are recorded after the production ZIP is built. External mailbox delivery is unrelated to this contract.
