import http.server
import json
import os
import socket
import sys
import threading
import urllib.parse
import builtins

# Inject mock helper namespace into builtins before importing handler.py
builtins.__rc_helpers__ = {
    "vault_get": lambda key: {
        "subdomain": "127.0.0.1:0",  # Will be overridden in test run
        "email": "test@example.com",
        "api_token": "mocktoken12345"
    } if key == "zendesk" else None,
    "airlock_payload_hash": lambda cmd, inputs: "mock_airlock_hash_val"
}

# Insert the module search path so we can import handlers
sys.path.insert(0, "/home/joshi/railcall-modules/zendesk")
import handlers.handler as handler

# ── MOCK ZENDESK SERVER ────────────────────────────────────────────────

class _MockZendeskHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        pass  # silence log messages
        
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
        
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        
        # Verify authorization
        if not self.headers.get("Authorization"):
            self._send_json(401, {"error": "Missing Authorization header"})
            return
            
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path == "/api/v2/tickets.json":
            ticket = body.get("ticket", {})
            self._send_json(201, {
                "ticket": {
                    "id": 12345,
                    "subject": ticket.get("subject"),
                    "description": ticket.get("comment", {}).get("body"),
                    "priority": ticket.get("priority", "normal"),
                    "type": ticket.get("type", "question")
                }
            })
        elif path == "/api/v2/tickets/create_many.json":
            self._send_json(200, {
                "job_status": {
                    "id": "job_999",
                    "status": "queued"
                }
            })
        elif path == "/api/v2/users.json":
            user = body.get("user", {})
            self._send_json(201, {
                "user": {
                    "id": 999,
                    "name": user.get("name"),
                    "email": user.get("email"),
                    "role": user.get("role", "end-user")
                }
            })
        elif path == "/api/v2/organizations.json":
            org = body.get("organization", {})
            self._send_json(201, {
                "organization": {
                    "id": 111,
                    "name": org.get("name")
                }
            })
        elif path == "/api/v2/groups.json":
            group = body.get("group", {})
            self._send_json(201, {
                "group": {
                    "id": 789,
                    "name": group.get("name")
                }
            })
        else:
            self._send_json(404, {"error": "Not Found"})
            
    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        
        if not self.headers.get("Authorization"):
            self._send_json(401, {"error": "Missing Authorization"})
            return
            
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path.startswith("/api/v2/tickets/") and path.endswith(".json"):
            ticket_id = int(path.split("/")[-1].replace(".json", ""))
            ticket = body.get("ticket", {})
            self._send_json(200, {
                "ticket": {
                    "id": ticket_id,
                    "status": ticket.get("status", "open"),
                    "priority": ticket.get("priority", "normal")
                }
            })
        elif path.startswith("/api/v2/users/") and path.endswith(".json"):
            user_id = int(path.split("/")[-1].replace(".json", ""))
            user = body.get("user", {})
            self._send_json(200, {
                "user": {
                    "id": user_id,
                    "name": user.get("name", "Updated Name"),
                    "email": user.get("email", "updated@example.com"),
                    "role": user.get("role", "end-user")
                }
            })
        else:
            self._send_json(404, {"error": "Not Found"})
            
    def do_GET(self):
        if not self.headers.get("Authorization"):
            self._send_json(401, {"error": "Missing Authorization"})
            return
            
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        
        if path.startswith("/api/v2/tickets/") and path.endswith(".json"):
            ticket_id = int(path.split("/")[-1].replace(".json", ""))
            self._send_json(200, {
                "ticket": {
                    "id": ticket_id,
                    "subject": "Get Ticket Subject",
                    "status": "open",
                    "requester_id": 999
                },
                "users": [
                    {"id": 999, "email": "alice@customer.com", "name": "Alice User"}
                ]
            })
        elif path.startswith("/api/v2/tickets.json"):
            self._send_json(200, {
                "tickets": [
                    {"id": 12345, "subject": "Ticket A", "status": "new"},
                    {"id": 12346, "subject": "Ticket B", "status": "open"}
                ]
            })
        elif path.startswith("/api/v2/organizations/search.json"):
            # Return empty organization list to force creation
            self._send_json(200, {
                "organizations": []
            })
        elif path.startswith("/api/v2/search.json"):
            # Mock return values for search query parameters
            self._send_json(200, {
                "results": [
                    {"id": 12345, "subject": "Search Ticket A", "status": "new", "priority": "urgent"},
                    {"id": 22222, "subject": "Search Ticket B", "status": "open", "priority": "high"}
                ]
            })
        elif path.startswith("/api/v2/users/") and path.endswith(".json"):
            user_id = int(path.split("/")[-1].replace(".json", ""))
            self._send_json(200, {
                "user": {
                    "id": user_id,
                    "name": "Jane Doe",
                    "email": "jane@example.com"
                }
            })
        elif path.startswith("/api/v2/users.json"):
            self._send_json(200, {
                "users": [
                    {"id": 999, "name": "User A", "email": "a@example.com", "role": "end-user"},
                    {"id": 1000, "name": "User B", "email": "b@example.com", "role": "agent"}
                ]
            })
        elif path.startswith("/api/v2/organizations/") and path.endswith(".json"):
            org_id = int(path.split("/")[-1].replace(".json", ""))
            self._send_json(200, {
                "organization": {
                    "id": org_id,
                    "name": "Acme Corp"
                }
            })
        elif path.startswith("/api/v2/organizations.json"):
            self._send_json(200, {
                "organizations": [
                    {"id": 456, "name": "Acme Corp"}
                ]
            })
        elif path.startswith("/api/v2/groups.json"):
            self._send_json(200, {
                "groups": [
                    {"id": 789, "name": "Support Group"}
                ]
            })
        elif path.startswith("/api/v2/macros/") and path.endswith(".json"):
            macro_id = int(path.split("/")[-1].replace(".json", ""))
            self._send_json(200, {
                "macro": {
                    "id": macro_id,
                    "title": "Welcome Macro",
                    "active": True,
                    "actions": [
                        {"field": "status", "value": "solved"},
                        {"field": "comment", "value": ["Macro comment text"]}
                    ]
                }
            })
        elif path.startswith("/api/v2/macros.json"):
            self._send_json(200, {
                "macros": [
                    {"id": 321, "title": "Macro A", "active": True}
                ]
            })
        elif path.startswith("/api/v2/job_statuses/"):
            job_id = path.split("/")[-1].replace(".json", "")
            self._send_json(200, {
                "job_status": {
                    "id": job_id,
                    "status": "completed",
                    "results": [
                        {"id": 33333},
                        {"id": 44444}
                    ]
                }
            })
        else:
            self._send_json(404, {"error": "Not Found"})
            
    def do_DELETE(self):
        if not self.headers.get("Authorization"):
            self._send_json(401, {"error": "Missing Authorization"})
            return
            
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path.startswith("/api/v2/tickets/") and path.endswith(".json"):
            # Return 204 No Content for delete success
            self.send_response(204)
            self.end_headers()
        else:
            self._send_json(404, {"error": "Not Found"})


