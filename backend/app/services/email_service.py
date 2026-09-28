# app/services/email_service.py
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("udyog_sarathi.email")

def get_smtp_config():
    """Read latest SMTP configuration from environment variables."""
    load_dotenv(override=True)
    host = os.getenv("SMTP_HOST", "").strip()
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        port = 587
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip().replace(" ", "")
    from_email = os.getenv("SMTP_FROM_EMAIL", "").strip() or username
    return host, port, username, password, from_email

def is_smtp_configured() -> bool:
    """Check if valid non-placeholder SMTP credentials are configured."""
    host, _, username, password, _ = get_smtp_config()
    if not host or not username or not password:
        return False
    if "your_email" in username or "example.com" in username:
        return False
    return True

def send_otp_email(recipient_email: str, otp: str) -> bool:
    """
    Send the exact 6-digit verification OTP to the user's registered email address.
    Uses SMTP with TLS (or SSL).
    Handles failures gracefully so login flow does not crash.
    """
    if not recipient_email or not otp:
        print(f"[EMAIL WARNING] Cannot send OTP email: missing recipient or OTP.")
        return False

    host, port, username, password, from_email = get_smtp_config()

    if not is_smtp_configured():
        print(f"[EMAIL NOTICE] SMTP not configured in .env. OTP email skipped for {recipient_email}. (Console OTP fallback active).")
        return False

    subject = "Your Verification OTP — Udyog Sarathi"
    
    # Plain text version
    text_content = f"""Hello,

Your verification OTP is:

{otp}

This OTP is valid for 5 minutes.

If you did not request this verification, please ignore this email.

Regards,
Udyog Sarathi Team
Smart Industrial Approvals & Compliance
"""

    # HTML formatted version
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: Arial, sans-serif; background-color: #f7f8f4; margin: 0; padding: 24px; color: #101820;">
    <div style="max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #dbdfd3; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.06);">
        <div style="background: #0A192F; padding: 22px 28px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0.05em;">UDYOG SARATHI</h1>
            <p style="color: #E8A33D; margin: 4px 0 0; font-size: 11px; font-weight: 600; text-transform: uppercase;">Industrial Approvals & Compliance Intelligence</p>
        </div>
        <div style="padding: 28px;">
            <p style="font-size: 15px; margin: 0 0 16px; color: #101820;">Hello,</p>
            <p style="font-size: 14px; margin: 0 0 20px; color: #4E5964; line-height: 1.5;">
                You are logging in to your <strong>Udyog Sarathi</strong> enterprise account. Please use the following One-Time Password (OTP) to complete your secure two-step authentication:
            </p>
            <div style="background: #FBF0DC; border: 2px dashed #E8A33D; border-radius: 12px; padding: 18px; text-align: center; margin-bottom: 22px;">
                <span style="font-family: monospace; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #0A192F;">{otp}</span>
            </div>
            <p style="font-size: 13px; color: #4E5964; margin: 0 0 10px;">
                ⏱️ This OTP is valid for <strong>5 minutes</strong> and can only be used once.
            </p>
            <p style="font-size: 12px; color: #8FA3B8; margin: 0 0 24px;">
                If you did not initiate this login request, please ignore this email or change your password immediately.
            </p>
            <hr style="border: none; border-top: 1px solid #EEF0E9; margin: 20px 0;">
            <p style="font-size: 12px; color: #4E5964; margin: 0;">
                Regards,<br>
                <strong>Udyog Sarathi Team</strong><br>
                <span style="color: #8FA3B8; font-size: 11px;">National Single Window Clearance & Regulatory Intelligence</span>
            </p>
        </div>
    </div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Udyog Sarathi <{from_email}>"
    msg["To"] = recipient_email

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(username, password)
        server.sendmail(from_email, [recipient_email], msg.as_string())
        server.quit()

        print(f"[EMAIL SUCCESS] OTP email successfully delivered to {recipient_email}")
        return True
    except Exception as e:
        # Never log SMTP password or sensitive data
        print(f"[EMAIL ERROR] OTP email delivery failed for {recipient_email}: {type(e).__name__}: {str(e)}")
        return False
