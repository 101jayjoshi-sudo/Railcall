# Zendesk Support Suite: Governed Help Desk Automation

Enterprise-ready, heavily governed Zendesk integration for Support-Ops, CRM enrichment, and automated ticket triage. Exposes **27 commands** spanning every major Zendesk resource, built for the solo consultant or scaling agency that needs rock-solid reliability without fear of double-charges or leaked credentials.

## Advanced Orchestration
The real power of this module lies in 5 exclusive orchestration commands that compose multiple Zendesk API calls into single, atomic operations:
- `zendesk.auto_assign_organization` `{"ticket_id":123}` — Parses the requester's email domain, searches for an existing organization, creates it if missing, and links both the user and ticket automatically. One human approval, 5 API calls.
- `zendesk.merge_duplicate_tickets` `{"ticket_id":123}` — Scans for all open tickets from the same requester, posts a merge notice on the primary ticket, and marks duplicates solved. Zero orphaned tickets.
- `zendesk.apply_macro_to_ticket` `{"ticket_id":456,"macro_id":789}` — Fetches the macro's action list and applies status, priority, comment, and group_id fields to the ticket in one transaction.
- `zendesk.generate_support_digest` `{}` — Queries all tickets created in the last 24h, aggregates by status and priority, and returns a clean Markdown report. The report Zendesk's dashboard does not give you out of the box.
- `zendesk.bulk_import_tickets` `{"tickets":[{"subject":"Crash","comment":"App crashed on iOS"}]}` — Submits a batch-create job and safely polls the async job status endpoint until the import is confirmed.

## Tickets
- `zendesk.create_ticket` `{"subject":"Login issue","comment":"Can't login since update"}` — Creates a new ticket. Idempotent via airlock payload hash in the External-Id header.
- `zendesk.update_ticket` `{"ticket_id":123,"status":"solved"}` — Updates ticket status, priority, or appends a public or internal comment.
- `zendesk.get_ticket` `{"ticket_id":123}` — Fetches a single ticket with full metadata.
- `zendesk.list_tickets` `{"status":"open"}` — Lists tickets, filterable by status.
- `zendesk.search_tickets` `{"query":"type:ticket status:open tag:billing"}` — Exposes Zendesk's full search syntax.
- `zendesk.delete_ticket` `{"ticket_id":123}` — High-risk delete, always stop-at-airlock.

## Users & Provisioning
- `zendesk.create_user` `{"name":"Ada Lovelace","email":"ada@example.com"}` — Provisions a new user. Idempotent via External-Id.
- `zendesk.update_user` `{"user_id":456,"phone":"555-0100"}` — Enriches user profile fields.
- `zendesk.get_user` `{"user_id":456}` — Fetches user details by ID.
- `zendesk.list_users` `{"role":"agent"}` — Lists users, filterable by role.

## Organizations & Groups
- `zendesk.create_organization` `{"name":"Acme Corp"}` — Creates an org. Idempotent via External-Id.
- `zendesk.get_organization` `{"organization_id":789}` — Fetches org profile.
- `zendesk.list_organizations` `{}` — Lists all organizations.
- `zendesk.create_group` `{"name":"Tier 2 Support"}` — Creates an agent team group.
- `zendesk.list_groups` `{}` — Lists all groups.

## Macros
- `zendesk.list_macros` `{"active":true}` — Lists available ticket macros.
- `zendesk.get_macro` `{"macro_id":111}` — Fetches macro details and its action list.

## Trust
Every write operation (POST/PUT) carries an Idempotency-Key derived from the airlock payload hash. One approval equals at most one write, even if the connection drops mid-retry. A missing idempotency helper is a hard error, never a silent fallback.

Rate limiting is fully handled via HTTP 429 Retry-After headers with up to 3 attempts and exponential backoff.

Raw error payloads are redacted before they reach logs — credentials, tokens, and raw URLs are never surfaced.

## Setup
Add a single vault entry named `zendesk` with three keys: `subdomain`, `email`, and `api_token`. The module reads these at execution time from the local 0600 vault. Credentials are never sent in request bodies and never logged in receipts. Works with both API token and OAuth scoped tokens.

[contest:2026Q3]
