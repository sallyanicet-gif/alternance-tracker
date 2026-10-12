"""Petit outil en ligne de commande pour suivre tes candidatures.

  python cli.py list --status new
  python cli.py list --kind spontanee
  python cli.py show 12
  python cli.py status 12 applied        (new | applied | rejected | interview)
  python cli.py note 12 "Envoyé CV + lettre le 15/10, relancer le 25"
"""
import argparse
import os
import sys

import db


def short(text, width):
    text = (text or "—").replace("\n", " ")
    return text if len(text) <= width else text[: width - 1] + "…"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Suivi des offres d'alternance")
    parser.add_argument("--db", default=os.environ.get("OFFERS_DB", "offers.db"))
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="lister les offres")
    p.add_argument("--status", choices=db.STATUSES)
    p.add_argument("--kind", choices=("offre", "spontanee"))

    p = sub.add_parser("show", help="afficher le détail d'une offre")
    p.add_argument("id", type=int)

    p = sub.add_parser("status", help="changer le statut d'une offre")
    p.add_argument("id", type=int)
    p.add_argument("status", choices=db.STATUSES)

    p = sub.add_parser("note", help="écrire une note sur une offre")
    p.add_argument("id", type=int)
    p.add_argument("text")

    args = parser.parse_args(argv)
    conn = db.connect(args.db)

    if args.command == "list":
        rows = db.list_offers(conn, args.status, args.kind)
        if not rows:
            print("Aucune offre.")
        for r in rows:
            print(f"{r['id']:>4}  {r['status']:<9} {short(r['title'], 45):<45} "
                  f"{short(r['company'], 25):<25} {short(r['location'], 22):<22} {r['date_found'][:10]}")
        return 0

    row = db.get_offer(conn, args.id)
    if row is None:
        print(f"Offre {args.id} introuvable.", file=sys.stderr)
        return 1

    if args.command == "show":
        for key in ("id", "kind", "source", "title", "company", "location",
                    "contract_type", "url", "date_found", "status", "notes"):
            print(f"{key:<14}: {row[key]}")
    elif args.command == "status":
        db.set_status(conn, args.id, args.status)
        print(f"Offre {args.id} : statut -> {args.status}")
    elif args.command == "note":
        db.set_note(conn, args.id, args.text)
        print(f"Offre {args.id} : note enregistrée.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
