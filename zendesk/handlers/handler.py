"""RailCall Zendesk Integration Module.

Enterprise-ready governed Zendesk module for Support-Ops and Help Desk automation.

SECURITY & SETUP:
All credentials are read at execution time from RailCall's local 0600 vault.
The module never accepts, returns, logs, or persists credentials or raw URLs.
To configure, add a vault entry named `zendesk` with keys: `subdomain`, `email`, `api_token`.
"""

import base64
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

_H = __rc_helpers__
_USER_AGENT = "RailCall-Zendesk/1.0"
_MAX_ATTEMPTS = 3
_RETRY_CODES = {429, 502, 503, 504}


class ZendeskError(RuntimeError):
    """Clean error raised for Zendesk integration."""
    pass


# ── VALIDATION HELPERS ──────────────────────────────────────────────────

def _clean_text(value, field, maximum=500):
    value = str(value or "").strip()
    if not value:
        raise ZendeskError(f"{field} must not be empty")
    if len(value) > maximum:
        raise ZendeskError(f"{field} exceeds {maximum} characters")
    return value


def _optional_text(value, field, maximum=500):
    if value in (None, ""):
        return None
    return _clean_text(value, field, maximum)


def _positive_id(value, field):
    if value in (None, ""):
        raise ZendeskError(f"{field} must be supplied")
    if isinstance(value, bool):
        raise ZendeskError(f"{field} must be a positive integer")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ZendeskError(f"{field} must be a positive integer")
    if number <= 0 or float(value) != number:
        raise ZendeskError(f"{field} must be a positive integer")
    return number


def _optional_positive_id(value, field):
    if value in (None, ""):
        return None
    return _positive_id(value, field)


def _email(value):
    text = _clean_text(value, "email", 254).lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text):
        raise ZendeskError(f"email '{text}' is not valid")
    return text


def _optional_email(value):
    if value in (None, ""):
        return None
    return _email(value)


# ── CREDENTIALS & OUTBOUND REQUESTS ────────────────────────────────────

def _credentials():
    entry = _H["vault_get"]("zendesk")
    if not isinstance(entry, dict):
        raise ZendeskError(
            "No Zendesk credential saved. Open RailCall Studio > Connect > "
            "Zendesk, and configure your subdomain, email, and api_token."
        )
    subdomain = str(entry.get("subdomain") or "").strip()
    email = str(entry.get("email") or "").strip()
    api_token = str(entry.get("api_token") or "").strip()
    
    if not subdomain or not email or not api_token:
        raise ZendeskError(
            "Zendesk credential missing required fields. Ensure subdomain, "
            "email, and api_token are configured in the Studio Vault."
        )
    if any(ch.isspace() for ch in subdomain):
        raise ZendeskError("Zendesk subdomain cannot contain whitespace.")
    if len(api_token) < 8:
        raise ZendeskError("Zendesk api_token is invalid (too short).")
        
    return subdomain, email, api_token


def _safe_api_message(raw, status):
    if status in (401, 403):
        return "Zendesk rejected the saved credential or its permissions."
    if status == 404:
        return "Zendesk resource was not found or is not visible to this user."
    message = ""
    try:
        payload = json.loads(raw.decode("utf-8", "replace"))
        if isinstance(payload.get("description"), str):
            message = payload["description"]
        elif isinstance(payload.get("error"), str):
            message = payload["error"]
        elif isinstance(payload.get("message"), str):
            message = payload["message"]
    except Exception:
        pass
    if not message:
        message = f"Zendesk returned HTTP {status}"
    
    # Redact sensitive keys and URLs to prevent credential leaks in logs
    message = re.sub(r"(?i)(api[_-]?token|token|password|auth|key)\s*[:=]\s*\S+", r"\1=[REDACTED]", message)
    message = re.sub(r"https?://\S+", "[URL REDACTED]", message)
    return message[:240]


def _sleep_seconds(headers, attempt):
    raw = ""
    try:
        raw = headers.get("Retry-After", "")
    except Exception:
        pass
    try:
        delay = float(raw)
    except (TypeError, ValueError):
        delay = float(2 ** (attempt - 1))
    return max(0.0, min(delay, 10.0))