def _run_mock_server():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    
    server = http.server.HTTPServer(("127.0.0.1", port), _MockZendeskHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


# ── TESTS ──────────────────────────────────────────────────────────────

def test_all():
    server, port = _run_mock_server()
    mock_host = f"127.0.0.1:{port}"
    print(f"Mock server running on http://{mock_host}")
    
    # Inject __rc_helpers__ into handler namespace (Vault mock)
    builtins.__rc_helpers__["vault_get"] = lambda key: {
        "subdomain": mock_host,
        "email": "test@example.com",
        "api_token": "mocktoken12345"
    } if key == "zendesk" else None
    handler._H = builtins.__rc_helpers__
    
    # 1. create_ticket
    print("Testing create_ticket...")
    ticket, _ = handler.zendesk_create_ticket({
        "subject": "Help with login",
        "comment": "Cannot sign into my account",
        "priority": "high",
        "type": "task"
    }, "stamp")
    assert ticket["id"] == 12345
    assert ticket["subject"] == "Help with login"
    
    # 2. update_ticket
    print("Testing update_ticket...")
    updated, _ = handler.zendesk_update_ticket({
        "ticket_id": 12345,
        "status": "solved",
        "priority": "normal",
        "comment": "Issue fixed!"
    }, "stamp")
    assert updated["id"] == 12345
    assert updated["status"] == "solved"
    
    # 3. get_ticket
    print("Testing get_ticket...")
    fetched, _ = handler.zendesk_get_ticket({"ticket_id": 12345}, "stamp")
    assert fetched["id"] == 12345
    assert fetched["status"] == "open"
    
    # 4. list_tickets
    print("Testing list_tickets...")
    tickets_res, _ = handler.zendesk_list_tickets({"status": "open", "limit": 2}, "stamp")
    assert len(tickets_res["tickets"]) == 2
    
    # 5. search_tickets
    print("Testing search_tickets...")
    search_res, _ = handler.zendesk_search_tickets({"query": "login"}, "stamp")
    assert len(search_res["tickets"]) == 2
    assert search_res["tickets"][0]["subject"] == "Search Ticket A"
    
    # 6. delete_ticket
    print("Testing delete_ticket...")
    deleted_res, _ = handler.zendesk_delete_ticket({"ticket_id": 12345}, "stamp")
    assert deleted_res["deleted"] is True
    
    # 7. create_user
    print("Testing create_user...")
    user, _ = handler.zendesk_create_user({
        "name": "Jane Doe",
        "email": "jane@example.com",
        "role": "agent"
    }, "stamp")
    assert user["id"] == 999
    assert user["role"] == "agent"
    
    # 8. get_user
    print("Testing get_user...")
    user_res, _ = handler.zendesk_get_user({"user_id": 999}, "stamp")
    assert user_res["id"] == 999
    assert user_res["name"] == "Jane Doe"
    
    # 9. update_user
    print("Testing update_user...")
    user_upd, _ = handler.zendesk_update_user({
        "user_id": 999,
        "name": "Jane updated"
    }, "stamp")
    assert user_upd["id"] == 999
    
    # 10. list_users
    print("Testing list_users...")
    users_res, _ = handler.zendesk_list_users({"role": "agent"}, "stamp")
    assert len(users_res["users"]) == 2
    
    # 11. create_organization
    print("Testing create_organization...")
    org, _ = handler.zendesk_create_organization({"name": "Acme Corp"}, "stamp")
    assert org["id"] == 111
    
    # 12. get_organization
    print("Testing get_organization...")
    org_res, _ = handler.zendesk_get_organization({"organization_id": 456}, "stamp")
    assert org_res["id"] == 456
    
    # 13. list_organizations
    print("Testing list_organizations...")
    orgs_res, _ = handler.zendesk_list_organizations({"limit": 5}, "stamp")
    assert len(orgs_res["organizations"]) == 1
    
    # 14. create_group
    print("Testing create_group...")
    group, _ = handler.zendesk_create_group({"name": "Support Group"}, "stamp")
    assert group["id"] == 789
    
    # 15. list_groups
    print("Testing list_groups...")
    groups_res, _ = handler.zendesk_list_groups({"limit": 5}, "stamp")
    assert len(groups_res["groups"]) == 1
    
    # 16. list_macros
    print("Testing list_macros...")
    macros_res, _ = handler.zendesk_list_macros({"limit": 5}, "stamp")
    assert len(macros_res["macros"]) == 1
    
    # 17. get_macro
    print("Testing get_macro...")
    macro_res, _ = handler.zendesk_get_macro({"macro_id": 321}, "stamp")
    assert macro_res["id"] == 321
    assert macro_res["active"] is True
    
    # 18. auto_assign_organization
    print("Testing auto_assign_organization...")
    assign_res, _ = handler.zendesk_auto_assign_organization({"ticket_id": 12345}, "stamp")
    assert assign_res["ok"] is True
    assert assign_res["organization_id"] == 111
    assert assign_res["organization_name"] == "customer.com"
    
    # 19. merge_duplicate_tickets
    print("Testing merge_duplicate_tickets...")
    merge_res, _ = handler.zendesk_merge_duplicate_tickets({"ticket_id": 12345}, "stamp")
    assert merge_res["ok"] is True
    assert merge_res["merged_count"] == 1
    assert merge_res["merged_ticket_ids"] == [22222]
    
    # 20. apply_macro_to_ticket
    print("Testing apply_macro_to_ticket...")
    macro_apply_res, _ = handler.zendesk_apply_macro_to_ticket({
        "ticket_id": 12345,
        "macro_id": 321
    }, "stamp")
    assert macro_apply_res["ok"] is True
    assert "status" in macro_apply_res["applied_fields"]
    
    # 21. generate_support_digest
    print("Testing generate_support_digest...")
    digest_res, _ = handler.zendesk_generate_support_digest({}, "stamp")
    assert digest_res["ok"] is True
    assert digest_res["total_tickets"] == 2
    assert "Zendesk Support Digest" in digest_res["summary"]
    
    # 22. bulk_import_tickets
    print("Testing bulk_import_tickets...")
    bulk_res, _ = handler.zendesk_bulk_import_tickets({
        "tickets": [
            {"subject": "Bulk A", "comment": "Comment A"},
            {"subject": "Bulk B", "comment": "Comment B"}
        ]
    }, "stamp")
    assert bulk_res["ok"] is True
    assert bulk_res["success_count"] == 2
    assert bulk_res["created_ids"] == [33333, 44444]

    print("\nAll 22 Zendesk operations (including 5 advanced flows) passed verification successfully! 🚀")


if __name__ == '__main__':
    test_all()
