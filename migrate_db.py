import sqlite3
import os

# Path to the database - checking both potential locations
db_paths = ["nightlife.db", "instance/nightlife.db"]
db_path = None

for path in db_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    print("❌ Could not find database file!")
    exit(1)

print(f"🔧 Fixing database at: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get existing columns
    cursor.execute("PRAGMA table_info(event)")
    columns = [info[1] for info in cursor.fetchall()]
    
    # 1. Add status column if missing
    if "status" not in columns:
        print("  → Adding 'status' column...")
        cursor.execute("ALTER TABLE event ADD COLUMN status VARCHAR(20) DEFAULT 'approved'")
    else:
        print("  ✓ 'status' column already exists")
        
    # 2. Add suggested_by_id column if missing
    if "suggested_by_id" not in columns:
        print("  → Adding 'suggested_by_id' column...")
        cursor.execute("ALTER TABLE event ADD COLUMN suggested_by_id INTEGER")
    else:
        print("  ✓ 'suggested_by_id' column already exists")

    # 3. Create user table if missing (might be missing if dropping failed)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
    if not cursor.fetchone():
        print("  → Creating 'user' table...")
        cursor.execute("""
            CREATE TABLE user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80) NOT NULL UNIQUE,
                password_hash VARCHAR(120),
                role VARCHAR(20) DEFAULT 'user',
                okta_user_id VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        print("  ✓ 'user' table already exists")

    conn.commit()
    conn.close()
    print("✅ Database schema successfully migrated!")

except Exception as e:
    print(f"❌ Error updating database: {e}")