def _request(method, path, params=None, body=None, payload_hash=None):
    subdomain, email, api_token = _credentials()
    
    # Build Basic Auth header
    auth_str = f"{email}/token:{api_token}"
    auth_header = "Basic " + base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    
    # Check if local loopback redirect for testing is requested
    if subdomain.startswith("127.0.0.1") or subdomain.startswith("localhost"):
        url = f"http://{subdomain}{path}"
    else:
        url = f"https://{subdomain}.zendesk.com{path}"
        
    if params:
        clean_params = {
            k: str(v) for k, v in params.items() if v not in (None, "")
        }
        if clean_params:
            url += "?" + urllib.parse.urlencode(clean_params)
            
    headers = {
        "Accept": "application/json",
        "User-Agent": _USER_AGENT,
        "Authorization": auth_header,
    }
    
    # Add idempotency headers derived from the airlock payload hash
    if payload_hash:
        headers["X-Idempotency-Key"] = payload_hash
        headers["External-Id"] = payload_hash
        
    encoded = None
    if body is not None:
        encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
        
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, data=encoded, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read(2_000_000)
                status = response.getcode()
        except urllib.error.HTTPError as error:
            raw = error.read(64_000)
            status = int(error.code)
            
            # Retry writes ONLY on 429 Rate Limit. Retry reads on 429 and 5xx Server Errors.
            safe_to_retry = status == 429 or (method == "GET" and status in _RETRY_CODES)
            if safe_to_retry and attempt < _MAX_ATTEMPTS:
                time.sleep(_sleep_seconds(error.headers, attempt))
                continue
                
            if status == 429:
                raise ZendeskError(
                    f"Zendesk rate limit persisted after {attempt} attempts; no further requests sent."
                )
            raise ZendeskError(f"Zendesk API HTTP {status}: {_safe_api_message(raw, status)}")
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            if method == "GET" and attempt < _MAX_ATTEMPTS:
                time.sleep(float(2 ** (attempt - 1)))
                continue
            if method == "GET":
                raise ZendeskError(f"Zendesk read failed after {attempt} attempts.")
            raise ZendeskError(
                "Network failed after a Zendesk write was sent; outcome is unknown. "
                "Verify the record in Zendesk before retrying."
            ) from error
            
        try:
            if not raw or raw.strip() == b"":
                return {}, status, attempt
            payload = json.loads(raw.decode("utf-8"))
        except Exception as error:
            raise ZendeskError(
                f"Zendesk returned non-JSON data (HTTP {status}); verify service status."
            ) from error
            
        return payload, status, attempt


# ── TICKETS COMMANDS ────────────────────────────────────────────────────

def zendesk_create_ticket(inputs, stamp):
    payload_hash = _H["airlock_payload_hash"]("jayy/zendesk-integration.create_ticket", inputs)
    
    subject = _clean_text(inputs.get("subject"), "subject", 150)
    comment_body = _clean_text(inputs.get("comment"), "comment", 10000)
    priority = _optional_text(inputs.get("priority"), "priority", 20)
    type_ = _optional_text(inputs.get("type"), "type", 20)
    req_email = _optional_email(inputs.get("requester_email"))
    req_name = _optional_text(inputs.get("requester_name"), "requester_name", 100)
    
    ticket_payload = {
        "subject": subject,
        "comment": {"body": comment_body},
        "external_id": payload_hash
    }
    if priority:
        ticket_payload["priority"] = priority
    if type_:
        ticket_payload["type"] = type_
    if req_email:
        ticket_payload["requester"] = {"email": req_email}
        if req_name:
            ticket_payload["requester"]["name"] = req_name
            
    payload, _, _ = _request("POST", "/api/v2/tickets.json", body={"ticket": ticket_payload}, payload_hash=payload_hash)
    ticket = payload.get("ticket") or {}
    return {
        "ok": True,
        "id": ticket.get("id"),
        "subject": ticket.get("subject"),
        "priority": ticket.get("priority"),
        "type": ticket.get("type")
    }, None


