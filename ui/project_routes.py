# ============================================================================
# PROJECT MANAGEMENT ROUTES
# ============================================================================

@app.route('/projects')
@login_required
def manage_projects():
    """Project management page for authenticated users."""
    from ui.database import Project, ProjectReference
    
    # Get all projects for current user
    projects = Project.query.filter_by(user_id=current_user.id).all()
    
    # Convert to dictionaries with stats
    project_list = [p.to_dict() for p in projects]
    
    return render_template('projects.html', projects=project_list)


@app.route('/projects/create', methods=['POST'])
@login_required
def create_project():
    """Create a new project for the authenticated user."""
    from ui.database import Project, db as project_db
    
    project_name = request.form.get('project_name', '').strip()
    if not project_name:
        flash('Project name is required', 'error')
        return redirect(url_for('manage_projects'))
    
    # Generate unique ID from name
    import re
    project_id = re.sub(r'[^a-z0-9_]', '_', project_name.lower())
    project_id = f"{current_user.id}_{project_id}"
    
    # Check if project already exists
    existing = Project.query.filter_by(id=project_id).first()
    if existing:
        flash(f'Project with similar name already exists', 'error')
        return redirect(url_for('manage_projects'))
    
    try:
        project = Project(
            id=project_id,
            user_id=current_user.id,
            name=project_name
        )
        project_db.session.add(project)
        project_db.session.commit()
        
        flash(f'Project "{project_name}" created successfully', 'success')
        # Auto-switch to new project
        session['current_project_id'] = project_id
    except Exception as e:
        project_db.session.rollback()
        app.logger.error(f"Error creating project: {e}")
        flash('Error creating project', 'error')
    
    return redirect(url_for('manage_projects'))


@app.route('/projects/<project_id>/switch')
@login_required
def switch_project(project_id):
    """Switch to a different project."""
    from ui.database import Project
    
    # Verify project belongs to user
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('manage_projects'))
    
    session['current_project_id'] = project_id
    flash(f'Switched to project "{project.name}"', 'success')
    return redirect(url_for('index'))


@app.route('/projects/<project_id>/rename', methods=['POST'])
@login_required
def rename_project(project_id):
    """Rename a project."""
    from ui.database import Project, db as project_db
    
    data = request.get_json() if request.is_json else {}
    new_name = data.get('name', '').strip()
    
    if not new_name:
        return jsonify({'success': False, 'error': 'Name is required'}), 400
    
    # Verify project belongs to user
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        return jsonify({'success': False, 'error': 'Project not found'}), 404
    
    try:
        project.name = new_name
        project_db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        project_db.session.rollback()
        app.logger.error(f"Error renaming project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/projects/<project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    """Delete a project and all its references."""
    from ui.database import Project, db as project_db
    
    # Verify project belongs to user
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        return jsonify({'success': False, 'error': 'Project not found'}), 404
    
    try:
        project_name = project.name
        project_db.session.delete(project)
        project_db.session.commit()
        
        # If this was the current project, switch to another
        if session.get('current_project_id') == project_id:
            remaining = Project.query.filter_by(user_id=current_user.id).first()
            session['current_project_id'] = remaining.id if remaining else None
        
        return jsonify({'success': True, 'message': f'Deleted project "{project_name}"'})
    except Exception as e:
        project_db.session.rollback()
        app.logger.error(f"Error deleting project: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# PROJECT CONTEXT PROCESSOR
# ============================================================================

@app.context_processor
def inject_project_context():
    """Inject current project data into all templates."""
    if not current_user.is_authenticated:
        return {
            'current_project': None,
            'available_projects': []
        }
    
    from ui.database import Project
    
    # Get current project ID from session
    current_project_id = session.get('current_project_id')
    
    # Get all projects for user
    all_projects = Project.query.filter_by(user_id=current_user.id).all()
    
    # If no current project or doesn't exist, use first available
    current_project = None
    if current_project_id:
        current_project = Project.query.filter_by(
            id=current_project_id, 
            user_id=current_user.id
        ).first()
    
    if not current_project and all_projects:
        current_project = all_projects[0]
        session['current_project_id'] = current_project.id
    
    # Convert to dicts for template
    return {
        'current_project': current_project.to_dict() if current_project else None,
        'available_projects': [p.to_dict() for p in all_projects]
    }


