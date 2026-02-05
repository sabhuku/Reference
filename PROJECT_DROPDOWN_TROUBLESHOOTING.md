# Multi-Project UI Troubleshooting Guide

## Why You're Not Seeing the Project Dropdown

The project dropdown **only appears** when BOTH conditions are met:

1. ✅ **You are logged in** (`current_user.is_authenticated`)
2. ✅ **You have at least one project** (`available_projects`)

## Solution Steps

### Step 1: Login to the Application

1. Go to http://127.0.0.1:5000
2. Click "Login" in the top-right
3. Enter your credentials

**Don't have an account?** Click "Sign Up" to create one.

### Step 2: Create Your First Project

Once logged in, you have two options:

**Option A: Via Direct URL**
1. Navigate to http://127.0.0.1:5000/projects
2. You'll see the project management page
3. Enter a project name (e.g., "My First Project")
4. Click "Create"

**Option B: Via Homepage**
After creating a project via `/projects`, the dropdown will appear in the navbar.

### Step 3: Verify the Dropdown

After creating your first project:
1. Go back to http://127.0.0.1:5000 (homepage)
2. **Hard refresh** the page (Ctrl+F5 or Ctrl+Shift+R)
3. You should now see a dropdown button with a folder icon in the navbar
4. It will show your project name

## Expected Behavior

### Before Login
- ❌ No project dropdown visible
- ✅ "Login" and "Sign Up" buttons visible

### After Login (No Projects Yet)
- ❌ No project dropdown visible yet
- ✅ User menu with username visible
- ℹ️ Visit `/projects` to create first project

### After Login (With Projects)
- ✅ Project dropdown visible in navbar
- ✅ Shows current project name
- ✅ Click to switch between projects
- ✅ "Manage Projects" link at bottom of dropdown

## Quick Test

1. **Clear browser cache** (Ctrl+Shift+Delete)
2. **Hard refresh** (Ctrl+F5)
3. **Verify you're logged in** (see your username in top-right)
4. **Create a project** at `/projects`
5. **Return to homepage** and hard refresh

## Still Not Working?

### Check 1: Verify Flask App Restarted
```bash
# You should see this in terminal:
# * Running on http://127.0.0.1:5000
```

### Check 2: Check Browser Console
Press F12 → Console tab → Look for JavaScript errors

### Check 3: Verify Route Exists
Visit http://127.0.0.1:5000/projects directly
- Should redirect to login if not authenticated
- Should show project management page if authenticated

### Check 4: Template Syntax
The dropdown code in `index.html` line 73:
```html
{% if current_user.is_authenticated and available_projects %}
```

This means BOTH must be true!

## Code Location

- **Dropdown Code**: `ui/templates/index.html` (lines 72-102)
- **Context Processor**: `ui/app.py` (line ~1851, function `inject_project_context()`)
- **Routes**: `ui/app.py` (lines 1726-1901)

## Manual Override (For Testing)

If you want to see the dropdown regardless of projects, temporarily change line 73 in `index.html`:

**FROM:**
```html
{% if current_user.is_authenticated and available_projects %}
```

**TO:**
```html
{% if current_user.is_authenticated %}
```

This will show the dropdown even if empty (not recommended for production).