def zendesk_update_ticket(inputs, stamp):
    ticket_id = _positive_id(inputs.get("ticket_id"), "ticket_id")
    status = _optional_text(inputs.get("status"), "status", 20)
    priority = _optional_text(inputs.get("priority"), "priority", 20)
    comment = _optional_text(inputs.get("comment"), "comment", 10000)
    is_private = inputs.get("comment_private")
    if is_private is not None:
        if not isinstance(is_private, bool):
            raise ZendeskError("comment_private must be a boolean")
            
    ticket_payload = {}
    if status:
        ticket_payload["status"] = status
    if priority:
        ticket_payload["priority"] = priority
    if comment:
        ticket_payload["comment"] = {
            "body": comment,
            "public": not is_private
        }
        
    payload, _, _ = _request("PUT", f"/api/v2/tickets/{ticket_id}.json", body={"ticket": ticket_payload})
    ticket = payload.get("ticket") or {}
    return {
        "ok": True,
        "id": ticket.get("id"),
        "status": ticket.get("status"),
        "priority": ticket.get("priority")
    }, None


def zendesk_get_ticket(inputs, stamp):
    ticket_id = _positive_id(inputs.get("ticket_id"), "ticket_id")
    payload, _, _ = _request("GET", f"/api/v2/tickets/{ticket_id}.json")
    ticket = payload.get("ticket") or {}
    return {
        "ok": True,
        "id": ticket.get("id"),
        "subject": ticket.get("subject"),
        "status": ticket.get("status")
    }, None


def zendesk_list_tickets(inputs, stamp):
    params = {}
    status = _optional_text(inputs.get("status"), "status", 20)
    if status:
        params["status"] = status
    limit = inputs.get("limit")
    if limit is not None:
        params["per_page"] = _positive_id(limit, "limit")
        
    payload, _, _ = _request("GET", "/api/v2/tickets.json", params=params)
    tickets = payload.get("tickets") or []
    return {
        "ok": True,
        "tickets": [
            {
                "id": t.get("id"),
                "subject": t.get("subject"),
                "status": t.get("status")
            } for t in tickets
        ]
    }, None


def zendesk_search_tickets(inputs, stamp):
    query = _clean_text(inputs.get("query"), "query", 500)
    payload, _, _ = _request("GET", "/api/v2/search.json", params={"query": f"type:ticket {query}"})
    results = payload.get("results") or []
    return {
        "ok": True,
        "tickets": [
            {
                "id": t.get("id"),
                "subject": t.get("subject"),
                "status": t.get("status")
            } for t in results
        ]
    }, None


def zendesk_delete_ticket(inputs, stamp):
    ticket_id = _positive_id(inputs.get("ticket_id"), "ticket_id")
    _, status, _ = _request("DELETE", f"/api/v2/tickets/{ticket_id}.json")
    return {
        "ok": True,
        "id": ticket_id,
        "deleted": status == 204
    }, None


# ── USERS COMMANDS ──────────────────────────────────────────────────────

def zendesk_create_user(inputs, stamp):
    payload_hash = _H["airlock_payload_hash"]("jayy/zendesk-integration.create_user", inputs)
    
    name = _clean_text(inputs.get("name"), "name", 100)
    email = _email(inputs.get("email"))
    role = _optional_text(inputs.get("role"), "role", 20)
    
    user_payload = {
        "name": name,
        "email": email,
        "external_id": payload_hash
    }
    if role:
        user_payload["role"] = role
        
    payload, _, _ = _request("POST", "/api/v2/users.json", body={"user": user_payload}, payload_hash=payload_hash)
    user = payload.get("user") or {}
    return {
        "ok": True,
        "id": user.get("id"),
        "name": user.get("name"),
        "email": user.get("email"),
        "role": user.get("role")
    }, None


def zendesk_get_user(inputs, stamp):
    user_id = _positive_id(inputs.get("user_id"), "user_id")
    payload, _, _ = _request("GET", f"/api/v2/users/{user_id}.json")
    user = payload.get("user") or {}
    return {
        "ok": True,
        "id": user.get("id"),
        "name": user.get("name"),
        "email": user.get("email")
    }, None


