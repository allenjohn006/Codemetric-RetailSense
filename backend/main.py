from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import hash_password
from config import settings
from database import engine, Base, SessionLocal
from models import User
from routers import auth_router, upload_router, report_router, analyze_router

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed demo account
    db = SessionLocal()
    try:
        demo_user = db.query(User).filter(User.email == settings.DEMO_EMAIL).first()
        if not demo_user:
            print(f"Creating demo user: {settings.DEMO_EMAIL}")
            user = User(
                email=settings.DEMO_EMAIL,
                full_name="Demo User",
                hashed_password=hash_password(settings.DEMO_PASSWORD),
                is_demo=True,
            )
            db.add(user)
            db.commit()
    except Exception as e:
        print(f"Failed to seed demo user: {e}")
    finally:
        db.close()
    
    yield
    # Shutdown


app = FastAPI(
    title="RetailSense API",
    description="Backend API for RetailSense analytics and forecasting platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev. Restrict in prod.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(upload_router.router)
app.include_router(report_router.router)
app.include_router(analyze_router.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "RetailSense API is running"}
