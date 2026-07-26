# RailCall Zendesk Integration Module & Support Triage Workflow

A professional, local-first integration module for **Zendesk** and a sample **Support Triage Workflow** built for RailCall. 

This module satisfies all RailCall governance principles:
* **Zero-Trust & Safe Auth**: Secrets never touch the database or request bodies; credentials stay encrypted in the local Vault (`keys.local.json`).
* **Signature Verified**: The bundle is signed by the publisher's Ed25519 keypair and verified locally before loading.
* **Airlock Governance**: Sensitive write commands require operator approval and log tamper-evident receipts.

---

## 📦 Installation

To install the Zendesk integration module from the marketplace:
```bash
railcall market install jayy/zendesk
```

*Pricing: $49 one-time purchase. Trial licenses are supported automatically by the marketplace.*

Restart your local RailCall Studio server to load the new commands:
```bash
railcall studio
```

---

## 🔑 Configuration

To authorize the module, configure your Zendesk credentials in the local Vault. In the RailCall Studio, navigate to **Integrations** -> **Zendesk**, or add them directly to your `keys.local.json` file inside your workspace directory:

```json
{
  "jayy/zendesk": {
    "ZENDESK_SUBDOMAIN": "your-subdomain",
    "ZENDESK_EMAIL": "your-email@example.com",
    "ZENDESK_API_TOKEN": "your-zendesk-api-token"
  }
}
```

*Note: The API token is a Zendesk password-less API token. Make sure it is enabled under Admin Center -> Apps and Integrations -> APIs -> Zendesk API.*

---

## 🛠️ Module API Commands

The module exposes 6 core commands under the `zendesk` namespace:

### 1. `zendesk.create_ticket` (Write/Requires Approval)
Create a new Zendesk ticket.
* **Inputs**:
  * `subject` (string, required): The ticket subject.
  * `comment` (string, required): The initial public comment body.
  * `priority` (string, optional): `urgent` | `high` | `normal` | `low`.
  * `type` (string, optional): `problem` | `incident` | `question` | `task`.
  * `requester_email` (string, optional): The requester's email.
  * `requester_name` (string, optional): The requester's full name.

### 2. `zendesk.update_ticket` (Write/Requires Approval)
Update ticket status, priority, or add a comment.
* **Inputs**:
  * `ticket_id` (number, required): The ticket ID.
  * `status` (string, optional): `new` | `open` | `pending` | `hold` | `solved` | `closed`.
  * `comment` (string, optional): Add a comment to the ticket.
  * `comment_private` (boolean, optional): Set to `true` to make the comment an internal note.

### 3. `zendesk.get_ticket` (Read-only)
Fetch detailed information for a specific ticket.
* **Inputs**:
  * `ticket_id` (number, required)

### 4. `zendesk.list_tickets` (Read-only)
List tickets with optional status filtering.
* **Inputs**:
  * `status` (string, optional)
  * `limit` (number, optional, default 20)

### 5. `zendesk.create_user` (Write/Requires Approval)
Create a new user (end-user, agent, or admin) in Zendesk.
* **Inputs**:
  * `name` (string, required)
  * `email` (string, required)
  * `role` (string, optional): `end-user` | `agent` | `admin`

### 6. `zendesk.list_users` (Read-only)
List users filtered by role.
* **Inputs**:
  * `role` (string, optional)
  * `limit` (number, optional, default 20)

---

## 🎬 Support Triage Workflow Template

We include an end-to-end support ticket triage workflow (`zendesk_support_triage.json`) that automates support ticket routing.

1. **Trigger**: Support leads CSV containing `name`, `email`, and `status`.
2. **Routing Logic**:
   * Rows with status `"new"` route to `zendesk.create_user` to provision their account.
   * Rows with status `"escalated"` route to `zendesk.create_ticket` to open an urgent support ticket.
   * Rows with status `"notified"` route to `slack.message_post` to alert the team.

To run this workflow locally:
```bash
railcall workflow run zendesk_support_triage.json --data customer_leads.csv
```

---

## 🧪 Local Testing & Verification

Run the included verification test suite which starts a loopback mock server and executes all 6 operations offline:
```bash
python3 tests/test_zendesk_module.py
```
All commands will execute, assert against the mock server's output, and print the telemetry logs.
