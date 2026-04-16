"""
Instagram Description Agent con Gamma Slides
============================================

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
    """Esegue il task giornaliero: genera contenuto Instagram e crea deck Gamma."""
    from src.instagram_agent import InstagramAgent
    from src.gamma_client import GammaClient
    from src.notifier import Notifier
    from src.drive_uploader import DriveUploader

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"=== Task giornaliero avviato: {timestamp} ===")

    agent = InstagramAgent()
    gamma = GammaClient()
    notifier = Notifier()
    drive = DriveUploader()

    logger.info("Generazione contenuto Instagram con Claude...")
    content = agent.generate_daily_content(topic=topic)

    logger.info(f"Argomento: {content['topic']}")
    logger.info(f"Slide da creare: {len(content['slide_sections'])}")

    deck_title = f"{content['topic'].title()} — {datetime.now().strftime('%d/%m/%Y')}"
    logger.info(f"Creazione deck Gamma: '{deck_title}'")
    deck_info = gamma.create_deck(
        title=deck_title,
        slide_sections=content["slide_sections"],
    )

    result = {
        "timestamp": timestamp,
        "topic": content["topic"],
        "caption": content["caption"],
        "hashtags": content["hashtags"],
        "slide_sections": content["slide_sections"],
        "deck": deck_info,
    }

    _save_result(result)
    _print_summary(result)

    logger.info("Caricamento su Google Drive...")
    drive_links = drive.upload(content, deck_info)
    if drive_links:
        result["drive"] = drive_links

    logger.info("Invio notifica...")
    notifier.send(content, deck_info)

    return result


def _save_result(result: dict) -> None:
    """Salva il risultato in un file JSON nella cartella logs/."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"post_{date_str}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"Risultato salvato in: {log_file}")


def _print_summary(result: dict) -> None:
    print("\n" + "=" * 60)
    print("RIEPILOGO CONTENUTO GENERATO")
    print("=" * 60)
    print(f"Argomento: {result['topic']}")
    print(f"\nCAPTION:\n{result['caption'][:300]}{'...' if len(result['caption']) > 300 else ''}")
    print(f"\nHASHTAG ({len(result['hashtags'])}): {' '.join(result['hashtags'][:10])}...")
    print(f"\nDECK GAMMA:")
    print(f"  URL: {result['deck']['deck_url']}")
    print(f"  Slide: {len(result['slide_sections'])}")
    print("=" * 60 + "\n")


def _check_env() -> bool:
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY non impostata. Copia .env.example in .env e configura le chiavi.")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Instagram Description Agent con Gamma Slides",
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

        # Prima esecuzione immediata, poi schedule
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
