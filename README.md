# RailCall Zendesk Module & Support Workflows (2026Q3 Contest Submission)

This repository contains the complete source code, manifest, workflow specs, and test suites for my submission to the **2026Q3 RailCall Module and Workflow Contest**.

All submissions are fully published, signature-verified, and live on the marketplace.

---

## 📂 Repository Structure

* **`zendesk/`** (Zendesk Integration Module):
  * `module.json`: The manifest file declaring slug, commands, and schemas.
  * `handlers/handler.py`: The module's Python backend code (executes REST requests).
  * `module.sig`: Ed25519 signature hex verifying the manifest and handler code.
  * `epic_description.md`: The developer/user guide for the module's marketplace page.
* **`workflow_support_triage_spec.json`**: The basic support triage workflow spec.
* **`workflow_intelligent_pipeline_spec.json`**: The advanced 7-step orchestration workflow spec.
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

### Exposes 22 Core Commands:
1. **Tickets (6)**: create, update, get, list, search, delete
2. **User Lifecycle (4)**: create, update, get, list
3. **Organizations (3)**: create, get, list
4. **Groups (2)**: create, list
5. **Macros (2)**: get, list
6. **Advanced Orchestration (5)**: auto-assign org, merge duplicates, apply macro, generate digest, bulk import

---

## 🎬 Entry 2: Track B — Intelligent Support Pipeline (Advanced)

* **Marketplace Slug**: `jayy/intelligent-support-pipeline`
* **Pricing**: Free ($0)
* **Install Command**:
  ```bash
  railcall market install jayy/intelligent-support-pipeline
  ```

### Scenario:
An advanced, 7-step Support-Ops pipeline that demonstrates the full orchestration power of the Zendesk module. It:
1. Provisions the incoming user.
2. Creates a governed support ticket.
3. Auto-detects and links their corporate organization based on email domain.
4. Deduplicates any existing open tickets for that user.
5. Applies a welcome macro.
6. Compiles a daily support metrics digest.
7. Alerts the Ops team via Slack.

---

## 🎬 Entry 3: Track B — Support Triage (Basic)

* **Marketplace Slug**: `jayy/support-triage`
* **Pricing**: Free ($0)
* **Install Command**:
  ```bash
  railcall market install jayy/support-triage
  ```

### Scenario:
A basic webhook routing flow that processes support leads, creating Zendesk users, tickets, or Slack alerts based on state machine rules.

---

## 🧪 Local Testing & Offline Verification

Both entries are fully verified offline. You can execute these test scripts directly from the repository.

### 1. Run Zendesk Module Operations Test:
Starts a local mock server and executes all 22 operations, validating payload formatting and returns:
```bash
python3 test_zendesk_module.py
```

### 2. Run Workflow Routing Simulation:
Executes the workflow engine to process records in `zendesk_leads.csv`, verifying correct routing rules and variables substitution:
```bash
python3 run_workflow_engine.py
```
