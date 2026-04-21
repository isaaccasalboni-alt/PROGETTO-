"""
Instagram Description Agent con Slide Generate in Python
=========================================================

Uso:
  python main.py                          # Esegui una volta subito
  python main.py --topic "mindfulness"    # Con argomento specifico
  python main.py --schedule               # Avvia scheduler giornaliero (09:00)
  python main.py --schedule --time 18:30  # Scheduler a orario custom
"""

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


def run_daily_task(topic: str | None = None) -> dict:
    """Esegue il task giornaliero: genera contenuto Instagram, crea le 3 slide e invia via email."""
    from src.instagram_agent import InstagramAgent
    from src.slide_generator import generate_slides
    from src.notifier import Notifier
    from src.drive_uploader import DriveUploader

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"=== Task giornaliero avviato: {timestamp} ===")

    agent = InstagramAgent()
    notifier = Notifier()
    drive = DriveUploader()

    logger.info("Generazione contenuto Instagram con Claude...")
    content = agent.generate_daily_content(topic=topic)

    logger.info(f"Argomento: {content['topic']}")
    logger.info(f"Slide da generare: {len(content['slide_sections'])}")

    logger.info("Generazione immagini slide (1080x1080 PNG)...")
    slides = generate_slides(content["slide_sections"])
    logger.info(f"Generate {len(slides)} slide")

    result = {
        "timestamp": timestamp,
        "topic": content["topic"],
        "caption": content["caption"],
        "hashtags": content["hashtags"],
        "slide_sections": content["slide_sections"],
    }

    _save_result(result)
    _print_summary(result, slides)

    logger.info("Caricamento su Google Drive...")
    drive_links = drive.upload(content)
    if drive_links:
        result["drive"] = drive_links

    logger.info("Invio notifica email con slide allegate...")
    notifier.send(content, slides)

    return result


def _save_result(result: dict) -> None:
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"post_{date_str}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"Risultato salvato in: {log_file}")


def _print_summary(result: dict, slides: list) -> None:
    print("\n" + "=" * 60)
    print("RIEPILOGO CONTENUTO GENERATO")
    print("=" * 60)
    print(f"Argomento: {result['topic']}")
    print(f"\nCAPTION:\n{result['caption'][:300]}{'...' if len(result['caption']) > 300 else ''}")
    print(f"\nHASHTAG ({len(result['hashtags'])}): {' '.join(result['hashtags'][:10])}...")
    print(f"\nSLIDE GENERATE: {len(slides)}")
    for i, s in enumerate(slides):
        size_kb = len(s["bytes"]) // 1024
        print(f"  • {s['filename']} ({size_kb} KB)")
    print("=" * 60 + "\n")


def _check_env() -> bool:
    if not os.getenv("GROQ_API_KEY"):
        logger.error("GROQ_API_KEY non impostata. Vai su console.groq.com e crea una chiave gratuita.")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Instagram Description Agent con Slide Generate in Python",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Avvia lo scheduler giornaliero invece di eseguire una volta sola",
    )
    parser.add_argument(
        "--time",
        default=None,
        metavar="HH:MM",
        help="Orario di esecuzione giornaliera (default: DAILY_RUN_TIME da .env o 09:00)",
    )
    parser.add_argument(
        "--topic",
        default=None,
        help="Argomento specifico per il post (default: auto-generato)",
    )
    args = parser.parse_args()

    if not _check_env():
        sys.exit(1)

    if args.schedule:
        from src.scheduler import DailyScheduler

        scheduler = DailyScheduler(run_time=args.time)

        def scheduled_job():
            try:
                run_daily_task(topic=args.topic)
            except Exception as e:
                logger.error(f"Errore nel task giornaliero: {e}", exc_info=True)

        logger.info("Esecuzione immediata prima di avviare lo scheduler...")
        scheduled_job()

        scheduler.start(scheduled_job)
    else:
        try:
            run_daily_task(topic=args.topic)
        except Exception as e:
            logger.error(f"Errore: {e}", exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    main()
