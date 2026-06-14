"""
frontend/dashboard.py - Simple Gradio dashboard (compatible version)
"""
import os
import requests
import gradio as gr

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

def _get(path):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def _post(path, body):
    try:
        r = requests.post(f"{API_BASE}{path}", json=body, timeout=15)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def simulate_message(sender_id, platform, text):
    if not text.strip():
        return "Please enter a message.", ""
    result = _post("/api/simulate", {
        "sender_id": sender_id or "gradio_test_user",
        "platform": platform,
        "text": text,
    })
    if "error" in result:
        return f"Error: {result['error']}", ""
    interest = result.get("interest_level", "?").upper()
    emoji = {"HOT": "🔥", "WARM": "🌡️", "COLD": "❄️"}.get(interest, "")
    info = (f"Lead ID: #{result.get('lead_id')}\n"
            f"Interest: {emoji} {interest}\n"
            f"Escalated: {'Yes ⚡' if result.get('escalated') else 'No'}")
    return info, result.get("reply", "")

def load_leads(filter_level):
    data = _get("/api/leads")
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data['error']}"
    if filter_level != "All":
        data = [l for l in data if l.get("interest_level") == filter_level.lower()]
    lines = []
    for l in data:
        esc = "⚡Yes" if l.get("escalated") else "No"
        lines.append(
            f"#{l.get('id')} | {l.get('name') or 'Unknown'} | "
            f"{l.get('platform','').title()} | {l.get('interest_level','').upper()} | "
            f"Escalated:{esc} | {str(l.get('updated_at',''))[:16]}"
        )
    return "\n".join(lines) if lines else "No leads found."

def load_lead_detail(lead_id):
    if not str(lead_id).strip().isdigit():
        return "Enter a valid lead ID", ""
    data = _get(f"/api/leads/{lead_id}")
    if "error" in data:
        return f"Error: {data['error']}", ""
    lead = data.get("lead", {})
    msgs = data.get("messages", [])
    info = (f"Name: {lead.get('name') or 'Unknown'}\n"
            f"Platform: {lead.get('platform','').title()}\n"
            f"Interest: {lead.get('interest_level','').upper()}\n"
            f"Contact: {lead.get('contact_details') or 'N/A'}\n"
            f"Escalated: {'Yes' if lead.get('escalated') else 'No'}\n\n"
            f"Summary:\n{lead.get('conversation_summary') or 'N/A'}")
    convo = "\n".join(
        f"[{m['direction'].upper()}] {m['content']}" for m in msgs
    )
    return info, convo or "No messages."

def load_stats():
    stats = _get("/api/stats")
    if "error" in stats:
        return f"Error: {stats['error']}"
    lines = [
        f"Total Leads:  {stats.get('total', 0)}",
        f"🔥 Hot:       {stats.get('hot', 0)}",
        f"🌡️  Warm:      {stats.get('warm', 0)}",
        f"❄️  Cold:      {stats.get('cold', 0)}",
        f"⚡ Escalated: {stats.get('escalated', 0)}",
        "", "By Platform:",
    ]
    for p in stats.get("by_platform", []):
        lines.append(f"  {p['platform'].title()}: {p['cnt']}")
    return "\n".join(lines)

def send_daily_report():
    result = _post("/api/daily-summary", {})
    return "✅ Daily summary sent!" if result.get("status") == "sent" else f"❌ {result}"

with gr.Blocks(title="AI Lead Generation CRM") as demo:
    gr.Markdown("# 🤖 AI Lead Generation CRM\n**Gemini AI • MySQL • Meta Webhook • Gmail Alerts**")

    with gr.Tab("💬 Simulate Message"):
        gr.Markdown("### Test the AI pipeline")
        with gr.Row():
            sim_sender = gr.Textbox(label="Sender ID", value="user_001")
            sim_platform = gr.Dropdown(["facebook","instagram","reddit","website"], label="Platform", value="facebook")
        sim_text = gr.Textbox(label="Customer Message", lines=3, placeholder="e.g. Hi, I want pricing for your tile software")
        sim_btn = gr.Button("🚀 Process Message", variant="primary")
        sim_result = gr.Textbox(label="Lead Classification", lines=4)
        sim_reply = gr.Textbox(label="AI Auto-Reply", lines=4)
        sim_btn.click(simulate_message, inputs=[sim_sender, sim_platform, sim_text], outputs=[sim_result, sim_reply])

    with gr.Tab("📋 All Leads"):
        gr.Markdown("### CRM Leads from MySQL")
        leads_filter = gr.Dropdown(["All","Hot","Warm","Cold"], label="Filter", value="All")
        leads_btn = gr.Button("🔄 Refresh Leads", variant="primary")
        leads_out = gr.Textbox(label="Leads", lines=15)
        leads_btn.click(load_leads, inputs=[leads_filter], outputs=[leads_out])

    with gr.Tab("🔍 Lead Detail"):
        gr.Markdown("### View specific lead")
        detail_id = gr.Textbox(label="Lead ID", placeholder="e.g. 1")
        detail_btn = gr.Button("🔎 Load", variant="primary")
        with gr.Row():
            detail_info = gr.Textbox(label="Lead Info", lines=10)
            detail_convo = gr.Textbox(label="Conversation", lines=10)
        detail_btn.click(load_lead_detail, inputs=[detail_id], outputs=[detail_info, detail_convo])

    with gr.Tab("📊 Stats"):
        gr.Markdown("### Live Statistics")
        stats_btn = gr.Button("📈 Load Stats", variant="primary")
        stats_out = gr.Textbox(label="Statistics", lines=12)
        report_btn = gr.Button("📧 Send Daily Email Report")
        report_out = gr.Textbox(label="Email Status", lines=1)
        stats_btn.click(load_stats, outputs=[stats_out])
        report_btn.click(send_daily_report, outputs=[report_out])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, share=True)