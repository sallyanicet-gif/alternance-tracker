"""Filtrage des offres : mots-clés, type de contrat, lieu (Guadeloupe).

Tout est normalisé (minuscules, sans accents, sans ponctuation) pour que
"Développeur front-end" et "developpeur FRONT END" soient considérés égaux.
"""
import re
import unicodedata


def normalize(text: str) -> str:
    """Minuscules + suppression des accents + ponctuation remplacée par des espaces."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return text.strip()


def matching_keywords(text: str, keywords: list[str]) -> list[str]:
    """Renvoie la liste des mots-clés trouvés dans `text`.

    On compare des MOTS ENTIERS (on entoure de espaces), pour que "PAO"
    ne soit pas trouvé dans "paonne" ou "capaouet".
    """
    haystack = f" {normalize(text)} "
    found = []
    for kw in keywords:
        needle = normalize(kw)
        if needle and f" {needle} " in haystack:
            found.append(kw)
    return found


def offer_matches(offer, keywords: list[str], search_in: str = "title_and_description") -> bool:
    """Vrai si l'offre contient au moins un mot-clé (dans le titre, ou titre + description)."""
    text = offer.title
    if search_in == "title_and_description":
        text = f"{offer.title} {offer.description}"
    return bool(matching_keywords(text, keywords))


_POSTAL_CODE = re.compile(r"\b(\d{5})\b")


def is_in_guadeloupe(location: str, prefix: str = "971") -> bool:
    """Vrai si le lieu semble être en Guadeloupe.

    - Si on trouve un code postal (5 chiffres) : il doit commencer par `prefix`.
    - Si on n'en trouve aucun : on garde l'offre (dans le doute, mieux vaut la voir).
    """
    codes = _POSTAL_CODE.findall(location or "")
    if not codes:
        return True
    return any(code.startswith(prefix) for code in codes)


def is_accepted_contract(contract_type: str, accepted: list[str]) -> bool:
    """Vrai si le libellé du contrat contient un des types acceptés.

    Si le contrat n'est pas renseigné, on garde l'offre (les deux API ne
    renvoient déjà que de l'alternance quand elles sont bien configurées).
    """
    text = normalize(contract_type)
    if not text:
        return True
    return any(normalize(a) in text for a in accepted)
