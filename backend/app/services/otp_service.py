# app/services/otp_service.py
import os
import secrets
import hashlib
import datetime
from sqlalchemy.orm import Session
from ..models import OTPVerification, User
from dotenv import load_dotenv

load_dotenv()

OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", "5"))
MAX_OTP_ATTEMPTS = int(os.getenv("MAX_OTP_ATTEMPTS", "5"))

def hash_otp(otp: str) -> str:
    """Hash 6-digit OTP using SHA-256."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()

def generate_otp() -> str:
    """Generate cryptographically secure 6-digit OTP (100000 to 999999)."""
    return f"{secrets.randbelow(900000) + 100000}"

def create_user_otp(db: Session, user: User) -> str:
    """
    Generate random 6-digit OTP, store hashed in DB with expiration,
    and log clearly in development/demonstration console.
    """
    # Invalidate previous unverified OTPs for this user
    db.query(OTPVerification).filter(
        OTPVerification.user_id == user.id,
        OTPVerification.verified == False
    ).update({"verified": True})
    db.commit()

    otp = generate_otp()
    otp_hash = hash_otp(otp)
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=OTP_EXPIRE_MINUTES)

    db_otp = OTPVerification(
        user_id=user.id,
        otp_hash=otp_hash,
        expires_at=expires_at,
        attempts=0,
        verified=False
    )
    db.add(db_otp)
    db.commit()
    db.refresh(db_otp)

    # REQUIRED Development / Demo console output:
    print(f"\n========================================================")
    print(f"[DEMO OTP] User: {user.email} | OTP: {otp}")
    print(f"Expires in {OTP_EXPIRE_MINUTES} minutes (at {expires_at.strftime('%H:%M:%S UTC')})")
    print(f"========================================================\n")

    return otp

def verify_user_otp(db: Session, user: User, entered_otp: str) -> tuple[bool, str]:
    """
    Verify entered OTP against pending OTP verification record.
    Returns (success: bool, error_message_or_ok: str).
    """
    pending_otp = db.query(OTPVerification).filter(
        OTPVerification.user_id == user.id,
        OTPVerification.verified == False
    ).order_by(OTPVerification.created_at.desc()).first()

    if not pending_otp:
        return False, "No active OTP request found. Please request a new OTP."

    # Check maximum attempts
    if pending_otp.attempts >= MAX_OTP_ATTEMPTS:
        pending_otp.verified = True
        db.commit()
        return False, f"Maximum verification attempts ({MAX_OTP_ATTEMPTS}) exceeded. Please request a new OTP."

    # Check expiration
    now = datetime.datetime.utcnow()
    if now > pending_otp.expires_at:
        pending_otp.verified = True
        db.commit()
        return False, "OTP has expired. Please log in again to receive a fresh OTP."

    # Increment attempts
    pending_otp.attempts += 1

    # Verify hash
    entered_hash = hash_otp(entered_otp.strip())
    if entered_hash != pending_otp.otp_hash:
        remaining = MAX_OTP_ATTEMPTS - pending_otp.attempts
        db.commit()
        if remaining <= 0:
            pending_otp.verified = True
            db.commit()
            return False, f"Invalid OTP. Maximum attempts reached. Please request a new OTP."
        return False, f"Invalid OTP. {remaining} attempt(s) remaining."

    # Correct OTP! Mark verified and invalidate
    pending_otp.verified = True
    user.is_verified = True
    db.commit()
    return True, "OTP verified successfully"
