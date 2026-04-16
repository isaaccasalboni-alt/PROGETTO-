"""
Test rapido invio email Gmail.
Esegui con: python test_email.py
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def test_email():
    sender   = os.getenv("EMAIL_FROM", "")
    recipient = os.getenv("EMAIL_TO", sender)
    password = os.getenv("EMAIL_APP_PASSWORD", "")

    if not sender or not password:
        print("❌  EMAIL_FROM e EMAIL_APP_PASSWORD non configurati nel file .env")
        print("    Segui le istruzioni nel README per creare la App Password Gmail.")
        return

    print(f"📧  Invio email di test a: {recipient}")

    html = f"""
<!DOCTYPE html><html><body style='font-family:Arial,sans-serif;max-width:600px;margin:auto'>
<div style='background:#0095f6;color:white;padding:20px;border-radius:8px 8px 0 0'>
  <h1 style='margin:0'>✅ Test Instagram Agent</h1>
</div>
<div style='padding:20px;border:1px solid #ddd;border-radius:0 0 8px 8px'>
  <p>L'email funziona correttamente!</p>
  <p>Ogni giorno riceverai qui il post Instagram completo con:</p>
  <ul>
    <li>📝 Caption pronta da copiare</li>
    <li>🏷️ Hashtag ottimizzati</li>
    <li>🎞️ Link al deck Gamma con le slide</li>
  </ul>
  <p style='color:#888;font-size:13px'>Test inviato il {datetime.now().strftime("%d/%m/%Y alle %H:%M")}</p>
</div>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "✅ Test Instagram Agent — tutto funziona!"
    msg["From"]    = sender
    msg["To"]      = recipient
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        print(f"✅  Email inviata! Controlla la casella: {recipient}")
    except smtplib.SMTPAuthenticationError:
        print("❌  Autenticazione fallita.")
        print("    Assicurati di usare la APP PASSWORD (non la password Gmail normale).")
        print("    Guida: myaccount.google.com → Sicurezza → Password per le app")
    except Exception as e:
        print(f"❌  Errore: {e}")


if __name__ == "__main__":
    test_email()
