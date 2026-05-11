import os
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from database import engine, Base, SessionLocal
import models
from routers import auth, posts, comments, admin, awards
from routers.marks import router as marks_router, admin_router as marks_admin_router
from routers.emis import router as emis_router, seed_emis_marks
from sqlalchemy.orm import Session
from models import Teacher
from auth import hash_password

load_dotenv()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(_BASE_DIR, "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TLM Connect API",
    description="Tamil Nadu School Education Department - Teaching Learning Material Platform",
    version="1.0.0",
)


# ===========================================================================
# Rate limiting — 100 requests per minute per IP (pure ASGI, no extra deps)
# ===========================================================================
class _RateLimitMiddleware:
    def __init__(self, app_inner, max_requests: int = 100, window_seconds: int = 60):
        self.app = app_inner
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._log: dict = defaultdict(list)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            ip = self._get_ip(scope)
            now = datetime.utcnow()
            cutoff = now - timedelta(seconds=self.window_seconds)
            self._log[ip] = [t for t in self._log[ip] if t > cutoff]

            if len(self._log[ip]) >= self.max_requests:
                body = b'{"detail":"Rate limit exceeded. Max 100 requests per minute."}'
                await send({
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                })
                await send({"type": "http.response.body", "body": body})
                return

            self._log[ip].append(now)

        await self.app(scope, receive, send)

    @staticmethod
    def _get_ip(scope) -> str:
        headers = dict(scope.get("headers", []))
        forwarded = headers.get(b"x-forwarded-for", b"").decode()
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = scope.get("client")
        return client[0] if client else "unknown"


app.add_middleware(_RateLimitMiddleware, max_requests=100, window_seconds=60)


# ===========================================================================
# CORS — only allow the two known frontend origins
# ===========================================================================
_allowed_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5175").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
# Security headers — added to every HTTP response (pure ASGI, no buffering)
# ===========================================================================
class _SecurityHeadersMiddleware:
    def __init__(self, app_inner):
        self.app = app_inner

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                ]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


app.add_middleware(_SecurityHeadersMiddleware)


# Static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Routers
app.include_router(auth.router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(comments.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(awards.router, prefix="/api")
app.include_router(marks_router, prefix="/api")
app.include_router(marks_admin_router, prefix="/api")
app.include_router(emis_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "TLM Connect API"}


@app.get("/api/meta/subjects")
def get_subjects():
    return [
        "Mathematics", "Science", "Social Science", "Tamil", "English",
        "Physics", "Chemistry", "Biology", "History", "Geography",
    ]


@app.get("/api/meta/stats")
def get_stats():
    from sqlalchemy import func
    db = SessionLocal()
    try:
        teacher_count = db.query(func.count(models.Teacher.id)).filter(models.Teacher.is_admin == False).scalar() or 0
        post_count = db.query(func.count(models.Post.id)).scalar() or 0
        school_count = db.query(func.count(models.School.id)).scalar() or 0
        return {
            "teachers": teacher_count,
            "posts": post_count,
            "schools": school_count,
            "districts": 38,
        }
    finally:
        db.close()


@app.get("/api/meta/districts")
def get_districts():
    return [
        "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore",
        "Dharmapuri", "Dindigul", "Erode", "Kallakurichi", "Kancheepuram",
        "Karur", "Krishnagiri", "Madurai", "Mayiladuthurai", "Nagapattinam",
        "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai", "Ramanathapuram",
        "Ranipet", "Salem", "Sivaganga", "Tenkasi", "Thanjavur", "Theni",
        "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tirupathur",
        "Tiruppur", "Tiruvallur", "Tiruvannamalai", "Tiruvarur", "Vellore",
        "Villupuram", "Virudhunagar", "Kanyakumari",
    ]


# ===========================================================================
# Seed default accounts (run once on startup)
# ===========================================================================
_db: Session = SessionLocal()

_t001 = _db.query(Teacher).filter(Teacher.emis_id == "T001").first()
if not _t001:
    _db.add(Teacher(
        emis_id="T001",
        name="Test Teacher",
        password_hash=hash_password("teacher@123"),
        district="Chennai",
        is_admin=False,
    ))
    _db.commit()
    print("Test teacher T001 created")
elif not _t001.password_hash.startswith("$2"):
    _t001.password_hash = hash_password("teacher@123")
    _db.commit()
    print("Fixed T001 password hash")

_admin_emis = os.getenv("ADMIN_EMIS_ID", "SCERT001")
_admin_pass = os.getenv("ADMIN_PASSWORD", "scert@admin123")
_scert = _db.query(Teacher).filter(Teacher.emis_id == _admin_emis).first()
if not _scert:
    _db.add(Teacher(
        emis_id=_admin_emis,
        name="SCERT Administrator",
        password_hash=hash_password(_admin_pass),
        district="Chennai",
        is_admin=True,
    ))
    _db.commit()
    print(f"Admin account created (EMIS: {_admin_emis})")

_db.close()

# Seed EMIS exam marks (200 students × 3 exams)
_emis_db: Session = SessionLocal()
try:
    seed_emis_marks(_emis_db)
finally:
    _emis_db.close()
