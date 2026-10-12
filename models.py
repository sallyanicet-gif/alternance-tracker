"""Modèle de données commun aux deux sources."""
from dataclasses import dataclass

from filters import normalize


@dataclass
class Offer:
    source: str              # "lba" ou "francetravail"
    source_id: str           # identifiant chez la source
    title: str
    company: str = ""
    location: str = ""
    contract_type: str = ""
    url: str = ""
    description: str = ""    # utilisée pour filtrer, pas stockée en base
    kind: str = "offre"      # "offre" ou "spontanee" (entreprise sans offre publiée)

    @property
    def dedup_key(self) -> str:
        """Clé qui identifie « la même offre » d'une source à l'autre.

        Deux offres avec le même titre ET la même entreprise (après
        normalisation) sont considérées comme un doublon, même si elles
        viennent de sources différentes.
        Limite connue : une entreprise qui publie le même intitulé dans deux
        communes différentes n'apparaîtra qu'une fois.
        """
        company = normalize(self.company)
        if self.kind == "spontanee":
            return f"spont|{company}"
        return f"{normalize(self.title)}|{company}"
