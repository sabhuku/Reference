from ui.app import app
from ui.database import db, Project, ProjectReference, Bibliography, Reference as DBReference
from flask_login import login_user
from flask import session

with app.app_context():
    # Simulate user 1
    from ui.database import User
    user = User.query.get(1)
    if not user:
        print("User 1 not found")
        exit()

    with app.test_request_context('/'):
        login_user(user)
        # Ensure session have current_project_id
        project = Project.query.filter_by(user_id=user.id).first()
        if project:
            session['current_project_id'] = project.id
            print(f"Triggering migration for project: {project.id}")
            
            # Call index() via the app's view functions
            from ui.app import index
            response = index()
            print("Migration attempt complete.")

    # Re-verify counts
    print('--- Post-Migration Status ---')
    print('Projects:', Project.query.count())
    print('Project Refs:', ProjectReference.query.count())
    for p in Project.query.all():
        print(f"Project: {p.name} ({p.id}), Refs: {len(p.project_references)}")
