# app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from .database import engine, Base, SessionLocal
from .models import User
from .routers import auth
from .services.auth_service import hash_password
from dotenv import load_dotenv

load_dotenv()

# Create tables automatically on startup
Base.metadata.create_all(bind=engine)

def seed_default_users():
    db = SessionLocal()
    try:
        applicant_email = "contact@shirpuragro.in"
        user = db.query(User).filter(User.email == applicant_email).first()
        if not user:
            default_user = User(
                name="Rohan Patil",
                email=applicant_email,
                password_hash=hash_password("password123"),
                is_verified=True
            )
            db.add(default_user)

        officer_email = "officer@dic.gov.in"
        officer = db.query(User).filter(User.email == officer_email).first()
        if not officer:
            default_officer = User(
                name="Dr. Anand Shinde",
                email=officer_email,
                password_hash=hash_password("password123"),
                is_verified=True
            )
            db.add(default_officer)

        db.commit()
    except Exception as e:
        print("Seeding note:", e)
    finally:
        db.close()

seed_default_users()

app = FastAPI(
    title="Udyog Sarathi — Enterprise Authentication & Single Window API",
    description="Smart India Hackathon 2026 (SIH26130) Backend with Two-Factor OTP and JWT Security.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "null"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.get("/", tags=["Health"])
def root():
    return RedirectResponse(url="/app", status_code=307)

@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "database": "sqlite connected",
        "auth_architecture": "2FA (Password + Random 6-digit OTP) -> JWT"
    }

@app.get("/app", include_in_schema=False)
def serve_frontend():
    index_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "index.html"))
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend index.html ready"}

from fastapi.responses import HTMLResponse
import sqlite3

@app.get("/db", response_class=HTMLResponse, tags=["Database Viewer"])
def view_database():
    """Live visual viewer for SQLite database tables."""
    db_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "udyog_sarathi.db"))
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    cur.execute("SELECT id, name, email, password_hash, is_verified, created_at FROM users ORDER BY id ASC")
    users = cur.fetchall()
    
    cur.execute("SELECT o.id, o.user_id, u.email, o.otp_hash, o.expires_at, o.attempts, o.verified, o.created_at FROM otp_verifications o LEFT JOIN users u ON o.user_id = u.id ORDER BY o.id DESC")
    otps = cur.fetchall()
    conn.close()

    user_rows = "".join([f"""<tr>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;font-weight:bold;'>{u[0]}</td>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;font-weight:600;'>{u[1]}</td>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;color:#2563EB;'>{u[2]}</td>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;font-family:monospace;font-size:11px;color:#64748B;'>{u[3][:28]}...</td>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;'><span style='background:{'#DCFCE7' if u[4] else '#FEF3C7'};color:{'#166534' if u[4] else '#92400E'};padding:3px 8px;border-radius:12px;font-size:11px;font-weight:bold;'>{'VERIFIED' if u[4] else 'PENDING'}</span></td>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;font-size:12px;color:#64748B;'>{u[5]}</td>
    </tr>""" for u in users])

    otp_rows = "".join([f"""<tr>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;font-weight:bold;'>{o[0]}</td>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;'>{o[1]} ({o[2]})</td>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;font-family:monospace;font-size:11px;color:#64748B;'>{o[3][:24]}...</td>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;font-size:12px;'>{o[4]}</td>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;text-align:center;'>{o[5]} / 5</td>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;'><span style='background:{'#DCFCE7' if o[6] else '#F1F5F9'};color:{'#166534' if o[6] else '#475569'};padding:3px 8px;border-radius:12px;font-size:11px;font-weight:bold;'>{'USED' if o[6] else 'ACTIVE'}</span></td>
        <td style='padding:10px;border-bottom:1px solid #E2E8F0;font-size:12px;color:#64748B;'>{o[7]}</td>
    </tr>""" for o in otps])

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Udyog Sarathi — Database Viewer</title>
    <meta charset="utf-8">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; background: #F8FAFC; color: #0F172A; margin: 0; padding: 32px; }}
        .card {{ background: #FFF; border-radius: 16px; border: 1px solid #E2E8F0; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th {{ background: #0A192F; color: #FFF; text-align: left; padding: 12px 10px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }}
        th:first-child {{ border-top-left-radius: 8px; }}
        th:last-child {{ border-top-right-radius: 8px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }}
        .btn {{ background: #E8A33D; color: #000; font-weight: 700; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1 style="font-family:'Space Grotesk',sans-serif;margin:0 0 6px;">Udyog Sarathi Database Viewer</h1>
            <p style="color:#64748B;margin:0;font-size:14px;">Live file: <code>{db_file}</code></p>
        </div>
        <div>
            <a href="/db" class="btn">↻ Refresh Data</a>
            <a href="/docs" class="btn" style="background:#0A192F;color:#FFF;margin-left:8px;">Open Swagger /docs</a>
        </div>
    </div>

    <div class="card">
        <h2 style="font-family:'Space Grotesk',sans-serif;margin:0 0 16px;font-size:18px;">1. Users Table (<code>users</code>) — {len(users)} Records</h2>
        <table>
            <thead>
                <tr><th>ID</th><th>Name</th><th>Email</th><th>Password Hash (Bcrypt)</th><th>2FA Verified</th><th>Created At (UTC)</th></tr>
            </thead>
            <tbody>{user_rows if user_rows else "<tr><td colspan='6' style='padding:20px;text-align:center;'>No users registered yet.</td></tr>"}</tbody>
        </table>
    </div>

    <div class="card">
        <h2 style="font-family:'Space Grotesk',sans-serif;margin:0 0 16px;font-size:18px;">2. Two-Factor OTP Table (<code>otp_verifications</code>) — {len(otps)} Records</h2>
        <table>
            <thead>
                <tr><th>ID</th><th>User</th><th>OTP Hash (SHA-256)</th><th>Expires At</th><th>Attempts</th><th>Status</th><th>Created At (UTC)</th></tr>
            </thead>
            <tbody>{otp_rows if otp_rows else "<tr><td colspan='7' style='padding:20px;text-align:center;'>No OTP records yet.</td></tr>"}</tbody>
        </table>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)
