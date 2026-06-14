"""
backend/meta_webhook.py
Handles Facebook/Instagram webhook verification + message processing.
"""

import os
import hashlib
import hmac
import requests
from dotenv import load_dotenv

load_dotenv()

META_VERIFY_TOKEN    = os.getenv("META_VERIFY_TOKEN", "")
META_PAGE_TOKEN      = os.getenv("META_PAGE_ACCESS_TOKEN", "")
META_APP_SECRET      = os.getenv("META_APP_SECRET", "")
GRAPH_API_BASE       = "https://graph.facebook.com/v19.0"


# ──────────────────────────────────────────────────────────────
# WEBHOOK VERIFICATION
# ──────────────────────────────────────────────────────────────

def verify_webhook(mode: str, token: str, challenge: str) -> str | None:
    """Return challenge string if valid, else None."""
    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        return challenge
    return None


def verify_signature(payload: bytes, sig_header: str) -> bool:
    """Validate X-Hub-Signature-256 from Meta."""
    if not META_APP_SECRET:
        return True   # skip in dev
    try:
        expected = "sha256=" + hmac.new(
            META_APP_SECRET.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, sig_header)
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────
# PARSE INCOMING WEBHOOK PAYLOAD
# ──────────────────────────────────────────────────────────────

def parse_meta_messages(data: dict) -> list[dict]:
    """
    Returns list of:
      { sender_id, platform, text, recipient_id }
    """
    results = []
    for entry in data.get("entry", []):
        # ── Facebook Messenger ──────────────────────────────
        for messaging in entry.get("messaging", []):
            msg = messaging.get("message", {})
            text = msg.get("text", "")
            if not text:
                continue
            results.append({
                "sender_id":    messaging["sender"]["id"],
                "recipient_id": messaging["recipient"]["id"],
                "platform":     "facebook",
                "text":         text,
            })

        # ── Instagram DMs ────────────────────────────────────
        for change in entry.get("changes", []):
            val = change.get("value", {})
            if change.get("field") != "messages":
                continue
            for msg in val.get("messages", []):
                text = (msg.get("text", {}).get("body", "")
                        or msg.get("text", ""))
                if not text:
                    continue
                results.append({
                    "sender_id":    msg.get("from", {}).get("id", "unknown"),
                    "recipient_id": val.get("id", ""),
                    "platform":     "instagram",
                    "text":         text,
                })

            # Instagram comment-to-DM: capture comments with "interested"
            for comment in val.get("comments", []):
                comment_text = comment.get("text", "").lower()
                if "interested" in comment_text or "info" in comment_text:
                    results.append({
                        "sender_id":    comment.get("from", {}).get("id", "unknown"),
                        "recipient_id": val.get("id", ""),
                        "platform":     "instagram",
                        "text":         comment.get("text", ""),
                        "is_comment":   True,
                    })
    return results


# ──────────────────────────────────────────────────────────────
# SEND REPLY VIA GRAPH API
# ──────────────────────────────────────────────────────────────

def send_facebook_message(recipient_id: str, text: str) -> bool:
    url = f"{GRAPH_API_BASE}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message":   {"text": text[:2000]},
    }
    try:
        r = requests.post(url, json=payload,
                          params={"access_token": META_PAGE_TOKEN}, timeout=10)
        if r.status_code == 200:
            print(f"[Meta] FB reply sent to {recipient_id}")
            return True
        print(f"[Meta] FB send error {r.status_code}: {r.text}")
        return False
    except Exception as e:
        print(f"[Meta] Request error: {e}")
        return False


def send_instagram_dm(recipient_id: str, text: str) -> bool:
    url = f"{GRAPH_API_BASE}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message":   {"text": text[:1000]},
    }
    try:
        r = requests.post(url, json=payload,
                          params={"access_token": META_PAGE_TOKEN}, timeout=10)
        if r.status_code == 200:
            print(f"[Meta] IG DM sent to {recipient_id}")
            return True
        print(f"[Meta] IG DM error {r.status_code}: {r.text}")
        return False
    except Exception as e:
        print(f"[Meta] Request error: {e}")
        return False


def send_reply(sender_id: str, text: str, platform: str) -> bool:
    if platform == "instagram":
        return send_instagram_dm(sender_id, text)
    return send_facebook_message(sender_id, text)
