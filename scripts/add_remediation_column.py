import sqlite3
import os

# Database path - Flask instance folder usually
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'references.db')

def migrate_db():
    print(f"Connecting to database at {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database file not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tables to update
    tables = ['project_references', 'references']
    
    for table in tables:
        print(f"Checking table '{table}'...")
        try:
            # Check if column exists - QUOTE table name
            cursor.execute(f'PRAGMA table_info("{table}")')
            columns = [info[1] for info in cursor.fetchall()]
            
            if 'remediation' not in columns:
                print(f"Adding 'remediation' column to '{table}'...")
                cursor.execute(f'ALTER TABLE "{table}" ADD COLUMN remediation JSON')
                print(f"Column added to '{table}'.")
            else:
                print(f"Column 'remediation' already exists in '{table}'.")
                
        except Exception as e:
            print(f"Error processing table '{table}': {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_db()
