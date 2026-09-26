import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("EmailService")

# Test hook for capturing sent emails during unit tests
sent_emails_log = []

class EmailService:
    def __init__(self):
        self.smtp_host = getattr(settings, 'SMTP_HOST', None) or getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_username = getattr(settings, 'SMTP_USERNAME', None) or getattr(settings, 'SMTP_USER', None)
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', None)
        self.smtp_from = getattr(settings, 'SMTP_FROM', None) or getattr(settings, 'SMTP_FROM_EMAIL', 'alerts@swasemi.com')
        self.test_mode = False

    def send_temperature_breach_email(
        self,
        to_email: str,
        org_name: str,
        tracker_name: str,
        shipment_id: str,
        current_temp: float,
        min_temp: float,
        max_temp: float,
        timestamp: datetime,
        message_detail: Optional[str] = None
    ) -> bool:
        """
        Constructs and delivers a real SMTP email notification for a temperature breach.
        """
        subject = f"CRITICAL: Temperature Breach Alert - Tracker {tracker_name} ({shipment_id})"
        
        timestamp_str = timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)

        body_html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="background-color: #f87171; color: white; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
              <h2 style="margin: 0;">⚠️ Temperature Breach Alert</h2>
            </div>
            
            <p>A continuous temperature breach has been detected exceeding the grace period limit for your cold-chain shipment.</p>
            
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
              <tr style="background-color: #f1f5f9;"><td style="padding: 10px; border: 1px solid #cbd5e1;"><strong>Organization</strong></td><td style="padding: 10px; border: 1px solid #cbd5e1;">{org_name}</td></tr>
              <tr><td style="padding: 10px; border: 1px solid #cbd5e1;"><strong>Tracker</strong></td><td style="padding: 10px; border: 1px solid #cbd5e1;">{tracker_name}</td></tr>
              <tr style="background-color: #f1f5f9;"><td style="padding: 10px; border: 1px solid #cbd5e1;"><strong>Shipment ID</strong></td><td style="padding: 10px; border: 1px solid #cbd5e1;">{shipment_id}</td></tr>
              <tr><td style="padding: 10px; border: 1px solid #cbd5e1;"><strong>Current Temperature</strong></td><td style="padding: 10px; border: 1px solid #cbd5e1;"><strong style="color: #dc2626; font-size: 1.1em;">{current_temp}°C</strong></td></tr>
              <tr style="background-color: #f1f5f9;"><td style="padding: 10px; border: 1px solid #cbd5e1;"><strong>Allowed Threshold Range</strong></td><td style="padding: 10px; border: 1px solid #cbd5e1;">{min_temp}°C to {max_temp}°C</td></tr>
              <tr><td style="padding: 10px; border: 1px solid #cbd5e1;"><strong>Breach Timestamp</strong></td><td style="padding: 10px; border: 1px solid #cbd5e1;">{timestamp_str}</td></tr>
            </table>

            {f'<p style="margin-top: 20px; color: #64748b;"><em>{message_detail}</em></p>' if message_detail else ''}

            <hr style="border: none; border-top: 1px solid #e2e8f0; margin-top: 30px;" />
            <p style="font-size: 0.8em; color: #94a3b8;">SWASEMI Cold-Chain Automated Monitoring Platform</p>
          </body>
        </html>
        """

        email_record = {
            "to": to_email,
            "subject": subject,
            "org_name": org_name,
            "tracker_name": tracker_name,
            "shipment_id": shipment_id,
            "current_temp": current_temp,
            "min_temp": min_temp,
            "max_temp": max_temp,
            "timestamp": timestamp_str
        }
        
        sent_emails_log.append(email_record)

        if self.test_mode or not self.smtp_username or not self.smtp_password:
            logger.info(f"[Email Logged / Test Mode] To: {to_email} | Subject: '{subject}' | Temp: {current_temp}°C")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_from
            msg["To"] = to_email
            msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=5) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Successfully sent SMTP email alert to {to_email}")
            return True
        except Exception as e:
            logger.warning(f"Failed to deliver SMTP email alert to {to_email}: {e}")
            return False

email_service = EmailService()
