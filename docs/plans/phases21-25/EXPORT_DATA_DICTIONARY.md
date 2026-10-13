# Export data dictionary

Exports are CSV and JSON for Nathan's later analysis. They are operational
facts. They are not formal books and they do not move money.

Every export includes `exported_at`, `timezone` (`America/New_York`), `as_of`,
`organization_reference`, and `schema_version`. Filters are explicit. Cells that
begin with `=`, `+`, `-`, or `@` are prefixed so a spreadsheet does not treat
them as formulas.

Stable identifiers are public references, not a requirement to type raw UUIDs
in the product UI. Money columns are integer minor units with a `currency` of
`USD`. Timestamps include an offset. Missing values stay blank or `unknown`.
They are not zero.

Phase 25 serves the files. Earlier phases do not pretend an export succeeded
when the source is absent. The export omits call audio, transcripts, auth
secrets, and precise location coordinates.