def zendesk_update_user(inputs, stamp):
    user_id = _positive_id(inputs.get("user_id"), "user_id")
    name = _optional_text(inputs.get("name"), "name", 100)
    email = _optional_email(inputs.get("email"))
    role = _optional_text(inputs.get("role"), "role", 20)
    
    user_payload = {}
    if name:
        user_payload["name"] = name
    if email:
        user_payload["email"] = email
    if role:
        user_payload["role"] = role
        
    payload, _, _ = _request("PUT", f"/api/v2/users/{user_id}.json", body={"user": user_payload})
    user = payload.get("user") or {}
    return {
        "ok": True,
        "id": user.get("id"),
        "name": user.get("name"),
        "email": user.get("email"),
        "role": user.get("role")
    }, None


def zendesk_list_users(inputs, stamp):
    params = {}
    role = _optional_text(inputs.get("role"), "role", 20)
    if role:
        params["role"] = role
    limit = inputs.get("limit")
    if limit is not None:
        params["per_page"] = _positive_id(limit, "limit")
        
    payload, _, _ = _request("GET", "/api/v2/users.json", params=params)
    users = payload.get("users") or []
    return {
        "ok": True,
        "users": [
            {
                "id": u.get("id"),
                "name": u.get("name"),
                "email": u.get("email"),
                "role": u.get("role")
            } for u in users
        ]
    }, None


# ── ORGANIZATIONS COMMANDS ──────────────────────────────────────────────

def zendesk_create_organization(inputs, stamp):
    payload_hash = _H["airlock_payload_hash"]("jayy/zendesk-integration.create_organization", inputs)
    name = _clean_text(inputs.get("name"), "name", 150)
    org_payload = {
        "name": name,
        "external_id": payload_hash
    }
    payload, _, _ = _request("POST", "/api/v2/organizations.json", body={"organization": org_payload}, payload_hash=payload_hash)
    org = payload.get("organization") or {}
    return {
        "ok": True,
        "id": org.get("id"),
        "name": org.get("name")
    }, None


def zendesk_get_organization(inputs, stamp):
    org_id = _positive_id(inputs.get("organization_id"), "organization_id")
    payload, _, _ = _request("GET", f"/api/v2/organizations/{org_id}.json")
    org = payload.get("organization") or {}
    return {
        "ok": True,
        "id": org.get("id"),
        "name": org.get("name")
    }, None


def zendesk_list_organizations(inputs, stamp):
    params = {}
    limit = inputs.get("limit")
    if limit is not None:
        params["per_page"] = _positive_id(limit, "limit")
    payload, _, _ = _request("GET", "/api/v2/organizations.json", params=params)
    orgs = payload.get("organizations") or []
    return {
        "ok": True,
        "organizations": [
            {
                "id": o.get("id"),
                "name": o.get("name")
            } for o in orgs
        ]
    }, None


# ── GROUPS COMMANDS ─────────────────────────────────────────────────────

def zendesk_create_group(inputs, stamp):
    payload_hash = _H["airlock_payload_hash"]("jayy/zendesk-integration.create_group", inputs)
    name = _clean_text(inputs.get("name"), "name", 150)
    group_payload = {
        "name": name,
    }
    payload, _, _ = _request("POST", "/api/v2/groups.json", body={"group": group_payload}, payload_hash=payload_hash)
    group = payload.get("group") or {}
    return {
        "ok": True,
        "id": group.get("id"),
        "name": group.get("name")
    }, None


def zendesk_list_groups(inputs, stamp):
    params = {}
    limit = inputs.get("limit")
    if limit is not None:
        params["per_page"] = _positive_id(limit, "limit")
    payload, _, _ = _request("GET", "/api/v2/groups.json", params=params)
    groups = payload.get("groups") or []
    return {
        "ok": True,
        "groups": [
            {
                "id": g.get("id"),
                "name": g.get("name")
            } for g in groups
        ]
    }, None


# ── MACROS COMMANDS ─────────────────────────────────────────────────────

