"""
backend/database.py
MySQL CRM helper – handles leads, messages, and escalations.
"""

import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

_pool = pooling.MySQLConnectionPool(
    pool_name="leadpool",
    pool_size=5,
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", 3306)),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    database=os.getenv("MYSQL_DATABASE", "ai_lead_crm"),
    autocommit=True,
    charset="utf8mb4",
)


def _conn():
    return _pool.get_connection()


# ──────────────────────────────────────────────────────────────
# LEAD CRUD
# ──────────────────────────────────────────────────────────────

def upsert_lead(sender_id: str, platform: str, name: str = None,
                contact: str = None, interest: str = "cold",
                summary: str = None) -> int:
    """Insert or update a lead; returns lead_id."""
    cn = _conn()
    cur = cn.cursor()
    cur.execute("SELECT id FROM leads WHERE sender_id=%s AND platform=%s",
                (sender_id, platform))
    row = cur.fetchone()

    if row:
        lead_id = row[0]
        cur.execute(
            """UPDATE leads SET name=COALESCE(%s,name),
               contact_details=COALESCE(%s,contact_details),
               interest_level=%s,
               conversation_summary=COALESCE(%s,conversation_summary),
               updated_at=NOW()
               WHERE id=%s""",
            (name, contact, interest, summary, lead_id)
        )
    else:
        cur.execute(
            """INSERT INTO leads
               (sender_id, platform, name, contact_details, interest_level, conversation_summary)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (sender_id, platform, name, contact, interest, summary)
        )
        lead_id = cur.lastrowid

    cur.close()
    cn.close()
    return lead_id


def get_lead(lead_id: int) -> dict | None:
    cn = _conn()
    cur = cn.cursor(dictionary=True)
    cur.execute("SELECT * FROM leads WHERE id=%s", (lead_id,))
    row = cur.fetchone()
    cur.close()
    cn.close()
    return row


def get_all_leads(limit: int = 200) -> list[dict]:
    cn = _conn()
    cur = cn.cursor(dictionary=True)
    cur.execute("SELECT * FROM leads ORDER BY updated_at DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    cur.close()
    cn.close()
    return rows


def get_lead_by_sender(sender_id: str, platform: str) -> dict | None:
    cn = _conn()
    cur = cn.cursor(dictionary=True)
    cur.execute("SELECT * FROM leads WHERE sender_id=%s AND platform=%s",
                (sender_id, platform))
    row = cur.fetchone()
    cur.close()
    cn.close()
    return row


# ──────────────────────────────────────────────────────────────
# MESSAGE CRUD
# ──────────────────────────────────────────────────────────────

def save_message(lead_id: int, direction: str, platform: str, content: str):
    cn = _conn()
    cur = cn.cursor()
    cur.execute(
        "INSERT INTO messages (lead_id, direction, platform, content) VALUES (%s,%s,%s,%s)",
        (lead_id, direction, platform, content)
    )
    cur.close()
    cn.close()


def get_messages(lead_id: int) -> list[dict]:
    cn = _conn()
    cur = cn.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM messages WHERE lead_id=%s ORDER BY created_at ASC",
        (lead_id,)
    )
    rows = cur.fetchall()
    cur.close()
    cn.close()
    return rows


# ──────────────────────────────────────────────────────────────
# ESCALATION
# ──────────────────────────────────────────────────────────────

def mark_escalated(lead_id: int, reason: str):
    cn = _conn()
    cur = cn.cursor()
    cur.execute(
        "UPDATE leads SET escalated=1, escalation_reason=%s WHERE id=%s",
        (reason, lead_id)
    )
    cur.execute(
        "INSERT INTO escalations (lead_id, reason) VALUES (%s,%s)",
        (lead_id, reason)
    )
    cur.close()
    cn.close()


# ──────────────────────────────────────────────────────────────
# STATS
# ──────────────────────────────────────────────────────────────

def get_stats() -> dict:
    cn = _conn()
    cur = cn.cursor(dictionary=True)
    cur.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(interest_level='hot')  AS hot,
            SUM(interest_level='warm') AS warm,
            SUM(interest_level='cold') AS cold,
            SUM(escalated=1)           AS escalated
        FROM leads
    """)
    stats = cur.fetchone()
    cur.close()

    cur = cn.cursor(dictionary=True)
    cur.execute("""
        SELECT platform, COUNT(*) AS cnt
        FROM leads GROUP BY platform
    """)
    by_platform = cur.fetchall()
    cur.close()
    cn.close()

    stats["by_platform"] = by_platform
    return stats
