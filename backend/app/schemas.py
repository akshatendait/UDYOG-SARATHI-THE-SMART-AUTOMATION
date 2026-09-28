# app/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
import datetime

# --- Generic Response ---
class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

# --- User Registration ---
class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full name or enterprise lead")
    email: EmailStr = Field(..., description="Valid work/personal email address")
    password: str = Field(..., min_length=6, max_length=128, description="Secure password (minimum 6 chars)")

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_verified: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# --- Login Request ---
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginSuccessResponse(BaseModel):
    success: bool
    message: str
    email: str
    requires_otp: bool = True
    demo_otp: Optional[str] = None

# --- OTP Verification ---
class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit One-Time Password")

class TokenResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
