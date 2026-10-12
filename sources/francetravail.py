"""Source 2 : France Travail, API « Offres d'emploi v2 » (francetravail.io).

Authentification OAuth2 « client credentials » :
FT_CLIENT_ID + FT_CLIENT_SECRET -> jeton -> appels de l'API.

Source FACULTATIVE : sans identifiants elle est ignorée ; si l'accès est refusé
(l'API a connu des restrictions d'accès), le run continue avec les autres sources.
"""
import logging
import os
import re
import time

import requests

from filters import normalize
from models import Offer
from sources.base import TIMEOUT, SourceError, SourceSkipped, dig, make_session, text_of

log = logging.getLogger(__name__)

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
API_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2"
SCOPE = "api_offresdemploiv2 o2dsoffre"
PAGE_SIZE = 150  # maximum autorisé par l'API


def get_token(session, client_id: str, client_secret: str) -> str:
    resp = session.post(
        TOKEN_URL,
        params={"realm": "/partenaire"},
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": SCOPE,
        },
        timeout=TIMEOUT,
    )
    if resp.status_code in (400, 401, 403):
        raise SourceError(
            "France Travail a refusé les identifiants (FT_CLIENT_ID / FT_CLIENT_SECRET) "
            "ou l'API n'est pas activée pour ton application. Voir le README."
        )
    resp.raise_for_status()
    return resp.json()["access_token"]


def find_nature_codes(session, headers: dict, wanted: list[str]) -> list[str]:
    """Cherche dans le référentiel de l'API les codes des natures de contrat voulues
    (ex. « Contrat apprentissage », « Contrat professionnalisation »)."""
    resp = session.get(f"{API_URL}/referentiel/naturesContrats", headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    codes = []
    for item in resp.json():
        label = normalize(item.get("libelle", ""))
        if any(normalize(w) in label for w in wanted):
            codes.append(item["code"])
    return codes


def parse_offer(raw: dict) -> Offer:
    offer_id = str(raw.get("id", ""))
    # lieuTravail.libelle ressemble à "971 - LES ABYMES"
    place = re.sub(r"^\d+\s*-\s*", "", text_of(dig(raw, "lieuTravail", "libelle")))
    postal = text_of(dig(raw, "lieuTravail", "codePostal"))
    contract = " ".join(
        filter(None, [text_of(raw.get("natureContrat")), text_of(raw.get("typeContratLibelle"))])
    )
    return Offer(
        source="francetravail",
        source_id=offer_id,
        title=text_of(raw.get("intitule")),
        company=text_of(dig(raw, "entreprise", "nom")),
        location=f"{place} ({postal})" if postal else place,
        contract_type=contract,
        url=text_of(dig(raw, "origineOffre", "urlOrigine"))
        or f"https://candidat.francetravail.fr/offres/recherche/detail/{offer_id}",
        description=text_of(raw.get("description")),
        kind="offre",
    )


def _search_all(session, headers: dict, params: dict, max_results: int) -> list[dict]:
    """Parcourt toutes les pages de résultats (150 offres par page)."""
    results, start = [], 0
    while start < max_results:
        page_params = dict(params, range=f"{start}-{start + PAGE_SIZE - 1}")
        resp = session.get(f"{API_URL}/offres/search", headers=headers,
                           params=page_params, timeout=TIMEOUT)
        if resp.status_code == 204:        # aucun résultat
            break
        if resp.status_code in (401, 403):
            raise SourceError("France Travail : accès refusé à l'API Offres d'emploi (voir README).")
        resp.raise_for_status()
        results += resp.json().get("resultats", [])

        # En-tête du type "Content-Range: offres 0-149/1234"
        match = re.search(r"-(\d+)/(\d+)", resp.headers.get("Content-Range", ""))
        if not match or int(match.group(1)) + 1 >= int(match.group(2)):
            break
        start = int(match.group(1)) + 1
        time.sleep(0.15)  # l'API limite à 10 requêtes/seconde
    return results


def fetch(config: dict) -> list[Offer]:
    client_id = os.environ.get("FT_CLIENT_ID")
    client_secret = os.environ.get("FT_CLIENT_SECRET")
    if not (client_id and client_secret):
        raise SourceSkipped("France Travail : identifiants absents, source ignorée.")

    ft_cfg = config["france_travail"]
    session = make_session()
    try:
        token = get_token(session, client_id, client_secret)
        headers = {"Authorization": f"Bearer {token}"}

        # Codes de contrat : saisis dans config.yaml, sinon cherchés dans le référentiel.
        codes = list(ft_cfg.get("nature_contrat_codes") or [])
        if not codes:
            try:
                codes = find_nature_codes(session, headers, config["contract_types"])
            except (requests.RequestException, ValueError, KeyError) as err:
                log.warning("France Travail : codes de contrat introuvables (%s). "
                            "Recherche sans ce filtre, tri fait ensuite localement.", err)

        params = {"departement": ft_cfg["departement"]}
        if codes:
            params["natureContrat"] = ",".join(codes)
        log.info("France Travail : recherche département %s, natureContrat=%s",
                 params["departement"], params.get("natureContrat", "(aucun)"))

        raw_offers = _search_all(session, headers, params, ft_cfg.get("max_results", 1000))
    except requests.RequestException as err:
        raise SourceError(f"France Travail : erreur réseau/API : {err}") from err

    if raw_offers:
        log.debug("Exemple d'offre brute : %s", raw_offers[0])
    log.info("France Travail : %d résultats bruts", len(raw_offers))
    return [parse_offer(r) for r in raw_offers]
