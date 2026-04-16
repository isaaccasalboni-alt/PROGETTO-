"""
Debug passo-passo della configurazione email.
Esegui con: python debug_email.py
"""

import os
import smtplib
from dotenv import load_dotenv

load_dotenv()

sender   = os.getenv("EMAIL_FROM", "")
password = os.getenv("EMAIL_APP_PASSWORD", "")
recipient = os.getenv("EMAIL_TO", sender)

print("=" * 50)
print("DEBUG CONFIGURAZIONE EMAIL")
print("=" * 50)

# Step 1 — controlla variabili
print(f"\n1. EMAIL_FROM       : {sender or '❌ NON IMPOSTATA'}")
print(f"   EMAIL_TO         : {recipient or '❌ NON IMPOSTATA'}")
if password:
    pwd_clean = password.replace(" ", "")
    print(f"   EMAIL_APP_PASSWORD: {'*' * len(pwd_clean)} ({len(pwd_clean)} caratteri)")
    if len(pwd_clean) != 16:
        print(f"   ⚠️  La App Password deve essere 16 caratteri, trovati {len(pwd_clean)}")
else:
    print("   EMAIL_APP_PASSWORD: ❌ NON IMPOSTATA")

if not sender or not password:
    print("\n❌ Configura EMAIL_FROM e EMAIL_APP_PASSWORD nel file .env")
    exit(1)

# Step 2 — connessione SMTP
print("\n2. Connessione a smtp.gmail.com:465 ...")
try:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
    print("   ✅ Connessione riuscita")
except Exception as e:
    print(f"   ❌ Connessione fallita: {e}")
    exit(1)

# Step 3 — login
print(f"\n3. Login come {sender} ...")
try:
    pwd_clean = password.replace(" ", "")
    server.login(sender, pwd_clean)
    print("   ✅ Login riuscito")
except smtplib.SMTPAuthenticationError as e:
    print("   ❌ LOGIN FALLITO — App Password non corretta o 2FA non attiva")
    print("\n   Soluzione:")
    print("   → Vai su myaccount.google.com/security")
    print("   → Attiva 'Verifica in 2 passaggi'")
    print("   → Cerca 'Password per le app' → genera una nuova")
    print("   → Copia i 16 caratteri nel .env (senza spazi)")
    server.quit()
    exit(1)
except Exception as e:
    print(f"   ❌ Errore: {e}")
    server.quit()
    exit(1)

# Step 4 — invio
print(f"\n4. Invio email a {recipient} ...")
try:
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart()
    msg["Subject"] = "✅ Test Instagram Agent — funziona!"
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(
        "<h2>✅ Email configurata correttamente!</h2>"
        "<p>L'agente Instagram può inviarti i post ogni giorno.</p>",
        "html", "utf-8"
    ))

    server.sendmail(sender, recipient, msg.as_string())
    server.quit()
    print(f"   ✅ Email inviata! Controlla {recipient}")
    print("\n✅ TUTTO OK — ora puoi lanciare: python main.py")
except Exception as e:
    print(f"   ❌ Invio fallito: {e}")
    server.quit()
