import os
import requests
from datetime import datetime


class GammaClient:
    """
    Client per l'API di Gamma (gamma.app).

    Setup:
    1. Vai su gamma.app > Settings > API
    2. Crea un API key
    3. Imposta GAMMA_API_KEY nel file .env

    Documentazione API: https://gamma.app/docs/api (richiede accesso beta)
    """

    BASE_URL = "https://api.gamma.app/v1"

    def __init__(self):
        self.api_key = os.environ.get("GAMMA_API_KEY", "")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "your_gamma_api_key_here")

    def create_deck(self, title: str, slide_sections: list[dict]) -> dict:
        """
        Crea un deck Gamma con le slide generate dall'agente Instagram.

        Args:
            title: Titolo del deck
            slide_sections: Lista di dizionari con 'title', 'content', 'image_description'

        Returns:
            dict con 'deck_id', 'deck_url', 'share_url'
        """
        if not self.is_configured():
            print("[Gamma] API key non configurata — salto creazione deck")
            return self._mock_deck_response(title)

        cards = self._build_cards(slide_sections)

        payload = {
            "title": title,
            "theme": "modern",
            "cards": cards,
            "ai_generation": True,
        }

        try:
            response = self.session.post(
                f"{self.BASE_URL}/decks",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            deck_id = data.get("id", "")
            deck_url = data.get("url", f"https://gamma.app/deck/{deck_id}")
            share_url = data.get("share_url", deck_url)

            print(f"[Gamma] Deck creato: {deck_url}")
            return {
                "deck_id": deck_id,
                "deck_url": deck_url,
                "share_url": share_url,
            }

        except requests.exceptions.HTTPError as e:
            print(f"[Gamma] Errore HTTP {e.response.status_code}: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"[Gamma] Errore di connessione: {e}")
            raise

    def _build_cards(self, slide_sections: list[dict]) -> list[dict]:
        cards = []
        for section in slide_sections:
            card = {
                "title": section.get("title", ""),
                "content": section.get("content", ""),
                "layout": "text_and_image",
            }
            image_desc = section.get("image_description", "")
            if image_desc:
                card["image_prompt"] = image_desc
            cards.append(card)
        return cards

    def _mock_deck_response(self, title: str) -> dict:
        """Risposta simulata quando l'API Gamma non è configurata."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mock_id = f"mock_{timestamp}"
        print(f"[Gamma] Modalità simulazione — deck_id: {mock_id}")
        return {
            "deck_id": mock_id,
            "deck_url": f"https://gamma.app/deck/{mock_id}",
            "share_url": f"https://gamma.app/deck/{mock_id}",
        }

    def get_deck(self, deck_id: str) -> dict:
        """Recupera i dettagli di un deck esistente."""
        if not self.is_configured():
            return {"id": deck_id, "status": "mock"}

        response = self.session.get(
            f"{self.BASE_URL}/decks/{deck_id}",
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
