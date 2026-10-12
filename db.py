"""Base SQLite (offers.db) : stockage, dédoublonnage et suivi des candidatures."""
import sqlite3
from datetime import datetime, timezone

from models import Offer

STATUSES = ("new", "applied", "rejected", "interview")

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source        TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    dedup_key     TEXT NOT NULL,
    kind          TEXT NOT NULL DEFAULT 'offre',
    title         TEXT NOT NULL,
    company       TEXT,
    location      TEXT,
    contract_type TEXT,
    url           TEXT,
    date_found    TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'new'
                  CHECK (status IN ('new', 'applied', 'rejected', 'interview')),
    notes         TEXT NOT NULL DEFAULT '',
    notified      INTEGER NOT NULL DEFAULT 0,   -- 1 = déjà envoyée par email
    UNIQUE (source, source_id),                 -- même offre, même source
    UNIQUE (dedup_key)                          -- même offre, autre source
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def add_if_new(conn: sqlite3.Connection, offer: Offer) -> bool:
    """Ajoute l'offre si elle est inconnue. Renvoie True si elle est nouvelle.

    Le dédoublonnage est fait par la base elle-même (contraintes UNIQUE) :
    si l'offre existe déjà (même source+id, ou même clé titre+entreprise),
    l'insertion échoue et on ne touche à rien -> ton statut et tes notes
    ne sont jamais écrasés.
    """
    try:
        with conn:
            conn.execute(
                """INSERT INTO offers
                   (source, source_id, dedup_key, kind, title, company, location,
                    contract_type, url, date_found)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    offer.source,
                    offer.source_id or offer.dedup_key,
                    offer.dedup_key,
                    offer.kind,
                    offer.title,
                    offer.company,
                    offer.location,
                    offer.contract_type,
                    offer.url,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def pending_notification(conn: sqlite3.Connection, kind: str) -> list[sqlite3.Row]:
    """Offres pas encore envoyées par email (donc les nouvelles de ce run,
    plus celles d'un run précédent dont l'email avait échoué)."""
    return conn.execute(
        "SELECT * FROM offers WHERE notified = 0 AND kind = ? ORDER BY id", (kind,)
    ).fetchall()


def mark_notified(conn: sqlite3.Connection, kind: str) -> None:
    with conn:
        conn.execute("UPDATE offers SET notified = 1 WHERE notified = 0 AND kind = ?", (kind,))


def list_offers(conn, status: str | None = None, kind: str | None = None) -> list[sqlite3.Row]:
    query, params = "SELECT * FROM offers WHERE 1=1", []
    if status:
        query += " AND status = ?"
        params.append(status)
    if kind:
        query += " AND kind = ?"
        params.append(kind)
    return conn.execute(query + " ORDER BY id DESC", params).fetchall()


def get_offer(conn, offer_id: int):
    return conn.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)).fetchone()


def set_status(conn, offer_id: int, status: str) -> bool:
    if status not in STATUSES:
        raise ValueError(f"Statut inconnu : {status} (choix : {', '.join(STATUSES)})")
    with conn:
        cur = conn.execute("UPDATE offers SET status = ? WHERE id = ?", (status, offer_id))
    return cur.rowcount > 0


def set_note(conn, offer_id: int, note: str) -> bool:
    with conn:
        cur = conn.execute("UPDATE offers SET notes = ? WHERE id = ?", (note, offer_id))
    return cur.rowcount > 0
