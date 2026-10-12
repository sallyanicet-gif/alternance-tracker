"""Test du déroulé complet avec de fausses sources (aucun accès réseau)."""
import yaml

import db
import main
from models import Offer
from sources.base import SourceSkipped

CONFIG = yaml.safe_load("""
keywords: [graphiste, monteur vidéo]
search_in: title
contract_types: [apprentissage, professionnalisation]
guadeloupe: {postal_prefix: "971"}
lba: {enabled: true, max_recruteurs_in_email: 15}
france_travail: {enabled: true}
""")


def lba_ok(config):
    return [
        Offer("lba", "1", "Graphiste", "Studio A", "97110 Pointe-à-Pitre", "Apprentissage", "https://x/1"),
        Offer("lba", "2", "Boulanger", "Fournil", "97110 Pointe-à-Pitre", "Apprentissage"),   # mot-clé absent
        Offer("lba", "3", "Graphiste", "Agence Paris", "75001 Paris", "Apprentissage"),        # hors Guadeloupe
        Offer("lba", "4", "Graphiste", "Studio B", "97122 Baie-Mahault", "CDI"),                # mauvais contrat
        Offer("lba", "recruteur-9", "Candidature spontanée : Web Karukera", "Web Karukera",
              "97100 Basse-Terre", "Spontanée", kind="spontanee"),
    ]


def ft_duplicate(config):
    return [Offer("francetravail", "FT1", "GRAPHISTE", "studio a", "LES ABYMES (97139)", "Contrat apprentissage"),
            Offer("francetravail", "FT2", "Monteur vidéo", "Radio Caraïbes", "BAIE-MAHAULT", "Contrat professionnalisation")]


def boom(config):
    raise RuntimeError("API en panne")


def skipped(config):
    raise SourceSkipped("pas d'identifiants")


def run(tmp_path, sources, sent):
    def fake_send(subject, text, html):
        sent.append((subject, text))
        return True
    return main.run(CONFIG, str(tmp_path / "t.db"), sources=sources, send=fake_send)


def test_filters_dedup_and_email(tmp_path):
    sent = []
    code = run(tmp_path, [("LBA", "lba", lba_ok), ("FT", "france_travail", ft_duplicate)], sent)
    assert code == 0
    assert len(sent) == 1
    text = sent[0][1]
    assert "Studio A" in text and "Radio Caraïbes" in text and "Web Karukera" in text
    assert "Fournil" not in text and "Agence Paris" not in text and "Studio B" not in text
    conn = db.connect(str(tmp_path / "t.db"))
    assert len(db.list_offers(conn)) == 3   # Studio A (une seule fois), Radio Caraïbes, Web Karukera


def test_second_run_sends_nothing(tmp_path):
    sent = []
    sources = [("LBA", "lba", lba_ok), ("FT", "france_travail", ft_duplicate)]
    run(tmp_path, sources, sent)
    run(tmp_path, sources, sent)
    assert len(sent) == 1


def test_failing_source_does_not_stop_the_run(tmp_path):
    sent = []
    code = run(tmp_path, [("LBA", "lba", boom), ("FT", "france_travail", ft_duplicate)], sent)
    assert code == 0                                  # une source a marché
    assert "Radio Caraïbes" in sent[0][1]
    assert "LBA n'a pas pu être interrogée" in sent[0][1]   # l'email le signale


def test_all_sources_failing_gives_error_code(tmp_path):
    sent = []
    assert run(tmp_path, [("LBA", "lba", boom), ("FT", "france_travail", boom)], sent) == 1
    assert sent == []


def test_skipped_optional_source_is_not_an_error(tmp_path):
    sent = []
    assert run(tmp_path, [("LBA", "lba", lba_ok), ("FT", "france_travail", skipped)], sent) == 0


def test_failed_email_is_retried_next_run(tmp_path):
    sources = [("LBA", "lba", lba_ok)]
    main.run(CONFIG, str(tmp_path / "t.db"), sources=sources, send=lambda *a: False)   # envoi KO
    sent = []
    run(tmp_path, sources, sent)                                                         # envoi OK
    assert len(sent) == 1 and "Studio A" in sent[0][1]
