"""
backend/app.py
Main Flask application – Meta webhook, REST API endpoints.
"""

import os
import json
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from dotenv import load_dotenv

# Local modules
import database as db
import ai_engine as ai
import gmail_alerts as gmail
import meta_webhook as meta
import reddit_monitor as reddit

load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")


# ══════════════════════════════════════════════════════════════
#  CORE LEAD PROCESSING PIPELINE
# ══════════════════════════════════════════════════════════════

def process_incoming_message(sender_id: str, platform: str, text: str):
    """
    Full pipeline:
      1. Classify lead with Gemini
      2. Upsert into MySQL CRM
      3. Check escalation
      4. Generate & send reply
      5. Send Gmail alerts if needed
      6. Update conversation summary
    """
    # ── 1. Classify ──────────────────────────────────────────
    classification = ai.classify_lead(text, platform)
    interest   = classification.get("interest_level", "cold")
    name       = classification.get("name")
    contact    = classification.get("contact")

    # ── 2. Upsert CRM ────────────────────────────────────────
    lead_id = db.upsert_lead(
        sender_id=sender_id,
        platform=platform,
        name=name,
        contact=contact,
        interest=interest,
    )
    db.save_message(lead_id, "inbound", platform, text)

    # ── 3. Escalation check ──────────────────────────────────
    esc_keyword, esc_reason = ai.needs_escalation(text)
    escalate = esc_keyword or interest == "hot"

    # ── 4. Generate reply ────────────────────────────────────
    history = db.get_messages(lead_id)

    if escalate and not db.get_lead(lead_id).get("escalated"):
        reply = (
            "Thank you for your interest! 🎉 One of our sales specialists will "
            "reach out to you personally within the next few hours. "
            "We look forward to helping you!"
        )
        db.mark_escalated(lead_id, esc_reason or "Hot lead auto-escalation")
        lead = db.get_lead(lead_id)
        gmail.send_escalation_alert(lead, esc_reason or "Hot lead")
    else:
        reply = ai.generate_reply(text, interest, platform, history)

    # ── 5. Send reply via platform ───────────────────────────
    meta.send_reply(sender_id, reply, platform)
    db.save_message(lead_id, "outbound", platform, reply)

    # ── 6. Update summary ────────────────────────────────────
    all_msgs = db.get_messages(lead_id)
    summary  = ai.summarise_conversation(all_msgs)
    db.upsert_lead(sender_id, platform, name, contact, interest, summary)

    # ── 7. Hot lead Gmail alert (first time only) ─────────────
    if interest == "hot" and not escalate:
        lead = db.get_lead(lead_id)
        gmail.send_hot_lead_alert(lead)

    return {
        "lead_id":       lead_id,
        "interest_level": interest,
        "reply":         reply,
        "escalated":     escalate,
    }


# ══════════════════════════════════════════════════════════════
#  META WEBHOOK ENDPOINTS
# ══════════════════════════════════════════════════════════════

@app.route("/webhook", methods=["GET"])
def webhook_verify():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    result    = meta.verify_webhook(mode, token, challenge)
    if result:
        return result, 200
    abort(403)


@app.route("/webhook", methods=["POST"])
def webhook_receive():
    # Verify signature
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not meta.verify_signature(request.data, sig):
        abort(403, "Invalid signature")

    data = request.json or {}
    messages = meta.parse_meta_messages(data)

    results = []
    for msg in messages:
        try:
            result = process_incoming_message(
                sender_id=msg["sender_id"],
                platform=msg["platform"],
                text=msg["text"],
            )
            results.append(result)
        except Exception as e:
            print(f"[Webhook] Error processing message: {e}")

    return jsonify({"status": "ok", "processed": len(results)}), 200


# ══════════════════════════════════════════════════════════════
#  REST API – used by Gradio frontend
# ══════════════════════════════════════════════════════════════

@app.route("/api/leads", methods=["GET"])
def api_leads():
    leads = db.get_all_leads()
    # Convert datetime objects to string
    for lead in leads:
        for k, v in lead.items():
            if hasattr(v, "isoformat"):
                lead[k] = v.isoformat()
    return jsonify(leads)


@app.route("/api/leads/<int:lead_id>", methods=["GET"])
def api_lead_detail(lead_id):
    lead = db.get_lead(lead_id)
    if not lead:
        abort(404)
    for k, v in lead.items():
        if hasattr(v, "isoformat"):
            lead[k] = v.isoformat()
    msgs = db.get_messages(lead_id)
    for m in msgs:
        for k, v in m.items():
            if hasattr(v, "isoformat"):
                m[k] = v.isoformat()
    return jsonify({"lead": lead, "messages": msgs})


@app.route("/api/stats", methods=["GET"])
def api_stats():
    stats = db.get_stats()
    return jsonify(stats)


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """Simulate an incoming message (for testing without real Meta app)."""
    body = request.json or {}
    sender_id = body.get("sender_id", "test_user_001")
    platform  = body.get("platform", "facebook")
    text      = body.get("text", "")
    if not text:
        return jsonify({"error": "text required"}), 400

    result = process_incoming_message(sender_id, platform, text)
    return jsonify(result), 200


@app.route("/api/daily-summary", methods=["POST"])
def api_daily_summary():
    stats = db.get_stats()
    gmail.send_daily_summary(stats)
    return jsonify({"status": "sent"})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "AI Lead Gen"})


# ══════════════════════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Start Reddit monitor in background thread
    try:
        reddit.start_reddit_monitor(ai, db, gmail)
    except Exception as e:
        print(f"[Reddit] Could not start monitor: {e}")

    port = int(os.getenv("PORT", 5000))
    print(f"[Flask] Starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
