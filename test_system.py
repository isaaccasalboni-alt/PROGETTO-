"""
Test del sistema completo Instagram Agent.
Genera contenuto + slide PNG e le salva in locale (senza inviare email).

Uso:
  python test_system.py
  python test_system.py --topic "finanza personale"
  python test_system.py --send-email    # invia anche l'email (richiede RESEND_API_KEY)
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Test del sistema Instagram Agent")
    parser.add_argument("--topic", default=None, help="Argomento specifico")
    parser.add_argument("--send-email", action="store_true", help="Invia anche l'email")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "").startswith("metti_"):
        print("❌ ANTHROPIC_API_KEY non configurata nel .env")
        sys.exit(1)

    print("=" * 60)
    print("TEST SISTEMA INSTAGRAM AGENT")
    print("=" * 60)

    # Step 1: Genera contenuto
    print("\n[1/3] Generazione contenuto con Claude...")
    from src.instagram_agent import InstagramAgent
    agent = InstagramAgent()
    content = agent.generate_daily_content(topic=args.topic)

    print(f"\n✅ Argomento: {content['topic']}")
    print(f"✅ Caption: {len(content['caption'])} caratteri")
    print(f"✅ Hashtag: {len(content['hashtags'])}")
    print(f"✅ Slide sections: {len(content['slide_sections'])}")

    # Step 2: Genera slide PNG
    print("\n[2/3] Generazione slide PNG (1080x1080)...")
    from src.slide_generator import generate_slides
    slides = generate_slides(content["slide_sections"])

    output_dir = Path("output_test")
    output_dir.mkdir(exist_ok=True)

    for slide in slides:
        path = output_dir / slide["filename"]
        path.write_bytes(slide["bytes"])
        size_kb = len(slide["bytes"]) // 1024
        print(f"  ✅ {slide['filename']} ({size_kb} KB) → salvato in {path}")

    # Step 3: Email (opzionale)
    if args.send_email:
        print("\n[3/3] Invio email con Resend...")
        from src.notifier import Notifier
        notifier = Notifier()
        notifier.send(content, slides)
    else:
        print("\n[3/3] Email saltata (usa --send-email per inviarla)")

    print("\n" + "=" * 60)
    print("TEST COMPLETATO")
    print("=" * 60)
    print(f"Le slide sono in: {output_dir.resolve()}/")
    print(f"\nPRIMA SLIDE — {content['slide_sections'][0]['title']}")
    print(f"CAPTION (prime 200 char):\n{content['caption'][:200]}...")
    print(f"\nHASHTAG: {' '.join(content['hashtags'][:5])} ...")


if __name__ == "__main__":
    main()
