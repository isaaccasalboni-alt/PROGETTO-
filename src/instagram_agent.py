import json
import os
import requests
from datetime import datetime

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """Sei un esperto di marketing digitale e content creator specializzato in contenuti Instagram virali.

Per ogni richiesta genera un JSON valido con questa struttura ESATTA (niente testo prima o dopo):
{
  "topic": "argomento del giorno",
  "caption": "caption completa per Instagram (max 2200 caratteri), con emoji e call-to-action finale",
  "hashtags": ["hashtag1", "hashtag2"],
  "slide_sections": [
    {
      "title": "titolo breve della slide (max 6 parole)",
      "content": "testo della slide su 2-3 righe, conciso e impattante",
      "image_description": "descrizione visiva dell'immagine ideale per questa slide"
    }
  ]
}

Regole OBBLIGATORIE:
- caption coinvolgente con storytelling e call-to-action finale
- Esattamente 25 hashtag (mix popolari e di nicchia)
- Esattamente 3 slide_sections (non di più, non di meno)
- Ogni slide: titolo breve + contenuto su max 3 righe
- Rispondi SOLO con il JSON, senza markdown, senza ```json```"""

TOPICS_POOL = [
    "produttività e organizzazione",
    "mindset e crescita personale",
    "business e imprenditoria",
    "benessere e salute mentale",
    "tecnologia e innovazione",
    "finanza personale",
    "marketing digitale",
    "leadership e team building",
    "creatività e design",
    "sostenibilità e ambiente",
]


class InstagramAgent:
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY non impostata nel .env")
        self.language = os.getenv("CONTENT_LANGUAGE", "italiano")

    def generate_daily_content(self, topic: str | None = None) -> dict:
        today = datetime.now().strftime("%d %B %Y")
        effective_topic = topic or os.getenv("DEFAULT_TOPIC") or ""

        user_message = (
            f"Crea il contenuto Instagram per oggi, {today}.\n\n"
            + (f"Argomento: {effective_topic}\n\n" if effective_topic
               else f"Scegli il più rilevante tra: {', '.join(TOPICS_POOL)}.\n\n")
            + f"Lingua: {self.language}\n"
            + "Genera JSON con caption, 25 hashtag ed ESATTAMENTE 3 slide."
        )

        print(f"\n[Groq/Llama] Generazione contenuto — {today}")
        print("-" * 50)

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.9,
            "max_tokens": 4096,
        }

        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=60,
        )
        if not resp.ok:
            raise ValueError(f"Errore Groq {resp.status_code}: {resp.text}")

        full_response = resp.json()["choices"][0]["message"]["content"]
        print(full_response[:300] + "..." if len(full_response) > 300 else full_response)
        print("-" * 50)

        j_start = full_response.find("{")
        j_end = full_response.rfind("}") + 1
        if j_start == -1 or j_end <= j_start:
            raise ValueError("Risposta Gemini non contiene JSON valido")

        content = json.loads(full_response[j_start:j_end])
        self._validate(content)
        content["slide_sections"] = content["slide_sections"][:3]
        return content

    def _validate(self, c: dict) -> None:
        for field in ["topic", "caption", "hashtags", "slide_sections"]:
            if field not in c:
                raise ValueError(f"Campo mancante: {field}")
        if not c["slide_sections"]:
            raise ValueError("slide_sections è vuota")
