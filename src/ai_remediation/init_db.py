"""
Database Initialization Script for AI Remediation System

Run this script to create all AI remediation tables in your existing database.

Usage:
    python -m src.ai_remediation.init_db
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ui.app import create_app
from ui.database import db
from src.ai_remediation.models import (
    AISuggestion,
    AppliedSuggestion,
    FieldProvenance,
    AuditLog,
    FeatureFlag,
    UserFeatureFlag,
    RolloutCohort,
    RolloutHistory,
    MetricsEvent,
    init_ai_tables
)


def main():
    """Initialize AI remediation tables."""
    print("=" * 60)
    print("AI Remediation System - Database Initialization")
    print("=" * 60)
    print()
    
    # Create Flask app
    app = create_app()
    
    print("Creating AI remediation tables...")
    print()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # List of new tables
        tables = [
            'ai_suggestions',
            'applied_suggestions',
            'field_provenance',
            'audit_log',
            'feature_flags',
            'user_feature_flags',
            'rollout_cohorts',
            'rollout_history',
            'metrics_events'
        ]
        
        for table in tables:
            print(f"✓ Created table: {table}")
        
        print()
        
        # Create default feature flag
        existing_flag = FeatureFlag.query.filter_by(flag_name='ai_suggestions').first()
        
        if not existing_flag:
            flag = FeatureFlag(
                flag_name='ai_suggestions',
                enabled=False,
                rollout_percentage=0.0,
                description='AI-powered remediation suggestions (suggest-only mode)'
            )
            db.session.add(flag)
            db.session.commit()
            print("✓ Created 'ai_suggestions' feature flag (DISABLED by default)")
        else:
            print("✓ Feature flag 'ai_suggestions' already exists")
        
        print()
        print("=" * 60)
        print("Database initialization complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Review protected fields policy in src/ai_remediation/protected_fields.py")
        print("2. Implement Tier 0 deterministic fixes")
        print("3. Build validation pipeline")
        print()
        print("⚠️  AI suggestions are DISABLED by default")
        print("    Do NOT enable until Phase 3 (Shadow Mode Testing)")
        print()


if __name__ == '__main__':
    main()
