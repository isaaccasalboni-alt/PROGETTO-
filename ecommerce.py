#!/usr/bin/env python3
"""Assistente e-commerce interattivo — digita 'aiuto' per i comandi disponibili."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ──── Colori ANSI ─────────────────────────────────────────────────────────────
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

BANNER = f"""
{CYAN}{BOLD}╔══════════════════════════════════════════════════════╗
║         ASSISTENTE E-COMMERCE — powered by Groq      ║
║  Digita 'aiuto' per i comandi · 'esci' per uscire    ║
╚══════════════════════════════════════════════════════╝{RESET}
"""

HELP_TEXT = f"""
{BOLD}Comandi speciali:{RESET}
  {YELLOW}reset{RESET}   — Cancella la cronologia della conversazione
  {YELLOW}aiuto{RESET}   — Mostra questo messaggio
  {YELLOW}esci{RESET}    — Termina il programma

{BOLD}Esempi di richieste:{RESET}
  • "mostrami tutti i prodotti"
  • "aggiungi un prodotto: maglietta rossa, €25, categoria abbigliamento, stock 100"
  • "aggiorna il prezzo della SKU-0001 a 24.99"
  • "crea un ordine per Mario Rossi, mario@email.it, 2x SKU-0001"
  • "quali ordini sono in stato spedito?"
  • "genera una descrizione per le mie sneakers"
  • "dammi il report delle vendite"
  • "ho esaurito lo stock delle felpe, aggiorna a 0"
"""


def print_banner() -> None:
    print(BANNER)


def print_help() -> None:
    print(HELP_TEXT)


def main() -> None:
    print_banner()

    if not os.getenv("GROQ_API_KEY"):
        print(f"{RED}Errore: GROQ_API_KEY non impostata.{RESET}")
        print(f"Copia .env.example in .env e inserisci la tua chiave Groq.")
        sys.exit(1)

    from src.ecommerce_agent import EcommerceAgent, SHOP_NAME

    agent = EcommerceAgent()
    shop = os.getenv("SHOP_NAME", SHOP_NAME)

    print(f"{GREEN}Negozio: {BOLD}{shop}{RESET}")
    print(f"File dati: {Path('data').resolve()}\n")

    welcome = agent.chat("Benvenuto! Presentati brevemente e dimmi cosa puoi fare per me oggi.")
    print(f"{CYAN}{BOLD}Assistente:{RESET} {welcome}\n")

    while True:
        try:
            user_input = input(f"{BOLD}Tu:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Arrivederci!{RESET}")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("esci", "exit", "quit", "q"):
            print(f"{YELLOW}Arrivederci!{RESET}")
            break

        if cmd in ("reset",):
            agent.reset()
            print(f"{YELLOW}Conversazione resettata.{RESET}\n")
            continue

        if cmd in ("aiuto", "help", "?"):
            print_help()
            continue

        try:
            response = agent.chat(user_input)
            print(f"\n{CYAN}{BOLD}Assistente:{RESET} {response}\n")
        except RuntimeError as e:
            print(f"\n{RED}Errore API: {e}{RESET}\n")
        except Exception as e:
            print(f"\n{RED}Errore: {e}{RESET}\n")


if __name__ == "__main__":
    main()
