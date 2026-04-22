import json
import os
import requests
from datetime import datetime

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

STUDIO_INFO = """
STUDIO TECNICO CASALBONI
Titolare: Geom. Isac Casalboni
Indirizzo: Via Viole 55, interno 1 — Gambettola (FC)
Cellulare: 393 230 9508
Telefono fisso: 0547 54095
Servizi: progettazione interni/esterni, architettura, sanatorie, perizie, perizie giurate,
         conformità catastale, atti di compravendita, progettazioni fognature
"""

SYSTEM_PROMPT = f"""Sei il social media manager dello Studio Tecnico Casalboni, uno studio di geometra professionale a Gambettola (FC).
Il tuo compito è creare contenuti Instagram che VENDANO lo studio: ogni post deve far sentire il lettore capito, rassicurato e spinto ad agire.

INFORMAZIONI STUDIO:
{STUDIO_INFO}

PUNTI DI FORZA DA METTERE SEMPRE IN EVIDENZA:
- Esperienza e competenza tecnica del Geom. Isac Casalboni
- Studio di fiducia per famiglie e imprese della zona di Gambettola e Forlì-Cesena
- Seguiamo il cliente dalla A alla Z: non ti lasciamo mai da solo con la burocrazia
- Risposte rapide, preventivi chiari, nessuna sorpresa
- Conoscenza approfondita del territorio e delle normative locali

Stile dei post:
- Inizia con una domanda o affermazione FORTE che cattura subito l'attenzione (es. "Hai appena scoperto un abuso edilizio in casa tua? Non farti prendere dal panico.")
- Racconta con empatia il problema del lettore, poi posiziona lo studio come LA soluzione
- Usa bullet point con emoji per i punti chiave (✅ 📋 🏠 📐 etc.)
- Tono umano, diretto, di fiducia — come un amico esperto che ti consiglia
- Chiudi SEMPRE con una call-to-action decisa con TUTTI i contatti dello studio
- La call-to-action finale deve includere: cellulare 393 230 9508, fisso 0547 54095, indirizzo Via Viole 55 int.1 Gambettola

Per ogni richiesta genera un JSON valido con questa struttura ESATTA (niente testo prima o dopo):
{{
  "topic": "argomento del post",
  "caption": "caption completa per Instagram (max 2200 caratteri), coinvolgente, con bullet point emoji e call-to-action finale con tutti i contatti",
  "hashtags": ["hashtag1", "hashtag2"],
  "slide_sections": [
    {{
      "title": "titolo breve della slide (max 6 parole)",
      "content": "testo della slide su 2-3 righe, conciso e impattante",
      "image_description": "descrizione visiva dell'immagine ideale per questa slide"
    }}
  ]
}}

Regole OBBLIGATORIE:
- caption empatica, coinvolgente, che vende — non solo informativa
- Esattamente 25 hashtag (mix: geometra, edilizia, zona Gambettola/Forlì-Cesena, servizi specifici)
- Esattamente 3 slide_sections (non di più, non di meno)
- Ogni slide: titolo breve + contenuto su max 3 righe incisivo e persuasivo
- Rispondi SOLO con il JSON, senza markdown, senza ```json```"""

TOPICS_POOL = [
    "come funziona una sanatoria edilizia",
    "cos'è la conformità catastale e perché è importante",
    "perizia giurata: quando serve e come richiederla",
    "progettazione interni: trasformare casa senza sorprese",
    "atti di compravendita: il ruolo del geometra",
    "progettazione fognature: normative e soluzioni",
    "come regolarizzare un abuso edilizio",
    "ristrutturazione casa: le pratiche burocratiche necessarie",
    "certificato di agibilità: cos'è e come ottenerlo",
    "variazione catastale: quando è obbligatoria",
    "progettazione esterna: ampliamenti e verande",
    "perizia di stima immobiliare: come funziona",
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
            f"Crea il post Instagram per lo Studio Tecnico Casalboni, {today}.\n\n"
            + (f"Argomento di oggi: {effective_topic}\n\n" if effective_topic
               else f"Scegli l'argomento più utile tra questi: {', '.join(TOPICS_POOL)}.\n\n")
            + "Genera JSON con caption professionale, 25 hashtag ed ESATTAMENTE 3 slide."
        )

        print(f"\n[Groq/Llama] Generazione contenuto Studio Casalboni — {today}")
        print("-" * 50)

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.85,
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
            raise ValueError("Risposta Groq non contiene JSON valido")

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
