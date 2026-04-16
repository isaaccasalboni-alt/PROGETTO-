import os
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


class Notifier:
    """
    Invia il contenuto generato via Email e/o Telegram.

    Configura nel .env:
      EMAIL_FROM, EMAIL_TO, EMAIL_APP_PASSWORD  → Gmail
      TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID      → Telegram
    """

    def send(self, content: dict, deck_info: dict) -> None:
        sent = False

        if os.getenv("EMAIL_FROM") and os.getenv("EMAIL_APP_PASSWORD"):
            try:
                self._send_email(content, deck_info)
                sent = True
            except Exception as e:
                print(f"[Notifier] Errore email: {e}")

        if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
            try:
                self._send_telegram(content, deck_info)
                sent = True
            except Exception as e:
                print(f"[Notifier] Errore Telegram: {e}")

        if not sent:
            print("[Notifier] Nessun canale configurato — output solo in logs/")

    # ── EMAIL ──────────────────────────────────────────────────────────────────

    def _send_email(self, content: dict, deck_info: dict) -> None:
        sender = os.environ["EMAIL_FROM"]
        recipient = os.getenv("EMAIL_TO", sender)
        password = os.environ["EMAIL_APP_PASSWORD"]

        today = datetime.now().strftime("%d/%m/%Y")
        subject = f"📸 Post Instagram del {today} — {content['topic'].title()}"

        html = self._build_html_email(content, deck_info, today)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())

        print(f"[Email] Inviata a {recipient}")

    def _build_html_email(self, content: dict, deck_info: dict, today: str) -> str:
        hashtags_html = " ".join(f"<span style='color:#0095f6'>#{h.lstrip('#')}</span>"
                                  for h in content["hashtags"])
        slides_html = "".join(
            f"""<div style='background:#f8f9fa;border-left:4px solid #0095f6;
                margin:8px 0;padding:12px;border-radius:4px'>
                <b>{s['title']}</b><br>
                <span style='color:#555'>{s['content']}</span>
                </div>"""
            for s in content["slide_sections"]
        )
        caption_escaped = content["caption"].replace("\n", "<br>")

        return f"""
<!DOCTYPE html><html><body style='font-family:Arial,sans-serif;max-width:680px;margin:auto;color:#222'>
<div style='background:#0095f6;color:white;padding:20px;border-radius:8px 8px 0 0'>
  <h1 style='margin:0'>📸 Post Instagram — {today}</h1>
  <p style='margin:4px 0 0;opacity:.85'>Argomento: <b>{content['topic'].title()}</b></p>
</div>
<div style='padding:20px;border:1px solid #ddd;border-top:none;border-radius:0 0 8px 8px'>

  <h2>📝 Caption</h2>
  <div style='background:#fff8f0;padding:16px;border-radius:8px;font-size:15px;line-height:1.6'>
    {caption_escaped}
  </div>

  <h2>🏷️ Hashtag ({len(content['hashtags'])})</h2>
  <div style='line-height:2;font-size:14px'>{hashtags_html}</div>

  <h2>🎞️ Deck Gamma ({len(content['slide_sections'])} slide)</h2>
  <a href='{deck_info['deck_url']}' style='background:#0095f6;color:white;
     padding:12px 24px;border-radius:6px;text-decoration:none;display:inline-block;
     font-weight:bold'>Apri il deck Gamma →</a>
  {slides_html}

</div>
<p style='color:#aaa;font-size:12px;text-align:center'>
  Generato automaticamente da Instagram Agent · {today}
</p>
</body></html>"""

    # ── TELEGRAM ───────────────────────────────────────────────────────────────

    def _send_telegram(self, content: dict, deck_info: dict) -> None:
        token = os.environ["TELEGRAM_BOT_TOKEN"]
        chat_id = os.environ["TELEGRAM_CHAT_ID"]
        today = datetime.now().strftime("%d/%m/%Y")

        hashtags_str = " ".join(f"#{h.lstrip('#')}" for h in content["hashtags"][:15])

        text = (
            f"📸 *Post Instagram — {today}*\n"
            f"Argomento: _{content['topic'].title()}_\n\n"
            f"*CAPTION:*\n{content['caption'][:800]}{'...' if len(content['caption']) > 800 else ''}\n\n"
            f"*HASHTAG:*\n{hashtags_str}\n\n"
            f"*DECK GAMMA ({len(content['slide_sections'])} slide):*\n"
            f"{deck_info['deck_url']}"
        )

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }, timeout=15)
        resp.raise_for_status()
        print(f"[Telegram] Messaggio inviato al chat_id {chat_id}")
