from app import create_app, db

print("🔄 Initializing app context...")
app = create_app()

with app.app_context():
    print("🗑️  Dropping all tables (to ensure clean slate)...")
    try:
        db.drop_all()
    except Exception as e:
        print(f"⚠️  Drop failed (might be empty): {e}")

    print("✨ Creating all tables...")
    db.create_all()
    print("✅ Database successfully recreated via SQLAlchemy!")
