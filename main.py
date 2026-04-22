import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def run_daily_task(topic: str | None = None) -> None:
    from src.instagram_agent import InstagramAgent
    from src.slide_generator import generate_slides
    from src.notifier import Notifier

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"=== Task avviato: {timestamp} ===")

    # 1. Genera contenuto con Groq/Llama
    logger.info("Generazione contenuto con Groq...")
    agent = InstagramAgent()
    content = agent.generate_daily_content(topic=topic)
    logger.info(f"Argomento: {content['topic']}")

    # 2. Genera 3 slide PNG
    logger.info("Generazione slide PNG...")
    slides = generate_slides(content["slide_sections"])
    logger.info(f"Generate {len(slides)} slide")

    # 3. Salva tutto in logs/
    date_str = datetime.now().strftime("%Y-%m-%d")
    _save_txt(content, date_str)
    _save_slides(slides, date_str)

    # 4. Stampa riepilogo
    _print_summary(content, slides)

    # 5. Invia email (opzionale, se RESEND_API_KEY configurata)
    notifier = Notifier()
    notifier.send(content, slides)


def _save_txt(content: dict, date_str: str) -> None:
    hashtags_str = " ".join(f"#{h.lstrip('#')}" for h in content["hashtags"])
    txt = f"""POST INSTAGRAM — {date_str}
Argomento: {content['topic']}
{'=' * 60}

CAPTION:
{content['caption']}

{'=' * 60}
HASHTAG ({len(content['hashtags'])}):
{hashtags_str}
"""
    path = LOG_DIR / f"post_{date_str}.txt"
    path.write_text(txt, encoding="utf-8")
    logger.info(f"Salvato: {path}")


def _save_slides(slides: list, date_str: str) -> None:
    slides_dir = LOG_DIR / f"slide_{date_str}"
    slides_dir.mkdir(exist_ok=True)
    for s in slides:
        p = slides_dir / s["filename"]
        p.write_bytes(s["bytes"])
        logger.info(f"Slide: {p} ({len(s['bytes'])//1024} KB)")


def _print_summary(content: dict, slides: list) -> None:
    print("\n" + "=" * 60)
    print(f"Argomento: {content['topic']}")
    print(f"Caption: {len(content['caption'])} caratteri")
    print(f"Hashtag: {len(content['hashtags'])}")
    print(f"Slide: {len(slides)}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default=None)
    args = parser.parse_args()

    if not os.getenv("GROQ_API_KEY"):
        logger.error("GROQ_API_KEY non impostata nel .env")
        sys.exit(1)

    try:
        run_daily_task(topic=args.topic)
    except Exception as e:
        logger.error(f"Errore: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
