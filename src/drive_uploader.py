import io
import json
import os
from datetime import datetime


class DriveUploader:
    """
    Salva i post Instagram generati su Google Drive.

    Setup (una volta sola):
      1. Vai su console.cloud.google.com → nuovo progetto
      2. Cerca "Drive API" → abilitala
      3. IAM e amministrazione → Account di servizio → Crea
      4. Scarica il file JSON delle credenziali → rinominalo 'credentials.json'
      5. Mettilo nella cartella del progetto
      6. Crea una cartella su Google Drive → tasto destro → Condividi →
         incolla l'email del service account (es. agent@progetto.iam.gserviceaccount.com)
      7. Copia l'ID della cartella (nell'URL di Drive dopo /folders/)
         → mettilo come GOOGLE_DRIVE_FOLDER_ID nel .env
    """

    SCOPES = ["https://www.googleapis.com/auth/drive.file"]
    CREDENTIALS_FILE = "credentials.json"

    def __init__(self):
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
        self.service = None

    def is_configured(self) -> bool:
        return (
            os.path.exists(self.CREDENTIALS_FILE)
            and bool(self.folder_id)
            and self.folder_id != "metti_qui_id_cartella_drive"
        )

    def _get_service(self):
        if self.service:
            return self.service
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(
            self.CREDENTIALS_FILE, scopes=self.SCOPES
        )
        self.service = build("drive", "v3", credentials=creds)
        return self.service

    def upload(self, content: dict) -> dict:
        """
        Carica su Drive un file di testo formattato con il post del giorno.
        Ritorna i link ai file caricati.
        """
        if not self.is_configured():
            print("[Drive] Non configurato — salto upload")
            return {}

        service = self._get_service()
        today = datetime.now().strftime("%Y-%m-%d")
        links = {}

        # File 1 — Post completo (testo formattato, pronto da copiare)
        post_text = self._format_post(content)
        post_link = self._upload_file(
            service,
            name=f"Instagram_{today}.txt",
            content=post_text,
            mime_type="text/plain",
        )
        links["post"] = post_link
        print(f"[Drive] Post caricato: {post_link}")

        # File 2 — Dati completi in JSON (archivio)
        json_text = json.dumps(
            {**content, "date": today},
            ensure_ascii=False,
            indent=2,
        )
        json_link = self._upload_file(
            service,
            name=f"Dati_{today}.json",
            content=json_text,
            mime_type="application/json",
        )
        links["json"] = json_link
        print(f"[Drive] Dati JSON caricati: {json_link}")

        return links

    def _upload_file(
        self, service, name: str, content: str, mime_type: str
    ) -> str:
        metadata = {"name": name, "parents": [self.folder_id]}
        from googleapiclient.http import MediaIoBaseUpload
        media = MediaIoBaseUpload(
            io.BytesIO(content.encode("utf-8")),
            mimetype=mime_type,
        )
        file = (
            service.files()
            .create(body=metadata, media_body=media, fields="id,webViewLink")
            .execute()
        )
        return file.get("webViewLink", "")

    def _format_post(self, content: dict) -> str:
        today = datetime.now().strftime("%d/%m/%Y")
        hashtags = " ".join(f"#{h.lstrip('#')}" for h in content["hashtags"])
        slides = "\n".join(
            f"\n  Slide {i+1}: {s['title']}\n  {s['content']}"
            for i, s in enumerate(content["slide_sections"])
        )
        return f"""POST INSTAGRAM — {today}
Argomento: {content['topic']}
{'=' * 60}

CAPTION (copia e incolla su Instagram):
{content['caption']}

{'=' * 60}
HASHTAG ({len(content['hashtags'])}):
{hashtags}

{'=' * 60}
SLIDE ({len(content['slide_sections'])}):
{slides}

{'=' * 60}
Generato il {datetime.now().strftime("%d/%m/%Y alle %H:%M")}
"""
