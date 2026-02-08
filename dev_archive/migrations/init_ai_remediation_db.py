"""
Initialize AI remediation tables in the production database.
"""
import os
import sys

# Ensure project root is in sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ui.app import app, db
# Import AI models to register them with SQLAlchemy
from src.ai_remediation.models import AISuggestion, AppliedSuggestion, FieldProvenance, AuditLog, FeatureFlag, UserFeatureFlag, RolloutCohort, RolloutHistory, MetricsEvent

def init_tables():
    with app.app_context():
        print("Creating AI remediation tables...")
        db.create_all()
        print("✓ Tables created.")
        
        # Enable ai_suggestions feature flag for testing
        flag_name = 'ai_suggestions'
        flag = FeatureFlag.query.get(flag_name)
        if not flag:
            print(f"Initializing feature flag: {flag_name}")
            flag = FeatureFlag(
                flag_name=flag_name,
                enabled=True,
                rollout_percentage=100.0,
                rollout_strategy='percentage',
                description='AI-powered remediation suggestions for Week 5 testing'
            )
            db.session.add(flag)
        else:
            print(f"Updating feature flag: {flag_name}")
            flag.enabled = True
            flag.rollout_percentage = 100.0
        
        db.session.commit()
        print(f"✓ Feature flag '{flag_name}' is now ENABLED (100% rollout).")

if __name__ == "__main__":
    init_tables()
