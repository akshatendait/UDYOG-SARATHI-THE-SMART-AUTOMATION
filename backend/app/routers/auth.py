# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    OTPVerifyRequest,
    ApiResponse,
    UserResponse,
    TokenResponse,
    LoginSuccessResponse
)
from ..services.auth_service import hash_password, verify_password, create_access_token
from ..services.otp_service import create_user_otp, verify_user_otp
from ..services.email_service import send_otp_email, is_smtp_configured
from ..dependencies.auth import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user entity:
    1. Validates input schema.
    2. Checks for duplicate email.
    3. Hashes password using bcrypt.
    4. Persists user in database.
    """
    clean_email = request.email.strip().lower()

    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "An account with this email address already exists."}
        )

    # Hash password securely
    hashed = hash_password(request.password)

    new_user = User(
        name=request.name.strip(),
        email=clean_email,
        password_hash=hashed,
        is_verified=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return ApiResponse(
        success=True,
        message="Registration successful. Please log in with your credentials.",
        data={"user_id": new_user.id, "email": new_user.email}
    )

@router.post("/login", response_model=LoginSuccessResponse)
def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """
    First Authentication Factor:
    Verifies email and password.
    If valid, generates a random 6-digit OTP and initiates 2FA flow.
    Does NOT issue JWT yet.
    """
    clean_email = request.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Incorrect email or password. Please verify and try again."}
        )

    # Credentials verified -> Generate 2nd factor OTP
    otp = create_user_otp(db, user)

    # Automatically dispatch the EXACT SAME OTP to user's registered email
    email_sent = send_otp_email(user.email, otp)

    if email_sent:
        msg = f"Credentials verified. A 6-digit verification OTP has been sent to {user.email}."
        demo_code = None
    else:
        msg = f"Credentials verified. Demo OTP is {otp}. (Configure SMTP in .env for live email delivery)."
        demo_code = otp

    return LoginSuccessResponse(
        success=True,
        message=msg,
        email=user.email,
        requires_otp=True,
        demo_otp=demo_code
    )

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(request: OTPVerifyRequest, db: Session = Depends(get_db)):
    """
    Second Authentication Factor:
    Validates 6-digit OTP, checks expiration (5 min) and attempts (< 5).
    If valid, issues JWT access token.
    """
    clean_email = request.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"success": False, "message": "User not found."}
        )

    is_valid, msg = verify_user_otp(db, user, request.otp)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": msg}
        )

    # Success! Generate JWT access token
    token = create_access_token(data={"sub": user.email, "user_id": user.id, "name": user.name})

    return TokenResponse(
        success=True,
        message="Authentication successful. Two-factor verification completed.",
        access_token=token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )

@router.get("/me", response_model=ApiResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Protected API endpoint requiring valid Bearer JWT.
    Returns authenticated user information.
    Never exposes passwords, hashes, or secrets.
    """
    return ApiResponse(
        success=True,
        message="Authenticated user profile retrieved successfully.",
        data={
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at.isoformat()
        }
    )

@router.post("/logout", response_model=ApiResponse)
def logout(response: Response):
    """
    Logout endpoint: notifies the client to purge token/session.
    """
    return ApiResponse(
        success=True,
        message="Logged out successfully."
    )