def zendesk_list_macros(inputs, stamp):
    params = {}
    limit = inputs.get("limit")
    if limit is not None:
        params["per_page"] = _positive_id(limit, "limit")
    payload, _, _ = _request("GET", "/api/v2/macros.json", params=params)
    macros = payload.get("macros") or []
    return {
        "ok": True,
        "macros": [
            {
                "id": m.get("id"),
                "title": m.get("title"),
                "active": m.get("active")
            } for m in macros
        ]
    }, None


def zendesk_get_macro(inputs, stamp):
    macro_id = _positive_id(inputs.get("macro_id"), "macro_id")
    payload, _, _ = _request("GET", f"/api/v2/macros/{macro_id}.json")
    macro = payload.get("macro") or {}
    return {
        "ok": True,
        "id": macro.get("id"),
        "title": macro.get("title"),
        "active": macro.get("active")
    }, None


# ── COMPLEX ADVANCED COMMANDS ───────────────────────────────────────────

def zendesk_auto_assign_organization(inputs, stamp):
    """Orchestrated helper to auto-assign a ticket/requester to organization based on email domain."""
    ticket_id = _positive_id(inputs.get("ticket_id"), "ticket_id")
    
    # 1. Fetch ticket with users sideloaded
    payload, _, _ = _request("GET", f"/api/v2/tickets/{ticket_id}.json?include=users")
    ticket = payload.get("ticket") or {}
    users = payload.get("users") or []
    
    requester_id = ticket.get("requester_id")
    if not requester_id:
        raise ZendeskError(f"No requester associated with ticket #{ticket_id}")
        
    requester = next((u for u in users if u.get("id") == requester_id), None)
    if not requester:
        # Fallback to fetch requester directly
        requester_payload, _, _ = _request("GET", f"/api/v2/users/{requester_id}.json")
        requester = requester_payload.get("user") or {}
        
    email = requester.get("email")
    if not email or "@" not in email:
        raise ZendeskError(f"Requester user #{requester_id} has no valid email to derive domain")
        
    domain = email.split("@")[-1].lower().strip()
    
    # Exclude common public email services to avoid wrong clustering
    public_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "mail.com"}
    if domain in public_domains:
        return {
            "ok": False,
            "note": f"Requester domain '{domain}' is a generic public provider; skipped organization routing."
        }, None
        
    # 2. Search if organization with this domain name exists
    org_search, _, _ = _request("GET", "/api/v2/organizations/search.json", params={"name": domain})
    orgs = org_search.get("organizations") or []
    
    org_id = None
    org_name = None
    if orgs:
        org_id = orgs[0].get("id")
        org_name = orgs[0].get("name")
    else:
        # 3. Create organization if missing
        create_payload = {"organization": {"name": domain}}
        new_org, _, _ = _request("POST", "/api/v2/organizations.json", body=create_payload)
        org_id = new_org.get("organization", {}).get("id")
        org_name = new_org.get("organization", {}).get("name")
        
    if not org_id:
        raise ZendeskError("Could not resolve or create organization.")
        
    # 4. Update requester user organization association
    _request("PUT", f"/api/v2/users/{requester_id}.json", body={"user": {"organization_id": org_id}})
    
    # 5. Update ticket organization association
    _request("PUT", f"/api/v2/tickets/{ticket_id}.json", body={"ticket": {"organization_id": org_id}})
    
    return {
        "ok": True,
        "ticket_id": ticket_id,
        "requester_id": requester_id,
        "organization_id": org_id,
        "organization_name": org_name
    }, None


