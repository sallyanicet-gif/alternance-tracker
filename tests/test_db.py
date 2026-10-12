import pytest

import db
from models import Offer


@pytest.fixture
def conn(tmp_path):
    return db.connect(str(tmp_path / "test.db"))


def offer(**kw):
    base = dict(source="lba", source_id="1", title="Graphiste H/F", company="Studio Kréol")
    return Offer(**{**base, **kw})


def test_new_offer_is_added_once(conn):
    assert db.add_if_new(conn, offer()) is True
    assert db.add_if_new(conn, offer()) is False          # même run ou run suivant
    assert len(db.list_offers(conn)) == 1


def test_same_offer_from_other_source_is_duplicate(conn):
    db.add_if_new(conn, offer(source="lba", source_id="abc"))
    # Même titre/entreprise (casse, accents, ponctuation différents) chez France Travail
    other = offer(source="francetravail", source_id="999", title="GRAPHISTE (H/F)", company="studio kreol")
    assert db.add_if_new(conn, other) is False


def test_different_company_is_not_duplicate(conn):
    db.add_if_new(conn, offer())
    assert db.add_if_new(conn, offer(source_id="2", company="Autre Agence")) is True


def test_same_source_id_is_duplicate_even_if_title_changed(conn):
    db.add_if_new(conn, offer())
    assert db.add_if_new(conn, offer(title="Graphiste senior")) is False


def test_rerun_keeps_status_and_notes(conn):
    db.add_if_new(conn, offer())
    row = db.list_offers(conn)[0]
    db.set_status(conn, row["id"], "applied")
    db.set_note(conn, row["id"], "CV envoyé")
    db.add_if_new(conn, offer())                          # re-découverte de la même offre
    row = db.get_offer(conn, row["id"])
    assert row["status"] == "applied" and row["notes"] == "CV envoyé"


def test_default_status_is_new(conn):
    db.add_if_new(conn, offer())
    assert db.list_offers(conn, status="new")[0]["status"] == "new"


def test_invalid_status_rejected(conn):
    db.add_if_new(conn, offer())
    with pytest.raises(ValueError):
        db.set_status(conn, 1, "ghosted")


def test_spontaneous_companies_dedup_by_company(conn):
    a = offer(source_id="recruteur-1", title="Candidature spontanée : X", kind="spontanee")
    b = offer(source_id="recruteur-2", title="Candidature spontanée : X", kind="spontanee")
    assert db.add_if_new(conn, a) is True
    assert db.add_if_new(conn, b) is False


def test_spontaneous_does_not_collide_with_offer(conn):
    db.add_if_new(conn, offer(title="Studio Kréol", company="Studio Kréol"))
    spont = offer(source_id="recruteur-1", kind="spontanee")
    assert db.add_if_new(conn, spont) is True


def test_notification_flag(conn):
    db.add_if_new(conn, offer())
    assert len(db.pending_notification(conn, "offre")) == 1
    db.mark_notified(conn, "offre")
    assert db.pending_notification(conn, "offre") == []
