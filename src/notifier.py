import base64
import os
import requests
from datetime import datetime


class Notifier:
    """
    Invia caption + hashtag + 3 slide allegate via email (Resend).

    Setup (2 minuti, gratuito):
      1. Vai su resend.com → Sign up con la tua Gmail
      2. Dashboard → API Keys → Create API Key
      3. Metti nel .env:  RESEND_API_KEY=re_...
    """

    RESEND_URL = "https://api.resend.com/emails"

    def send(self, content: dict, slides: list[dict]) -> None:
        api_key = os.getenv("RESEND_API_KEY", "")
        if not api_key or api_key.startswith("re_xxx"):
            print("[Email] RESEND_API_KEY non configurata — salto invio email")
            return

        to_email = os.getenv("EMAIL_TO", "")
        if not to_email:
            print("[Email] EMAIL_TO non configurata")
            return

        today = datetime.now().strftime("%d/%m/%Y")
        subject = f"📸 Post Instagram {today} — {content['topic'].title()}"

        attachments = [
            {
                "filename": s["filename"],
                "content": base64.b64encode(s["bytes"]).decode(),
            }
            for s in slides
        ]

        html = self._build_html(content, slides, today)

        payload = {
            "from": "Instagram Agent <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "html": html,
            "attachments": attachments,
        }

        try:
            resp = requests.post(
                self.RESEND_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            print(f"[Email] Inviata a {to_email} ✅")
        except requests.HTTPError as e:
            print(f"[Email] Errore {e.response.status_code}: {e.response.text}")
        except Exception as e:
            print(f"[Email] Errore: {e}")

    def _build_html(self, content: dict, slides: list[dict], today: str) -> str:
        hashtags_html = " ".join(
            f"<span style='color:#833ab4;font-weight:600'>#{h.lstrip('#')}</span>"
            for h in content["hashtags"]
        )
        caption_html = content["caption"].replace("\n", "<br>")

        slides_html = ""
        for i, s in enumerate(slides):
            b64 = base64.b64encode(s["bytes"]).decode()
            slides_html += f"""
            <div style='text-align:center;margin:16px 0'>
              <p style='margin:4px 0;color:#555;font-size:13px'>Slide {i+1} — allegata come <b>{s['filename']}</b></p>
              <img src='data:image/png;base64,{b64}'
                   style='width:100%;max-width:400px;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.15)'
                   alt='Slide {i+1}'>
            </div>"""

        return f"""<!DOCTYPE html>
<html><body style='font-family:Arial,sans-serif;max-width:680px;margin:auto;
                   background:#f5f5f5;padding:20px'>

<div style='background:linear-gradient(135deg,#833ab4,#fd1d1d,#fcb045);
            color:white;padding:28px;border-radius:12px 12px 0 0;text-align:center'>
  <h1 style='margin:0;font-size:26px'>📸 Post Instagram</h1>
  <p style='margin:6px 0 0;opacity:.9;font-size:16px'>{today} · <b>{content['topic'].title()}</b></p>
</div>

<div style='background:white;padding:28px;border-radius:0 0 12px 12px;
            box-shadow:0 4px 20px rgba(0,0,0,.08)'>

  <!-- SLIDE IMAGES -->
  <h2 style='color:#333;border-bottom:2px solid #fcb045;padding-bottom:8px'>
    🎨 Le tue 3 Slide (allegate)
  </h2>
  <p style='color:#666;font-size:14px'>
    Le slide sono allegate a questa email come file PNG pronti da pubblicare.
  </p>
  {slides_html}

  <!-- CAPTION -->
  <h2 style='color:#333;border-bottom:2px solid #833ab4;padding-bottom:8px;margin-top:32px'>
    📝 Caption (copia e incolla su Instagram)
  </h2>
  <div style='background:#fff8f0;border:1px solid #fce4c0;padding:20px;
              border-radius:8px;font-size:15px;line-height:1.7;
              white-space:pre-wrap;font-family:Georgia,serif'>
    {caption_html}
  </div>
  <button onclick="navigator.clipboard.writeText(this.dataset.text)"
          data-text="{content['caption'].replace(chr(34), '&quot;')}"
          style='margin-top:10px;background:#833ab4;color:white;border:none;
                 padding:10px 20px;border-radius:6px;cursor:pointer;font-size:14px'>
    📋 Copia Caption
  </button>

  <!-- HASHTAG -->
  <h2 style='color:#333;border-bottom:2px solid #fd1d1d;padding-bottom:8px;margin-top:32px'>
    🏷️ Hashtag ({len(content['hashtags'])})
  </h2>
  <div style='line-height:2.2;font-size:14px'>{hashtags_html}</div>

</div>

<p style='color:#aaa;font-size:12px;text-align:center;margin-top:16px'>
  Generato automaticamente da Instagram Agent · {today}
</p>
</body></html>"""
