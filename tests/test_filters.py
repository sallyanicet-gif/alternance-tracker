from filters import (is_accepted_contract, is_in_guadeloupe, matching_keywords,
                     normalize, offer_matches)
from models import Offer

KEYWORDS = ["graphiste", "PAO", "monteur vidéo", "développeur front-end", "multimédia"]


def test_normalize_removes_accents_case_and_punctuation():
    assert normalize("Développeur FRONT-END !") == "developpeur front end"


def test_keyword_ignores_accents_and_case():
    assert matching_keywords("Alternance MONTEUR VIDEO H/F", KEYWORDS) == ["monteur vidéo"]


def test_keyword_hyphen_variant():
    assert matching_keywords("Développeur front end en alternance", KEYWORDS) == ["développeur front-end"]


def test_short_keyword_matches_whole_word_only():
    assert matching_keywords("Opérateur PAO", KEYWORDS) == ["PAO"]
    assert matching_keywords("Éleveur de paons", KEYWORDS) == []
    assert matching_keywords("Technicien capaouet", KEYWORDS) == []


def test_no_keyword_no_match():
    assert matching_keywords("Boulanger en alternance", KEYWORDS) == []


def test_offer_matches_title_only_vs_description():
    offer = Offer("lba", "1", "Assistant polyvalent", description="Création de contenus multimédia")
    assert offer_matches(offer, KEYWORDS, "title_and_description")
    assert not offer_matches(offer, KEYWORDS, "title")


def test_guadeloupe_postal_code():
    assert is_in_guadeloupe("12 rue X 97110 POINTE-A-PITRE")
    assert not is_in_guadeloupe("5 avenue Y 97200 FORT-DE-FRANCE")  # Martinique
    assert not is_in_guadeloupe("75001 Paris")


def test_guadeloupe_unknown_location_is_kept():
    assert is_in_guadeloupe("")
    assert is_in_guadeloupe("LES ABYMES")


def test_contract_types():
    accepted = ["apprentissage", "professionnalisation"]
    assert is_accepted_contract("Contrat apprentissage", accepted)
    assert is_accepted_contract("Contrat de professionnalisation", accepted)
    assert is_accepted_contract("", accepted)  # non renseigné : on garde
    assert not is_accepted_contract("CDI", accepted)
