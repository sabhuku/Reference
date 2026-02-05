from ui.app import app, db
import json
from src.reference_manager import ReferenceManager
import hashlib

def get_compliance_hash():
    with app.app_context():
        rm = ReferenceManager(db.session)
        # Get first available project
        projects = rm.project_manager.get_projects()
        if not projects:
            return "empty", "{}"
        project_id = projects[0].id
        pubs = rm.get_project_references(project_id)
        if not pubs:
             return "empty_refs", "{}"
        pubs.sort(key=lambda x: x.id) 
        result = rm.check_style_compliance(pubs)
        data_snapshot = {
            'overall_score': result['report'].overall_compliance_score,
            'results': [
                {'id': r.id, 'score': r.compliance_score} for r in result['results']
            ]
        }
        json_str = json.dumps(data_snapshot, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest(), json_str

print("Running compliance determinism check...")
hash1, json1 = get_compliance_hash()
hash2, json2 = get_compliance_hash()

if hash1 == hash2:
    print("SUCCESS: Compliance output is deterministic.")
else:
    print("FAILURE: Compliance output changed!")
