# RailCall Zendesk Module & Support Triage Workflow (2026Q3 Contest Submission)

This repository contains the complete source code, manifest, workflow spec, and test suites for my submission to the **2026Q3 RailCall Module and Workflow Contest**.

Both submissions are fully published, signature-verified, and live on the marketplace.

---

## 📂 Repository Structure

* **`zendesk/`** (Zendesk Integration Module):
  * `module.json`: The manifest file declaring slug, commands, and schemas.
  * `handlers/handler.py`: The module's Python backend code (executes REST requests).
  * `module.sig`: Ed25519 signature hex verifying the manifest and handler code.
  * `README.md`: The developer/user guide for the module.
* **`workflow_support_triage_receipt.json`**: The workflow spec file.
* **`test_zendesk_module.py`**: Local unit test suite running against a loopback mock server.
* **`run_workflow_engine.py`**: Flow engine test harness to simulate lead CSV routing.

---

## 📦 Entry 1: Track A — Zendesk Integration Module

* **Marketplace Slug**: `jayy/zendesk-integration`
* **Direct Listing URL**: [https://railcall.ai/marketplace/jayy/zendesk-integration](https://railcall.ai/marketplace/jayy/zendesk-integration)
* **Pricing**: $49.00 One-time purchase
* **Install Command**:
  ```bash
  railcall market install jayy/zendesk-integration
  ```

### Exposes 6 Core Commands:
1. `zendesk.create_ticket`: Create a new support ticket (subject, comment, priority, requester details).
2. `zendesk.update_ticket`: Update ticket status, priority, or add a comment/internal note.
3. `zendesk.get_ticket`: Fetch ticket status and details by ID.
4. `zendesk.list_tickets`: List tickets with optional status filter.
5. `zendesk.create_user`: Create user profiles (end-user, agent, or admin).
6. `zendesk.list_users`: List users filtered by role.

---

## 🎬 Entry 2: Track B — Best Workflow

* **Marketplace Slug**: `jayy/support-triage`
* **Direct Listing URL**: [https://railcall.ai/marketplace/jayy/support-triage](https://railcall.ai/marketplace/jayy/support-triage)
* **Pricing**: Free ($0)
* **Install Command**:
  ```bash
  railcall market install jayy/support-triage
  ```

### Scenario:
1. **Trigger**: Processes support leads CSV containing fields `name`, `email`, `status`, `message`.
2. **Routing Flow**:
   * Rows with status `"new"` route to `zendesk.create_user` to provision accounts.
   * Rows with status `"escalated"` route to `zendesk.create_ticket` to open tickets.
   * Rows with status `"notified"` route to `slack.message_post` to alert developers.
   * Rows with status `"resolved"` are routed to the terminal stage.

---

## 🧪 Local Testing & Offline Verification

Both entries are fully verified offline. You can execute these test scripts directly from the repository.

### 1. Run Zendesk Module Operations Test:
Starts a local mock server and executes all 6 operations, validating payload formatting and returns:
```bash
python3 test_zendesk_module.py
```

### 2. Run Workflow Routing Simulation:
Executes the workflow engine to process records in `zendesk_leads.csv`, verifying correct routing rules and variables substitution:
```bash
python3 run_workflow_engine.py
```