def zendesk_merge_duplicate_tickets(inputs, stamp):
    """Automatically search and merge duplicate tickets for the same requester."""
    ticket_id = _positive_id(inputs.get("ticket_id"), "ticket_id")
    
    # 1. Fetch primary ticket requester
    payload, _, _ = _request("GET", f"/api/v2/tickets/{ticket_id}.json?include=users")
    ticket = payload.get("ticket") or {}
    users = payload.get("users") or []
    
    requester_id = ticket.get("requester_id")
    requester = next((u for u in users if u.get("id") == requester_id), None)
    if not requester and requester_id:
        requester_payload, _, _ = _request("GET", f"/api/v2/users/{requester_id}.json")
        requester = requester_payload.get("user") or {}
        
    email = requester.get("email") if requester else None
    if not email:
        raise ZendeskError(f"Cannot resolve email of requester for ticket #{ticket_id}")
        
    # 2. Search duplicate open tickets from the same user
    search_payload, _, _ = _request("GET", "/api/v2/search.json", params={
        "query": f"type:ticket status<solved requester:{email}"
    })
    results = search_payload.get("results") or []
    
    duplicate_ids = [r.get("id") for r in results if r.get("id") != ticket_id]
    if not duplicate_ids:
        return {
            "ok": True,
            "primary_ticket_id": ticket_id,
            "merged_count": 0,
            "note": "No other open duplicate tickets found for this requester."
        }, None
        
    # 3. Append merge comments on the primary ticket
    duplicate_ids_str = ", ".join(f"#{did}" for did in duplicate_ids)
    primary_update = {
        "ticket": {
            "comment": {
                "body": f"System merged open duplicate tickets: {duplicate_ids_str}.",
                "public": False
            }
        }
    }
    _request("PUT", f"/api/v2/tickets/{ticket_id}.json", body=primary_update)
    
    # 4. Solved and close all duplicate tickets
    for did in duplicate_ids:
        dup_update = {
            "ticket": {
                "status": "solved",
                "comment": {
                    "body": f"Closed as duplicate of primary ticket #{ticket_id}.",
                    "public": True
                }
            }
        }
        _request("PUT", f"/api/v2/tickets/{did}.json", body=dup_update)
        
    return {
        "ok": True,
        "primary_ticket_id": ticket_id,
        "merged_ticket_ids": duplicate_ids,
        "merged_count": len(duplicate_ids)
    }, None


def zendesk_apply_macro_to_ticket(inputs, stamp):
    """Fetch and execute macro actions directly onto a ticket in one transaction."""
    ticket_id = _positive_id(inputs.get("ticket_id"), "ticket_id")
    macro_id = _positive_id(inputs.get("macro_id"), "macro_id")
    
    # 1. Fetch macro actions
    macro_payload, _, _ = _request("GET", f"/api/v2/macros/{macro_id}.json")
    macro = macro_payload.get("macro") or {}
    actions = macro.get("actions") or []
    if not actions:
        raise ZendeskError(f"Macro #{macro_id} has no configured actions")
        
    # 2. Map macro actions to ticket payload
    ticket_payload = {}
    applied_fields = []
    for action in actions:
        field = action.get("field")
        val = action.get("value")
        if not field:
            continue
            
        if field == "status":
            ticket_payload["status"] = str(val)
            applied_fields.append("status")
        elif field == "priority":
            ticket_payload["priority"] = str(val)
            applied_fields.append("priority")
        elif field == "type":
            ticket_payload["type"] = str(val)
            applied_fields.append("type")
        elif field == "comment":
            body = val[0] if isinstance(val, list) and val else str(val)
            ticket_payload["comment"] = {"body": body, "public": True}
            applied_fields.append("comment")
        elif field == "group_id":
            ticket_payload["group_id"] = int(val)
            applied_fields.append("group_id")
        elif field == "assignee_id":
            ticket_payload["assignee_id"] = int(val)
            applied_fields.append("assignee_id")
            
    if not ticket_payload:
        return {
            "ok": False,
            "note": "Macro actions did not map to any supported ticket update fields."
        }, None
        
    # 3. Update the ticket
    _request("PUT", f"/api/v2/tickets/{ticket_id}.json", body={"ticket": ticket_payload})
    
    return {
        "ok": True,
        "ticket_id": ticket_id,
        "macro_id": macro_id,
        "applied_fields": applied_fields
    }, None


