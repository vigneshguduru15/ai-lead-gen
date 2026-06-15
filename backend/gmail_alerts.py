import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()

SENDER       = os.getenv("GMAIL_SENDER", "")
SALES_EMAIL  = os.getenv("SALES_TEAM_EMAIL", "")
SENDGRID_KEY = os.getenv("SENDGRID_API_KEY", "")


def _send(subject: str, html_body: str, to: str = None):
    recipient = to or SALES_EMAIL
    if not SENDGRID_KEY or not recipient:
        print("[Email] Missing credentials – skipping.")
        return False
    try:
        data = json.dumps({
            "personalizations": [{"to": [{"email": recipient}]}],
            "from": {"email": SENDER or "vigneshguduru15@gmail.com"},
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}]
        }).encode()

        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=data,
            headers={
                "Authorization": f"Bearer {SENDGRID_KEY}",
                "Content-Type": "application/json"
            }
        )
        urllib.request.urlopen(req, timeout=10)
        print(f"[Email] Alert sent → {recipient}")
        return True
    except Exception as e:
        print(f"[Email] Send error: {e}")
        return False


def send_hot_lead_alert(lead: dict):
    subject = f"🔥 HOT LEAD #{lead.get('id')} – {lead.get('platform','').upper()}"
    html = f"""
    <h2 style="color:#e53e3e;">🔥 New Hot Lead!</h2>
    <table border="1" cellpadding="8" cellspacing="0">
      <tr><td><b>Lead ID</b></td><td>#{lead.get('id')}</td></tr>
      <tr><td><b>Name</b></td><td>{lead.get('name') or 'Unknown'}</td></tr>
      <tr><td><b>Platform</b></td><td>{lead.get('platform','').title()}</td></tr>
      <tr><td><b>Contact</b></td><td>{lead.get('contact_details') or 'N/A'}</td></tr>
      <tr><td><b>Interest</b></td><td><b style="color:#e53e3e;">HOT</b></td></tr>
      <tr><td><b>Summary</b></td><td>{lead.get('conversation_summary') or 'N/A'}</td></tr>
    </table>
    """
    _send(subject, html)


def send_escalation_alert(lead: dict, reason: str):
    subject = f"⚡ ESCALATION – Lead #{lead.get('id')} – {lead.get('platform','').upper()}"
    html = f"""
    <h2 style="color:#d69e2e;">⚡ Lead Escalation Required</h2>
    <table border="1" cellpadding="8" cellspacing="0">
      <tr><td><b>Lead ID</b></td><td>#{lead.get('id')}</td></tr>
      <tr><td><b>Name</b></td><td>{lead.get('name') or 'Unknown'}</td></tr>
      <tr><td><b>Platform</b></td><td>{lead.get('platform','').title()}</td></tr>
      <tr><td><b>Contact</b></td><td>{lead.get('contact_details') or 'N/A'}</td></tr>
      <tr><td><b>Reason</b></td><td><b style="color:#d69e2e;">{reason}</b></td></tr>
      <tr><td><b>Interest</b></td><td>{lead.get('interest_level','').upper()}</td></tr>
    </table>
    <p>The AI has paused automated replies. Please take over immediately.</p>
    """
    _send(subject, html)


def send_daily_summary(stats: dict):
    subject = "📊 Daily Lead Summary"
    html = f"""
    <h2>📊 Daily Lead Summary</h2>
    <table border="1" cellpadding="8" cellspacing="0">
      <tr><td><b>Total</b></td><td>{stats.get('total',0)}</td></tr>
      <tr><td><b>🔥 Hot</b></td><td>{stats.get('hot',0)}</td></tr>
      <tr><td><b>🌡️ Warm</b></td><td>{stats.get('warm',0)}</td></tr>
      <tr><td><b>❄️ Cold</b></td><td>{stats.get('cold',0)}</td></tr>
      <tr><td><b>⚡ Escalated</b></td><td>{stats.get('escalated',0)}</td></tr>
    </table>
    """
    _send(subject, html)