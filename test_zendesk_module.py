import http.server
import json
import os
import socket
import sys
import threading
import urllib.request

# Insert the module search path so we can import handlers
sys.path.insert(0, "/home/joshi/railcall-modules/zendesk")
import handlers.handler as handler

# ----------------- Mock Zendesk Server -----------------

class _MockZendeskHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        pass  # silence logs
        
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
        
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        
        if self.path == "/tickets.json":
            ticket = body.get("ticket", {})
            self._send_json(201, {
                "ticket": {
                    "id": 12345,
                    "subject": ticket.get("subject"),
                    "description": ticket.get("comment", {}).get("body"),
                    "priority": ticket.get("priority", "normal"),
                    "type": ticket.get("type", "question"),
                    "requester_id": 999
                }
            })
        elif self.path == "/users.json":
            user = body.get("user", {})
            self._send_json(201, {
                "user": {
                    "id": 999,
                    "name": user.get("name"),
                    "email": user.get("email"),
                    "role": user.get("role", "end-user")
                }
            })
        else:
            self._send_json(404, {"error": "Not Found"})
            
    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        
        if self.path.startswith("/tickets/") and self.path.endswith(".json"):
            ticket_id = int(self.path.split("/")[-1].replace(".json", ""))
            ticket = body.get("ticket", {})
            self._send_json(200, {
                "ticket": {
                    "id": ticket_id,
                    "subject": "Updated Ticket Subject",
                    "status": ticket.get("status", "open"),
                    "priority": ticket.get("priority", "normal"),
                    "comment": ticket.get("comment", {}).get("body")
                }
            })
        else:
            self._send_json(404, {"error": "Not Found"})
            
    def do_GET(self):
        if self.path.startswith("/tickets/") and self.path.endswith(".json"):
            ticket_id = int(self.path.split("/")[-1].replace(".json", ""))
            self._send_json(200, {
                "ticket": {
                    "id": ticket_id,
                    "subject": "Sample Get Ticket Subject",
                    "status": "open",
                    "priority": "normal"
                }
            })
        elif self.path.startswith("/tickets.json"):
            self._send_json(200, {
                "tickets": [
                    {"id": 12345, "subject": "Ticket A", "status": "new"},
                    {"id": 12346, "subject": "Ticket B", "status": "open"}
                ]
            })
        elif self.path.startswith("/users.json"):
            self._send_json(200, {
                "users": [
                    {"id": 999, "name": "User A", "email": "a@example.com"},
                    {"id": 1000, "name": "User B", "email": "b@example.com"}
                ]
            })
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

# ----------------- Tests -----------------

def test_all():
    server, port = _run_mock_server()
    mock_url = f"http://127.0.0.1:{port}"
    print(f"Mock server running on {mock_url}")
    
    # Configure env vars for credentials and URL override
    os.environ["ZENDESK_API_BASE_URL"] = mock_url
    os.environ["ZENDESK_SUBDOMAIN"] = "mock-domain"
    os.environ["ZENDESK_EMAIL"] = "test@example.com"
    os.environ["ZENDESK_API_TOKEN"] = "mocktoken"
    
    # 1. Test create_ticket
    print("Testing zendesk_create_ticket...")
    ticket, _ = handler.zendesk_create_ticket({
        "subject": "Help with login",
        "comment": "I cannot sign into my account",
        "priority": "high",
        "type": "task"
    }, "context_ts")
    assert ticket["id"] == 12345
    assert ticket["subject"] == "Help with login"
    assert ticket["priority"] == "high"
    print("✓ zendesk_create_ticket passed!")
    
    # 2. Test update_ticket
    print("Testing zendesk_update_ticket...")
    updated, _ = handler.zendesk_update_ticket({
        "ticket_id": 12345,
        "status": "solved",
        "comment": "This is now resolved"
    }, "context_ts")
    assert updated["id"] == 12345
    assert updated["status"] == "solved"
    print("✓ zendesk_update_ticket passed!")
    
    # 3. Test get_ticket
    print("Testing zendesk_get_ticket...")
    fetched, _ = handler.zendesk_get_ticket({"ticket_id": 12345}, "context_ts")
    assert fetched["id"] == 12345
    assert fetched["status"] == "open"
    print("✓ zendesk_get_ticket passed!")
    
    # 4. Test list_tickets
    print("Testing zendesk_list_tickets...")
    tickets_res, _ = handler.zendesk_list_tickets({"status": "open", "limit": 5}, "context_ts")
    assert len(tickets_res["tickets"]) == 2
    assert tickets_res["tickets"][0]["id"] == 12345
    print("✓ zendesk_list_tickets passed!")
    
    # 5. Test create_user
    print("Testing zendesk_create_user...")
    user, _ = handler.zendesk_create_user({
        "name": "John Doe",
        "email": "john@example.com",
        "role": "agent"
    }, "context_ts")
    assert user["id"] == 999
    assert user["name"] == "John Doe"
    assert user["role"] == "agent"
    print("✓ zendesk_create_user passed!")
    
    # 6. Test list_users
    print("Testing zendesk_list_users...")
    users_res, _ = handler.zendesk_list_users({"role": "end-user"}, "context_ts")
    assert len(users_res["users"]) == 2
    assert users_res["users"][0]["name"] == "User A"
    print("✓ zendesk_list_users passed!")
    
    print("\nAll 6 Zendesk operations passed verification successfully! 🚀")

if __name__ == '__main__':
    test_all()
