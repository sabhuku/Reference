"""
Script to update index.html and app.py for always-visible projects dropdown
"""
import re

# Fix 1: Update index.html - remove 'and available_projects' condition
print("Updating index.html...")
with open('ui/templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the condition
old_condition = '{% if current_user.is_authenticated and available_projects %}'
new_condition = '{% if current_user.is_authenticated %}'

if old_condition in content:
    content = content.replace(old_condition, new_condition)
    
    with open('ui/templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("[PASS] Updated index.html dropdown condition")
else:
    print("[SKIP] Condition already updated or not found")

# Fix 2: Add Projects card to quick actions (if not already present)
print("\nAdding Projects card to homepage...")
with open('ui/templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

projects_card_html = '''      {% if current_user.is_authenticated %}
      <div class="col-md-3">
        <a href="{{ url_for('manage_projects') }}" class="text-decoration-none">
          <div class="card quick-action-card shadow-sm p-4 text-center h-100">
            <div class="card-body">
              <i class="bi bi-folder2-open feature-icon text-primary"></i>
              <h5 class="card-title text-dark">Projects</h5>
              <p class="card-text text-muted small">Organize references into projects.</p>
            </div>
          </div>
        </a>
      </div>
      {% endif %}'''

if 'manage_projects' not in content:
    # Find the closing </div> before Recent Activity
    marker = '    </div>\n\n    <!-- Recent Activity -->'
    if marker in content:
        content = content.replace(marker, projects_card_html + '\n' + marker)
        
        with open('ui/templates/index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("[PASS] Added Projects card to homepage")
    else:
        print("[WARN] Could not find insertion point for Projects card")
else:
    print("[SKIP] Projects card already present")

print("\nUpdates complete! Restart Flask app to see changes.")
