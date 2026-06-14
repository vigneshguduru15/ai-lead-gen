"""
backend/ai_engine.py
Gemini AI – lead qualification, reply generation, summary.
"""

import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
_model = genai.GenerativeModel("gemini-1.5-flash")

# ──────────────────────────────────────────────────────────────
# ESCALATION TRIGGERS (rule-based pre-filter, fast)
# ──────────────────────────────────────────────────────────────
ESCALATION_KEYWORDS = [
    "pricing", "price", "cost", "demo", "free trial",
    "sales call", "speak to someone", "talk to a human",
    "human", "agent", "representative", "discount", "quote",
    "how much", "what does it cost", "buy", "purchase", "subscribe"
]


def needs_escalation(message: str) -> tuple[bool, str]:
    msg_lower = message.lower()
    for kw in ESCALATION_KEYWORDS:
        if kw in msg_lower:
            return True, f"Keyword match: '{kw}'"
    return False, ""


# ──────────────────────────────────────────────────────────────
# LEAD QUALIFICATION
# ──────────────────────────────────────────────────────────────

def classify_lead(message: str, platform: str = "unknown") -> dict:
    """
    Returns:
        {
          "interest_level": "hot|warm|cold",
          "reason": "...",
          "confidence": 0-100,
          "name": "...",       # if detectable
          "contact": "..."     # if detectable
        }
    """
    prompt = f"""You are a lead qualification AI for a SaaS company (Tilesview/Tileswale).
Analyze the following message from {platform} and classify the lead.

Message: "{message}"

Respond ONLY with valid JSON (no markdown, no extra text):
{{
  "interest_level": "hot|warm|cold",
  "reason": "<one sentence>",
  "confidence": <0-100>,
  "name": "<extracted name or null>",
  "contact": "<extracted email/phone or null>"
}}

Classification rules:
- hot  = ready to buy, asks for pricing/demo/trial, urgent need
- warm = shows interest, asks product questions, comparing options
- cold = general curiosity, off-topic, just browsing
"""
    try:
        response = _model.generate_content(prompt)
        text = response.text.strip()
        # strip markdown code fences if present
        text = re.sub(r"```json|```", "", text).strip()
        data = json.loads(text)
        return data
    except Exception as e:
        return {
            "interest_level": "cold",
            "reason": f"AI error: {e}",
            "confidence": 0,
            "name": None,
            "contact": None
        }


# ──────────────────────────────────────────────────────────────
# AUTO-REPLY GENERATION
# ──────────────────────────────────────────────────────────────

def generate_reply(message: str, interest_level: str,
                   platform: str = "unknown",
                   conversation_history: list[dict] = None) -> str:
    """Generate a contextual, brand-appropriate auto-reply."""

    history_text = ""
    if conversation_history:
        history_text = "\n".join(
            f"{m['direction'].upper()}: {m['content']}"
            for m in conversation_history[-6:]   # last 6 turns
        )

    escalation_note = ""
    if interest_level == "hot":
        escalation_note = (
            "Since this is a HOT lead, warmly inform them that a sales representative "
            "will reach out shortly. Provide enthusiasm and urgency."
        )

    prompt = f"""You are an AI sales assistant for Tilesview – a leading SaaS platform 
for 3D tile visualisation and interior design. Be friendly, professional, concise.

Platform: {platform}
Lead temperature: {interest_level}
{escalation_note}

Recent conversation:
{history_text if history_text else "(no prior history)"}

Customer's latest message: "{message}"

Write a helpful, natural reply (2-4 sentences max). 
Do NOT use markdown formatting. Do NOT mention you are an AI unless directly asked.
Do NOT make up pricing figures. If pricing is asked, say a specialist will follow up.
"""
    try:
        response = _model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return ("Thanks for reaching out! Our team will get back to you shortly. "
                f"(AI error: {e})")


# ──────────────────────────────────────────────────────────────
# CONVERSATION SUMMARY
# ──────────────────────────────────────────────────────────────

def summarise_conversation(messages: list[dict]) -> str:
    """Produce a CRM-ready summary of a conversation."""
    if not messages:
        return "No conversation yet."

    history = "\n".join(
        f"{m['direction'].upper()} [{m['platform']}]: {m['content']}"
        for m in messages
    )

    prompt = f"""Summarise this customer conversation for a CRM record in 3-5 sentences.
Include: customer intent, key questions asked, product interest, and recommended next action.

Conversation:
{history}

Respond with plain text only."""
    try:
        response = _model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Summary unavailable: {e}"


# ──────────────────────────────────────────────────────────────
# REDDIT QUERY ANSWER
# ──────────────────────────────────────────────────────────────

def answer_reddit_query(post_title: str, post_body: str) -> str:
    """Generate a helpful Reddit comment reply."""
    prompt = f"""You are a helpful community member who also works at Tilesview SaaS.
Someone posted on Reddit asking about tiles, interior design, or similar topics.
Give a genuinely helpful answer (3-5 sentences). Only mention Tilesview naturally 
if it's clearly relevant. Do NOT be spammy.

Post title: "{post_title}"
Post body: "{post_body}"

Reply:"""
    try:
        response = _model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"AI error generating reply: {e}"
