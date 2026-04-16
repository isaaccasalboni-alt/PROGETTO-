import json
import os
import anthropic
from datetime import datetime

SYSTEM_PROMPT = """Sei un esperto di marketing digitale e content creator specializzato in contenuti Instagram virali.
Il tuo compito è creare contenuti professionali e coinvolgenti per post Instagram giornalieri.

Per ogni richiesta devi generare un JSON valido con questa struttura ESATTA:
{
  "topic": "argomento del giorno",
  "caption": "caption completa per Instagram (max 2200 caratteri), con emoji appropriate e call-to-action",
  "hashtags": ["hashtag1", "hashtag2", "..."],
  "slide_sections": [
    {
      "title": "titolo della slide",
      "content": "testo della slide (conciso e visivamente leggibile)",
      "image_description": "descrizione dettagliata dell'immagine da generare per questa slide"
    }
  ]
}

Regole:
- La caption deve essere coinvolgente, con storytelling e call-to-action finale
- Includi 20-30 hashtag strategici (mix di popolari e di nicchia)
- Crea 5-7 slide_sections per formare una presentazione Gamma completa
- Ogni slide deve avere contenuto visivamente equilibrato
- Usa emoji in modo strategico nella caption
- Rispondi SOLO con il JSON, nessun testo aggiuntivo prima o dopo"""

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
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = "claude-opus-4-7"
        self.language = os.getenv("CONTENT_LANGUAGE", "italiano")

    def generate_daily_content(self, topic: str | None = None) -> dict:
        today = datetime.now().strftime("%d %B %Y")
        effective_topic = topic or os.getenv("DEFAULT_TOPIC") or ""

        user_message = f"""Crea il contenuto Instagram completo per oggi, {today}.

{"Argomento specifico: " + effective_topic if effective_topic else f"Scegli l'argomento più rilevante tra questi: {', '.join(TOPICS_POOL)}. Scegli quello più adatto per oggi e per il pubblico italiano."}

Lingua contenuti: {self.language}

Genera il JSON completo con caption, hashtag e outline per 5-7 slide Gamma."""

        print(f"\n[Claude] Generazione contenuto per: {today}")
        print("-" * 50)

        full_response = ""

        with self.client.messages.stream(
            model=self.model,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                print(text, end="", flush=True)

        print("\n" + "-" * 50)

        json_start = full_response.find("{")
        json_end = full_response.rfind("}") + 1
        if json_start == -1 or json_end <= json_start:
            raise ValueError("Nessun JSON valido nella risposta di Claude")

        content = json.loads(full_response[json_start:json_end])
        self._validate_content(content)
        return content

    def _validate_content(self, content: dict) -> None:
        required = ["topic", "caption", "hashtags", "slide_sections"]
        for field in required:
            if field not in content:
                raise ValueError(f"Campo mancante nel contenuto generato: {field}")
        if not isinstance(content["slide_sections"], list) or len(content["slide_sections"]) < 1:
            raise ValueError("slide_sections deve essere una lista non vuota")
