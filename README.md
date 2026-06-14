# 🤖 AI Lead Generation & Social Media Auto-Reply System

Powered by **Gemini AI** | **MySQL CRM** | **Meta Webhook** | **Reddit Monitor** | **Gmail Alerts** | **Gradio Dashboard**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    INBOUND CHANNELS                      │
│  Facebook Messenger │ Instagram DM │ Reddit │ Website   │
└──────────────┬──────────────────────────────────────────┘
               │ webhooks / praw stream
               ▼
┌─────────────────────────────────────────────────────────┐
│              FLASK BACKEND  (app.py)                     │
│  /webhook  ──► parse_meta_messages()                     │
│  /api/*    ──► REST endpoints for Gradio                 │
└──────────────┬──────────────────────────────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌────────────┐   ┌─────────────────────────────────────┐
│ ai_engine  │   │          database.py                 │
│ (Gemini)   │   │  MySQL CRM – leads / messages /      │
│ • classify │   │  escalations tables                  │
│ • reply    │   └──────────────────┬──────────────────┘
│ • summary  │                      │
└────────────┘                      │
       │                            │
       ▼                            ▼
┌────────────────┐         ┌───────────────────┐
│ gmail_alerts   │         │  Gradio Dashboard  │
│ hot lead email │         │  (frontend/)       │
│ escalation     │         │  CRM view, stats,  │
│ daily summary  │         │  simulator, manual │
└────────────────┘         └───────────────────┘
```

---

## 📁 Project Structure

```
ai_lead_gen/
├── backend/
│   ├── app.py              # Flask app + pipeline
│   ├── ai_engine.py        # Gemini AI – classify / reply / summarise
│   ├── database.py         # MySQL CRM helpers
│   ├── gmail_alerts.py     # Gmail SMTP alerts
│   ├── meta_webhook.py     # Meta webhook parse + Graph API send
│   └── reddit_monitor.py   # Reddit praw stream + auto-reply
├── frontend/
│   └── dashboard.py        # Gradio UI
├── sql/
│   └── schema.sql          # MySQL schema
├── .env.example            # All required environment variables
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup Instructions

### 1. Clone & Install

```bash
git clone https://github.com/yourrepo/ai-lead-gen.git
cd ai_lead_gen
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 3. MySQL Setup

```bash
mysql -u root -p < sql/schema.sql
```

### 4. Start Flask Backend

```bash
cd backend
python app.py
```

Flask runs on `http://localhost:5000`

### 5. Start Gradio Dashboard

```bash
cd frontend
python dashboard.py
```

Gradio opens on `http://localhost:7860`

---

## 🔑 API Keys & Credentials Needed

| Service | Where to get |
|---------|-------------|
| `GEMINI_API_KEY` | https://aistudio.google.com |
| `META_VERIFY_TOKEN` | Your custom token (any string) |
| `META_PAGE_ACCESS_TOKEN` | Meta Developer Console → App → Page Access Token |
| `META_APP_SECRET` | Meta Developer Console → App Settings |
| `GMAIL_SENDER` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Google Account → Security → App Passwords |
| `MYSQL_*` | Your local/cloud MySQL instance |
| `REDDIT_CLIENT_ID/SECRET` | https://www.reddit.com/prefs/apps |
| `REDDIT_USERNAME/PASSWORD` | Your Reddit bot account |

---

## 🌐 Meta Webhook Setup

1. Go to [Meta Developers](https://developers.facebook.com)
2. Create App → Add **Messenger** and **Instagram** products
3. Under Webhooks → set callback URL: `https://yourdomain.com/webhook`
4. Verify Token: same as `META_VERIFY_TOKEN` in your `.env`
5. Subscribe to: `messages`, `messaging_postbacks`, `instagram_messages`
6. Link your Facebook Page to the app
7. For Instagram: connect your IG Business account through the linked Facebook Page

> **Local testing:** Use [ngrok](https://ngrok.com) to expose localhost:
> ```bash
> ngrok http 5000
> # Use the https URL as your webhook callback
> ```

---

## 🔥 Lead Classification Logic

| Level | Trigger Signals |
|-------|----------------|
| **Hot** 🔥 | Pricing questions, demo request, "buy", "subscribe", "how much" |
| **Warm** 🌡️ | Product questions, feature comparison, general interest |
| **Cold** ❄️ | Generic queries, off-topic, just browsing |

**Escalation** is triggered when:
- Lead is classified as **hot**
- Message contains keywords: pricing, demo, sales call, cost, quote, discount
- AI reply switches to "a specialist will contact you" message
- Sales team gets Gmail alert instantly

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/webhook` | Meta webhook verification |
| POST | `/webhook` | Receive Meta messages |
| GET | `/api/leads` | All CRM leads |
| GET | `/api/leads/<id>` | Lead detail + messages |
| GET | `/api/stats` | Dashboard statistics |
| POST | `/api/simulate` | Test with manual message |
| POST | `/api/daily-summary` | Send daily email report |
| GET | `/health` | Health check |

---

## 🧪 Quick Test (No Meta App Required)

```bash
curl -X POST http://localhost:5000/api/simulate \
  -H "Content-Type: application/json" \
  -d '{"sender_id":"test001","platform":"facebook","text":"Hi, I want to know the pricing for your tile software"}'
```

---

## 🚀 Deployment (Render / Railway)

```bash
# Procfile
web: gunicorn -w 2 -b 0.0.0.0:$PORT backend.app:app
```

Set all `.env` variables in your hosting platform's environment settings.

---

## 📦 Tech Stack

- **Backend:** Python, Flask, Flask-CORS
- **AI/LLM:** Google Gemini 1.5 Flash
- **CRM Database:** MySQL (via mysql-connector-python)
- **Email Alerts:** Gmail SMTP (smtplib)
- **Social Media:** Meta Graph API (Facebook + Instagram), PRAW (Reddit)
- **Frontend:** Gradio
- **Deployment:** Gunicorn
