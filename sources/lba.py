"""Source 1 : La Bonne Alternance (API Apprentissage, api.apprentissage.beta.gouv.fr).

Authentification : clé API dans la variable d'environnement LBA_API_KEY,
envoyée en "Authorization: Bearer <clé>".

⚠ Ce fichier a été écrit d'après la documentation publique, mais les noms
exacts des paramètres / champs n'ont pas pu être testés en direct. Si un run
échoue, lance `python main.py --verbose` et compare avec la documentation
technique : https://api.apprentissage.beta.gouv.fr/fr/documentation-technique
Tout ce qui dépend de l'API est regroupé dans SEARCH_URL, _search() et parse_*().
"""
import logging
import os

import requests

from models import Offer
from sources.base import TIMEOUT, SourceError, dig, make_session, text_of

log = logging.getLogger(__name__)

SEARCH_URL = "https://api.apprentissage.beta.gouv.fr/api/job/v1/search"


def parse_job(job: dict) -> Offer:
    """Transforme une offre de l'API en Offer."""
    return Offer(
        source="lba",
        source_id=str(dig(job, "identifier", "id")),
        title=text_of(dig(job, "offer", "title")),
        company=text_of(dig(job, "workplace", "name") or dig(job, "workplace", "brand")),
        location=text_of(dig(job, "workplace", "location", "address")),
        contract_type=text_of(dig(job, "contract", "type")),
        url=text_of(dig(job, "apply", "url")),
        description=text_of(dig(job, "offer", "description")),
        kind="offre",
    )


def parse_recruiter(rec: dict) -> Offer:
    """Transforme une entreprise « à fort potentiel d'embauche » en Offer de type spontanée."""
    company = text_of(dig(rec, "workplace", "name") or dig(rec, "workplace", "brand"))
    return Offer(
        source="lba",
        source_id="recruteur-" + str(dig(rec, "identifier", "id")),
        title=f"Candidature spontanée : {company}",
        company=company,
        location=text_of(dig(rec, "workplace", "location", "address")),
        contract_type="Spontanée",
        url=text_of(dig(rec, "apply", "url")),
        kind="spontanee",
    )


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _search(session, point: dict, radius: int, romes: list[str]) -> dict:
    """Une requête de recherche autour d'un point, pour un groupe de codes ROME."""
    params = {
        "latitude": point["lat"],
        "longitude": point["lon"],
        "radius": radius,
        "romes": ",".join(romes),
    }
    resp = session.get(SEARCH_URL, params=params, timeout=TIMEOUT)
    if resp.status_code in (401, 403):
        raise SourceError("La Bonne Alternance a refusé la clé API (LBA_API_KEY). Vérifie-la.")
    if not resp.ok:
        # On affiche le début de la réponse : elle explique souvent le paramètre fautif.
        raise requests.HTTPError(f"HTTP {resp.status_code} : {resp.text[:300]}")
    return resp.json()


def fetch(config: dict) -> list[Offer]:
    api_key = os.environ.get("LBA_API_KEY")
    if not api_key:
        raise SourceError("Variable d'environnement LBA_API_KEY absente.")

    lba_cfg = config["lba"]
    geo = config["guadeloupe"]
    session = make_session()
    session.headers["Authorization"] = f"Bearer {api_key}"

    offers: list[Offer] = []
    requests_done = requests_failed = 0

    for point in geo["search_points"]:
        for romes in _chunks(lba_cfg["romes"], lba_cfg.get("romes_per_request", 5)):
            requests_done += 1
            try:
                data = _search(session, point, geo["radius_km"], romes)
            except SourceError:
                raise  # clé refusée : inutile de continuer
            except (requests.RequestException, ValueError) as err:
                # Une requête qui échoue ne doit pas bloquer les autres.
                requests_failed += 1
                log.warning("LBA : requête échouée (%s, ROME %s) : %s", point["name"], romes, err)
                continue

            jobs = data.get("jobs") or []
            log.debug("LBA %s %s : %d offres", point["name"], romes, len(jobs))
            if jobs:
                log.debug("Exemple d'offre brute : %s", jobs[0])
            offers += [parse_job(j) for j in jobs]

            if lba_cfg.get("include_recruteurs"):
                offers += [parse_recruiter(r) for r in (data.get("recruiters") or [])]

    if requests_done and requests_failed == requests_done:
        raise SourceError("Toutes les requêtes La Bonne Alternance ont échoué (voir le journal).")
    log.info("LBA : %d résultats bruts (%d/%d requêtes réussies)",
             len(offers), requests_done - requests_failed, requests_done)
    return offers
