#!/usr/bin/env python3
"""Script to create demo user in the database."""

import sys
sys.path.insert(0, '/app')

from database import SessionLocal, Base, engine
from models import User
from auth import hash_password
from config import settings

# Create tables
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()

try:
    # Check if demo user exists
    demo_user = db.query(User).filter(User.email == settings.DEMO_EMAIL).first()
    if demo_user:
        print(f"Demo user already exists: {settings.DEMO_EMAIL}")
    else:
        # Create demo user
        user = User(
            email=settings.DEMO_EMAIL,
            full_name="Demo User",
            hashed_password=hash_password(settings.DEMO_PASSWORD),
            is_demo=True,
        )
        db.add(user)
        db.commit()
        print(f"Demo user created: {settings.DEMO_EMAIL}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
