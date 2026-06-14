"""
backend/gmail_alerts.py
Sends Gmail alerts to the sales team for hot leads / escalations.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

SENDER        = os.getenv("GMAIL_SENDER", "")
APP_PASSWORD  = os.getenv("GMAIL_APP_PASSWORD", "")
SALES_EMAIL   = os.getenv("SALES_TEAM_EMAIL", "")


def _send(subject: str, html_body: str, to: str = None):
    recipient = to or SALES_EMAIL
    if not SENDER or not APP_PASSWORD or not recipient:
        print("[Gmail] Missing credentials – skipping email.")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SENDER
        msg["To"]      = recipient
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER, APP_PASSWORD)
            server.sendmail(SENDER, recipient, msg.as_string())
        print(f"[Gmail] Alert sent → {recipient}")
        return True
    except Exception as e:
        print(f"[Gmail] Send error: {e}")
        return False


# ──────────────────────────────────────────────────────────────
# PUBLIC HELPERS
# ──────────────────────────────────────────────────────────────

def send_hot_lead_alert(lead: dict):
    subject = f"🔥 HOT LEAD #{lead.get('id')} – {lead.get('platform','').upper()}"
    html = f"""
    <h2 style="color:#e53e3e;">🔥 New Hot Lead Detected!</h2>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;font-family:Arial">
      <tr><td><b>Lead ID</b></td><td>#{lead.get('id')}</td></tr>
      <tr><td><b>Name</b></td><td>{lead.get('name') or 'Unknown'}</td></tr>
      <tr><td><b>Platform</b></td><td>{lead.get('platform','').title()}</td></tr>
      <tr><td><b>Contact</b></td><td>{lead.get('contact_details') or 'N/A'}</td></tr>
      <tr><td><b>Interest Level</b></td><td><b style="color:#e53e3e;">HOT</b></td></tr>
      <tr><td><b>Summary</b></td><td>{lead.get('conversation_summary') or 'N/A'}</td></tr>
    </table>
    <p style="margin-top:16px;color:#555;">
      Please follow up with this lead within 30 minutes for best conversion.
    </p>
    """
    _send(subject, html)


def send_escalation_alert(lead: dict, reason: str):
    subject = f"⚡ ESCALATION Required – Lead #{lead.get('id')} – {lead.get('platform','').upper()}"
    html = f"""
    <h2 style="color:#d69e2e;">⚡ Lead Escalation Required</h2>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;font-family:Arial">
      <tr><td><b>Lead ID</b></td><td>#{lead.get('id')}</td></tr>
      <tr><td><b>Name</b></td><td>{lead.get('name') or 'Unknown'}</td></tr>
      <tr><td><b>Platform</b></td><td>{lead.get('platform','').title()}</td></tr>
      <tr><td><b>Contact</b></td><td>{lead.get('contact_details') or 'N/A'}</td></tr>
      <tr><td><b>Escalation Reason</b></td><td><b style="color:#d69e2e;">{reason}</b></td></tr>
      <tr><td><b>Interest Level</b></td><td>{lead.get('interest_level','').upper()}</td></tr>
      <tr><td><b>Summary</b></td><td>{lead.get('conversation_summary') or 'N/A'}</td></tr>
    </table>
    <p style="margin-top:16px;color:#555;">
      The AI has paused automated replies. Please take over this conversation immediately.
    </p>
    """
    _send(subject, html)


def send_daily_summary(stats: dict):
    subject = "📊 Daily Lead Generation Summary – AI LeadBot"
    by_platform = "".join(
        f"<tr><td>{p['platform'].title()}</td><td>{p['cnt']}</td></tr>"
        for p in stats.get("by_platform", [])
    )
    html = f"""
    <h2 style="color:#3182ce;">📊 Daily Lead Summary</h2>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;font-family:Arial">
      <tr><td><b>Total Leads</b></td><td>{stats.get('total',0)}</td></tr>
      <tr><td><b>🔥 Hot</b></td><td>{stats.get('hot',0)}</td></tr>
      <tr><td><b>🌡️ Warm</b></td><td>{stats.get('warm',0)}</td></tr>
      <tr><td><b>❄️ Cold</b></td><td>{stats.get('cold',0)}</td></tr>
      <tr><td><b>⚡ Escalated</b></td><td>{stats.get('escalated',0)}</td></tr>
    </table>
    <h3>By Platform</h3>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;font-family:Arial">
      <tr><th>Platform</th><th>Leads</th></tr>
      {by_platform}
    </table>
    """
    _send(subject, html)
