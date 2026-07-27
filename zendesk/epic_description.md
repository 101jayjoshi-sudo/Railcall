# Zendesk Support Suite: Governed Help Desk Automation

Enterprise-ready, heavily governed Zendesk integration for Support-Ops, CRM enrichment, and automated ticket triage. Exposes **22 commands** spanning every major Zendesk resource, built specifically for the solo consultant or scaling agency that needs rock-solid reliability without fear of double-charges or leaked credentials.

## 🚀 ADVANCED ORCHESTRATION
The real power of this module lies in 5 exclusive orchestration commands that compose multiple Zendesk API calls into single, atomic operations:
- `zendesk.auto_assign_organization` `{"email":"ceo@acme.com"}` — Parses the email domain, searches for an existing organization, creates it if missing, and links the user/ticket automatically.
- `zendesk.merge_duplicate_tickets` `{"ticket_id":123,"threshold_hours":24}` — Scans for open tickets from the same user within a timeframe, merges them with a template note, and closes the duplicates.
- `zendesk.apply_macro_to_ticket` `{"ticket_id":456,"macro_id":789}` — Executes a Zendesk macro (canned response + tag updates) directly via the API.
- `zendesk.generate_support_digest` `{"hours":24}` — Compiles all support desk metrics (new tickets, closed tickets, SLA breaches) into a clean Markdown summary.
- `zendesk.bulk_import_tickets` `{"tickets":[{"subject":"Crash","comment":"App crashed"}]}` — Submits a batch job for mass ticket creation and safely polls the async status endpoint.

## 🎫 TICKETS
- `zendesk.create_ticket` `{"subject":"Login issue", "comment":"Can't login"}` — Creates a new ticket.
- `zendesk.update_ticket` `{"ticket_id":123, "status":"solved"}` — Updates ticket properties.
- `zendesk.get_ticket` `{"ticket_id":123}` — Fetches a single ticket with full metadata.
- `zendesk.list_tickets` `{"status":"open"}` — Lists tickets, filterable by status.
- `zendesk.search_tickets` `{"query":"type:ticket status:open"}` — Powerful Zendesk search syntax.
- `zendesk.delete_ticket` `{"ticket_id":123}` — Removes a ticket entirely.

## 👤 USERS & PROVISIONING
- `zendesk.create_user` `{"name":"Ada Lovelace", "email":"ada@example.com"}` — Provisions a new user.
- `zendesk.update_user` `{"user_id":456, "phone":"555-0100"}` — Enriches user profile.
- `zendesk.get_user` `{"user_id":456}` — Fetches user details.
- `zendesk.list_users` `{"role":"agent"}` — Lists users, filterable by role.

## 🏢 ORGANIZATIONS & GROUPS
- `zendesk.create_organization` `{"name":"Acme Corp"}`
- `zendesk.get_organization` `{"org_id":789}`
- `zendesk.list_organizations` `{}`
- `zendesk.create_group` `{"name":"Tier 2 Support"}`
- `zendesk.list_groups` `{}`

## 📝 MACROS
- `zendesk.list_macros` `{"active":true}`
- `zendesk.get_macro` `{"macro_id":111}`

## 🛡️ TRUST & SECURITY
Every write operation (POST/PUT) carries a **Stripe-style Idempotency-Key** derived from the `airlock_payload_hash`. This guarantees that if a connection drops mid-retry, one approval equals at most one write. Zero duplicate tickets. Zero phantom users. 
A missing idempotency helper is a hard error, never a silent fallback.

Rate limiting is fully handled via **HTTP 429 Retry-After** headers with exponential backoff.
Raw error payloads are aggressively **redacted** to strip sensitive tokens, passwords, and URLs before they reach the logs.

## ⚙️ SETUP
Requires a single `ZENDESK_API_TOKEN` and `ZENDESK_SUBDOMAIN` stored securely in the local Vault. No plaintext environment variable fallbacks. Tokens are NEVER sent in request bodies and NEVER logged in receipts.

[contest:2026Q3]
