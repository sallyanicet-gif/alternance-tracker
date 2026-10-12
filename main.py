"""Point d'entrée : récupère les offres, filtre, enregistre, envoie l'email.

Usage :  python main.py [--config config.yaml] [--db offers.db] [--no-email] [--verbose]
"""
import argparse
import logging
import os
import sys

import yaml

import db
import emailer
import filters
from sources import francetravail, lba
from sources.base import SourceSkipped

try:  # .env facultatif, pratique en local (ignoré sur GitHub Actions)
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

log = logging.getLogger("main")

# (nom affiché, clé dans config.yaml, fonction fetch)
DEFAULT_SOURCES = [
    ("La Bonne Alternance", "lba", lba.fetch),
    ("France Travail", "france_travail", francetravail.fetch),
]


def keep_offer(offer, config: dict) -> bool:
    """Applique les filtres de config.yaml à une offre."""
    if not filters.is_in_guadeloupe(offer.location, config["guadeloupe"]["postal_prefix"]):
        return False
    if offer.kind == "spontanee":
        return True  # pas de titre à filtrer : l'API les a déjà choisies par métier (ROME)
    if not filters.is_accepted_contract(offer.contract_type, config["contract_types"]):
        return False
    return filters.offer_matches(offer, config["keywords"], config.get("search_in", "title_and_description"))


def run(config: dict, db_path: str, sources=None, send=None, send_email=True) -> int:
    """Un run complet. Renvoie le code de sortie (0 = ok, 1 = toutes les sources ont échoué)."""
    sources = DEFAULT_SOURCES if sources is None else sources
    send = emailer.send_email if send is None else send

    warnings, attempted, succeeded = [], 0, 0
    fetched = []

    # 1) Récupération : chaque source est isolée, une panne n'arrête pas les autres.
    for name, config_key, fetch in sources:
        if not config.get(config_key, {}).get("enabled", True):
            continue
        try:
            fetched += fetch(config)
            attempted += 1
            succeeded += 1
        except SourceSkipped as info:
            log.info("%s", info)
        except Exception as err:  # noqa: BLE001 - on veut vraiment tout attraper ici
            attempted += 1
            log.error("%s a échoué : %s", name, err)
            log.debug("Détail de l'erreur", exc_info=True)
            warnings.append(f"{name} n'a pas pu être interrogée : {err}")

    # 2) Filtrage puis enregistrement (le dédoublonnage est fait par la base).
    kept = [o for o in fetched if keep_offer(o, config)]
    conn = db.connect(db_path)
    created = sum(db.add_if_new(conn, o) for o in kept)
    log.info("%d offres récupérées, %d gardées après filtres, %d nouvelles en base.",
             len(fetched), len(kept), created)

    # 3) Email : toutes les entrées pas encore notifiées (réessaie si l'envoi a échoué avant).
    offers = db.pending_notification(conn, "offre")
    spont = db.pending_notification(conn, "spontanee")
    if offers or spont:
        subject, text, html_body = emailer.build_digest(
            offers, spont, len(spont), warnings, config["lba"].get("max_recruteurs_in_email", 15))
        if not send_email:
            print(text)
        elif send(subject, text, html_body):
            db.mark_notified(conn, "offre")
            db.mark_notified(conn, "spontanee")
    else:
        log.info("Rien de nouveau : pas d'email.")
    conn.close()

    if attempted and succeeded == 0:
        log.error("Toutes les sources ont échoué.")
        return 1
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Suivi d'offres d'alternance en Guadeloupe")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--db", default=os.environ.get("OFFERS_DB", "offers.db"))
    parser.add_argument("--no-email", action="store_true", help="affiche le récap au lieu de l'envoyer")
    parser.add_argument("--verbose", action="store_true", help="journal détaillé (débogage)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return run(config, args.db, send_email=not args.no_email)


if __name__ == "__main__":
    sys.exit(main())
