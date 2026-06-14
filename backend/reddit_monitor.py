"""
backend/reddit_monitor.py
Monitor a subreddit for relevant posts and auto-reply using Gemini AI.
Run as a background thread alongside Flask.
"""

import os
import time
import threading
import praw
from dotenv import load_dotenv

load_dotenv()

SUBREDDIT_NAME = os.getenv("REDDIT_SUBREDDIT", "test")

KEYWORDS = [
    "tiles", "tile", "flooring", "interior design", "home renovation",
    "bathroom tiles", "kitchen tiles", "3d tiles", "tile visualizer",
    "tileswale", "tilesview", "floor design", "wall tiles", "ceramic tiles"
]


def _build_reddit() -> praw.Reddit:
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "LeadBot/1.0"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
    )


def _is_relevant(title: str, body: str) -> bool:
    text = (title + " " + body).lower()
    return any(kw in text for kw in KEYWORDS)


def _already_replied(submission, bot_username: str) -> bool:
    submission.comments.replace_more(limit=0)
    for comment in submission.comments.list():
        if comment.author and comment.author.name == bot_username:
            return True
    return False


def start_reddit_monitor(ai_engine_module, db_module, gmail_module):
    """
    Starts a daemon thread that continuously polls Reddit.
    Pass the imported modules to avoid circular imports.
    """

    def _run():
        print(f"[Reddit] Monitoring r/{SUBREDDIT_NAME} for keywords: {KEYWORDS[:4]}...")
        while True:
            try:
                reddit = _build_reddit()
                bot_name = reddit.user.me().name
                subreddit = reddit.subreddit(SUBREDDIT_NAME)

                for submission in subreddit.stream.submissions(skip_existing=True):
                    try:
                        title = submission.title or ""
                        body  = submission.selftext or ""

                        if not _is_relevant(title, body):
                            continue
                        if _already_replied(submission, bot_name):
                            continue

                        print(f"[Reddit] Relevant post: {title[:60]}")

                        # Qualify as a lead
                        classification = ai_engine_module.classify_lead(
                            f"{title}\n{body}", platform="reddit"
                        )
                        interest = classification.get("interest_level", "cold")

                        # Save to CRM
                        lead_id = db_module.upsert_lead(
                            sender_id=f"reddit_{submission.author.name if submission.author else 'anon'}",
                            platform="reddit",
                            name=str(submission.author) if submission.author else "Anonymous",
                            interest=interest,
                            summary=f"Reddit post: {title[:200]}"
                        )
                        db_module.save_message(lead_id, "inbound", "reddit",
                                               f"{title}\n{body}"[:1000])

                        # Generate AI reply
                        reply_text = ai_engine_module.answer_reddit_query(title, body)

                        # Post comment
                        submission.reply(reply_text)
                        print(f"[Reddit] Replied to post by {submission.author}")

                        db_module.save_message(lead_id, "outbound", "reddit", reply_text)

                        # Alert sales on hot leads
                        if interest == "hot":
                            lead = db_module.get_lead(lead_id)
                            gmail_module.send_hot_lead_alert(lead)

                        time.sleep(2)   # be polite to Reddit API

                    except Exception as inner_e:
                        print(f"[Reddit] Post error: {inner_e}")
                        time.sleep(5)

            except Exception as e:
                print(f"[Reddit] Stream error: {e} – restarting in 30s")
                time.sleep(30)

    t = threading.Thread(target=_run, daemon=True, name="reddit-monitor")
    t.start()
    return t
