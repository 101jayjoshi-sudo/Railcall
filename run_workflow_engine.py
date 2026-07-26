import json
import os
import sys

# Add station workbench to path to import flow_engine
sys.path.insert(0, "/home/joshi/.railcall/station/workbench")
import flow_engine

def run_test():
    spec_path = "/home/joshi/.railcall/station/tests/workflow_zendesk_support_triage_receipt.json"
    csv_path = "/home/joshi/.railcall/station/fixtures/zendesk_leads.csv"
    
    with open(spec_path, "r", encoding="utf-8") as f:
        spec_data = json.load(f)
    spec = spec_data["spec"]
    
    with open(csv_path, "r", encoding="utf-8") as f:
        csv_text = f.read()
        
    rows = flow_engine.rows_from_csv(csv_text)
    res = flow_engine.run_spec(spec, rows, "2026-07-26T21:30:00Z")
    
    print("Workflow Execution Results:")
    print(json.dumps(res, indent=2))
    
    # Assertions
    records = res["records"]
    assert len(records) == 3
    
    # Alice Smith: status = "new" -> Should route to "Create Zendesk user"
    assert records[0]["name"] == "Alice Smith"
    assert records[0]["current_stage"] == "Create Zendesk user"
    assert records[0]["status"] == "queued"
    assert records[0]["bound_command"] == "jayy/zendesk.create_user"
    
    # Bob Jones: status = "escalated" -> Should route to "Create Zendesk ticket"
    assert records[1]["name"] == "Bob Jones"
    assert records[1]["current_stage"] == "Create Zendesk ticket"
    assert records[1]["status"] == "queued"
    assert records[1]["bound_command"] == "jayy/zendesk.create_ticket"
    
    # Charlie Brown: status = "resolved" -> stage_map has resolved: null -> Should be terminal
    assert records[2]["name"] == "Charlie Brown"
    assert records[2]["current_stage"] == "— (terminal)"
    assert records[2]["status"] == "terminal_stage"
    
    print("\n✓ Workflow engine executed and correctly routed all records! 🚀")

if __name__ == '__main__':
    run_test()
