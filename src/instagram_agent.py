import json
import os
import anthropic
from datetime import datetime

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
- Rispondi SOLO con il JSON"""

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

        user_message = (
            f"Crea il contenuto Instagram per oggi, {today}.\n\n"
            + (f"Argomento: {effective_topic}\n\n" if effective_topic
               else f"Scegli il più rilevante tra: {', '.join(TOPICS_POOL)}.\n\n")
            + f"Lingua: {self.language}\n"
            + "Genera JSON con caption, 25 hashtag ed ESATTAMENTE 3 slide."
        )

        print(f"\n[Claude] Generazione contenuto — {today}")
        print("-" * 50)

        full_response = ""
        with self.client.messages.stream(
            model=self.model,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                print(text, end="", flush=True)

        print("\n" + "-" * 50)

        j_start = full_response.find("{")
        j_end = full_response.rfind("}") + 1
        if j_start == -1 or j_end <= j_start:
            raise ValueError("Risposta Claude non contiene JSON valido")

        content = json.loads(full_response[j_start:j_end])
        self._validate(content)
        # Forza esattamente 3 slide
        content["slide_sections"] = content["slide_sections"][:3]
        return content

    def _validate(self, c: dict) -> None:
        for field in ["topic", "caption", "hashtags", "slide_sections"]:
            if field not in c:
                raise ValueError(f"Campo mancante: {field}")
        if not c["slide_sections"]:
            raise ValueError("slide_sections è vuota")
