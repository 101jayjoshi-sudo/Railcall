"""
Zendesk Module Handlers.
Exposes ticket and user actions under governed local-first rules.
"""
import base64
import json
import urllib.request
import os

def _get_credentials():
    helpers = globals().get("__rc_helpers__", {})
    vault_get = helpers.get("vault_get")
    creds = vault_get("jayy/zendesk") if vault_get else None
    
    subdomain = None
    email = None
    token = None
    
    if isinstance(creds, dict):
        subdomain = creds.get("ZENDESK_SUBDOMAIN")
        email = creds.get("ZENDESK_EMAIL")
        token = creds.get("ZENDESK_API_TOKEN")
        
    subdomain = subdomain or os.environ.get("ZENDESK_SUBDOMAIN")
    email = email or os.environ.get("ZENDESK_EMAIL")
    token = token or os.environ.get("ZENDESK_API_TOKEN")
    
    if not (subdomain and email and token):
        raise ValueError("Missing Zendesk credentials. Ensure ZENDESK_SUBDOMAIN, ZENDESK_EMAIL, and ZENDESK_API_TOKEN are configured.")
    return subdomain, email, token

def _request(method: str, path: str, body_dict: dict = None) -> dict:
    subdomain, email, token = _get_credentials()
    
    base_url = os.environ.get("ZENDESK_API_BASE_URL")
    if base_url:
        url = base_url.rstrip("/") + path
    else:
        url = f"https://{subdomain}.zendesk.com/api/v2{path}"
        
    auth_str = f"{email}/token:{token}"
    auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "RailCall-ZendeskModule/1.0"
    }
    
    data = json.dumps(body_dict).encode("utf-8") if body_dict is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            err_body = ""
        raise RuntimeError(f"Zendesk HTTP {e.code} on {method} {path}: {err_body}")
    except Exception as e:
        raise RuntimeError(f"Zendesk connection failure on {method} {path}: {e!r}")

# --- Command Handlers ---

def zendesk_create_ticket(inputs: dict, context: str) -> dict:
    ticket_payload = {
        "ticket": {
            "subject": inputs["subject"],
            "comment": {"body": inputs["comment"]}
        }
    }
    if inputs.get("priority"):
        ticket_payload["ticket"]["priority"] = inputs["priority"]
    if inputs.get("type"):
        ticket_payload["ticket"]["type"] = inputs["type"]
    if inputs.get("requester_email"):
        ticket_payload["ticket"]["requester"] = {
            "email": inputs["requester_email"],
            "name": inputs.get("requester_name", inputs["requester_email"])
        }
    res = _request("POST", "/tickets.json", ticket_payload)
    return (res.get("ticket") or res), None

def zendesk_update_ticket(inputs: dict, context: str) -> dict:
    ticket_payload = {"ticket": {}}
    if inputs.get("status"):
        ticket_payload["ticket"]["status"] = inputs["status"]
    if inputs.get("priority"):
        ticket_payload["ticket"]["priority"] = inputs["priority"]
    if inputs.get("comment"):
        ticket_payload["ticket"]["comment"] = {
            "body": inputs["comment"],
            "public": not bool(inputs.get("comment_private"))
        }
    res = _request("PUT", f"/tickets/{inputs['ticket_id']}.json", ticket_payload)
    return (res.get("ticket") or res), None

def zendesk_get_ticket(inputs: dict, context: str) -> dict:
    res = _request("GET", f"/tickets/{inputs['ticket_id']}.json")
    return (res.get("ticket") or res), None

def zendesk_list_tickets(inputs: dict, context: str) -> dict:
    path = "/tickets.json"
    params = []
    if inputs.get("status"):
        params.append(f"status={inputs['status']}")
    limit = inputs.get("limit", 20)
    params.append(f"per_page={limit}")
    if params:
        path += "?" + "&".join(params)
    res = _request("GET", path)
    return {"tickets": res.get("tickets") or []}, None

def zendesk_create_user(inputs: dict, context: str) -> dict:
    user_payload = {
        "user": {
            "name": inputs["name"],
            "email": inputs["email"],
            "role": inputs.get("role", "end-user")
        }
    }
    res = _request("POST", "/users.json", user_payload)
    return (res.get("user") or res), None

def zendesk_list_users(inputs: dict, context: str) -> dict:
    path = "/users.json"
    params = []
    if inputs.get("role"):
        params.append(f"role={inputs['role']}")
    limit = inputs.get("limit", 20)
    params.append(f"per_page={limit}")
    if params:
        path += "?" + "&".join(params)
    res = _request("GET", path)
    return {"users": res.get("users") or []}, None
