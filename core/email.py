import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str) -> None:
    """Send a transactional email via SMTP. Raises on failure — callers decide whether to swallow."""
    if not settings.SMTP_HOST:
        raise RuntimeError("SMTP_HOST is not configured.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.sendmail(settings.SMTP_FROM_EMAIL, to, msg.as_string())

    logger.info("Email sent to %s — subject: %s", to, subject)


def send_password_reset_email(to: str, reset_link: str) -> None:
    subject = "Reset your NestAI password"
    html_body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">
      <h2 style="color:#1a1a1a">Reset your password</h2>
      <p style="color:#555;line-height:1.6">
        We received a request to reset the password for your NestAI account.
        Click the button below to set a new password. This link expires in <strong>15 minutes</strong>.
      </p>
      <a href="{reset_link}"
         style="display:inline-block;margin:24px 0;padding:12px 28px;background:#4f46e5;
                color:#fff;border-radius:8px;text-decoration:none;font-weight:600">
        Reset password
      </a>
      <p style="color:#999;font-size:12px">
        If you didn't request this, you can safely ignore this email.<br>
        The link above will expire in 15 minutes.
      </p>
      <hr style="border:none;border-top:1px solid #eee;margin-top:32px">
      <p style="color:#bbb;font-size:11px">NestAI — Student Housing Lebanon</p>
    </div>
    """
    send_email(to, subject, html_body)