def zendesk_generate_support_digest(inputs, stamp):
    """Aggregate search metrics for the last 24h and build a clean support report."""
    # Compute threshold for last 24 hours
    threshold_ts = time.time() - 86400
    threshold_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(threshold_ts))
    
    # Query Zendesk search for tickets created after threshold
    search_payload, _, _ = _request("GET", "/api/v2/search.json", params={
        "query": f"type:ticket created>{threshold_str}"
    })
    results = search_payload.get("results") or []
    
    # Aggregations
    statuses = {"new": 0, "open": 0, "pending": 0, "solved": 0, "closed": 0}
    priorities = {"low": 0, "normal": 0, "high": 0, "urgent": 0}
    
    for item in results:
        st = str(item.get("status") or "").lower()
        pr = str(item.get("priority") or "").lower()
        if st in statuses:
            statuses[st] += 1
        if pr in priorities:
            priorities[pr] += 1
            
    solved_closed = statuses["solved"] + statuses["closed"]
    
    # Render Markdown report digest
    report = (
        f"# 📊 Zendesk Support Digest (Last 24 Hours)\n\n"
        f"**Total Tickets Created**: {len(results)}\n\n"
        f"### 🎫 Status Summary\n"
        f"*   **New**: {statuses['new']}\n"
        f"*   **Open**: {statuses['open']}\n"
        f"*   **Pending**: {statuses['pending']}\n"
        f"*   **Solved & Closed**: {solved_closed}\n\n"
        f"### 🚨 Priority Breakdown\n"
        f"*   **Urgent**: {priorities['urgent']}\n"
        f"*   **High**: {priorities['high']}\n"
        f"*   **Normal**: {priorities['normal']}\n"
        f"*   **Low**: {priorities['low']}\n\n"
        f"*Report compiled automatically by RailCall Governance.*"
    )
    
    return {
        "ok": True,
        "total_tickets": len(results),
        "summary": report
    }, None


def zendesk_bulk_import_tickets(inputs, stamp):
    """Batch-import tickets to Zendesk and poll the background task status."""
    tickets = inputs.get("tickets")
    if not isinstance(tickets, list) or not tickets:
        raise ZendeskError("tickets must be a non-empty array of objects")
    if len(tickets) > 100:
        raise ZendeskError("Bulk import size exceeds maximum allowed (100 items)")
        
    payload_hash = _H["airlock_payload_hash"]("jayy/zendesk-integration.bulk_import_tickets", inputs)
    
    # 1. Post to Zendesk bulk tickets create endpoint
    body = {"tickets": []}
    for idx, t in enumerate(tickets):
        subject = _clean_text(t.get("subject"), f"tickets[{idx}].subject", 150)
        comment = _clean_text(t.get("comment"), f"tickets[{idx}].comment", 10000)
        priority = _optional_text(t.get("priority"), f"tickets[{idx}].priority", 20)
        
        ticket_item = {
            "subject": subject,
            "comment": {"body": comment},
            "external_id": f"{payload_hash}_{idx}"
        }
        if priority:
            ticket_item["priority"] = priority
        body["tickets"].append(ticket_item)
        
    job_payload, _, _ = _request("POST", "/api/v2/tickets/create_many.json", body=body, payload_hash=payload_hash)
    job_status = job_payload.get("job_status") or {}
    job_id = job_status.get("id")
    if not job_id:
        raise ZendeskError("No job status returned from Zendesk Bulk API")
        
    # 2. Poll job status (up to 10 attempts, 2 seconds between checks)
    job_completed = False
    final_status = {}
    for _ in range(10):
        time.sleep(2.0)
        poll_payload, _, _ = _request("GET", f"/api/v2/job_statuses/{job_id}.json")
        status_entry = poll_payload.get("job_status") or {}
        st = status_entry.get("status")
        if st in ("completed", "failed", "killed"):
            job_completed = True
            final_status = status_entry
            break
            
    if not job_completed:
        return {
            "ok": True,
            "job_id": job_id,
            "status": "pending",
            "note": "Bulk job is running in background at Zendesk. Poll the job status manually to retrieve IDs."
        }, None
        
    results = final_status.get("results") or []
    created_ids = [r.get("id") for r in results if r.get("id")]
    
    return {
        "ok": True,
        "job_id": job_id,
        "status": final_status.get("status"),
        "success_count": len(created_ids),
        "created_ids": created_ids
    }, None
