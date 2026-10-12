"""Outils communs aux sources (erreurs, session HTTP avec nouvelles tentatives)."""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TIMEOUT = 30  # secondes


class SourceError(Exception):
    """La source a échoué (clé refusée, API en panne...). Le run continue avec les autres."""


class SourceSkipped(Exception):
    """Source facultative non configurée (pas d'identifiants) : on l'ignore sans bruit."""


def make_session() -> requests.Session:
    """Session HTTP qui réessaie automatiquement en cas d'erreur temporaire (429, 5xx)."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = "alternance-tracker (projet personnel d'etudiant)"
    return session


def text_of(value) -> str:
    """Convertit une valeur d'API (texte, liste ou dict) en texte simple."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(str(v) for v in value.values() if v)
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value if v)
    return str(value)


def dig(data, *path, default=""):
    """Lit data[a][b][c] sans planter si une clé manque."""
    for key in path:
        if not isinstance(data, dict):
            return default
        data = data.get(key)
        if data is None:
            return default
    return data
