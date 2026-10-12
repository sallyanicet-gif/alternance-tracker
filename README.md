# Suivi d'offres d'alternance en Guadeloupe

Programme Python qui, chaque jour :

1. interroge **La Bonne Alternance** et **France Travail** (contrats d'apprentissage et de professionnalisation, Guadeloupe) ;
2. garde uniquement les offres qui correspondent à tes mots-clés (`config.yaml`) ;
3. évite les doublons (entre les deux sources et entre deux jours) grâce à une base SQLite `offers.db` ;
4. t'envoie **un email avec uniquement les nouvelles offres** ;
5. te laisse suivre tes candidatures (`new`, `applied`, `interview`, `rejected`) avec un petit outil en ligne de commande.

Aucun scraping de LinkedIn ou d'Indeed : seulement des API officielles.

---

## 1. Comptes et identifiants à créer

Tu as besoin de 4 choses. **Aucun de ces secrets ne doit jamais être écrit dans un fichier du dépôt** : ils vont dans les *GitHub Secrets* (et dans un fichier `.env` en local, ignoré par git).

| Secret | À quoi il sert | Où l'obtenir |
|---|---|---|
| `LBA_API_KEY` | Clé de l'API La Bonne Alternance | https://api.apprentissage.beta.gouv.fr |
| `FT_CLIENT_ID` + `FT_CLIENT_SECRET` | Identifiants de l'API France Travail (facultatif) | https://francetravail.io |
| `SMTP_USER` | Ton adresse Gmail (expéditeur) | ton compte Gmail |
| `SMTP_PASSWORD` | **Mot de passe d'application** Gmail (≠ ton mot de passe normal) | https://myaccount.google.com/apppasswords |
| `EMAIL_TO` | Adresse qui reçoit l'email (peut être la même) | — |

### a) La Bonne Alternance (obligatoire)
1. Va sur https://api.apprentissage.beta.gouv.fr et crée un compte (ou connecte-toi).
2. Dans ton espace, génère une **clé API** et copie-la : c'est `LBA_API_KEY`.
3. L'usage est gratuit pour un projet non lucratif comme celui-ci.

### b) France Travail « Offres d'emploi » (facultatif)
1. Crée un compte sur https://francetravail.io (espace développeur).
2. Crée une **application**, puis associe-lui l'API **« Offres d'emploi »**.
3. Récupère l'**identifiant client** (`FT_CLIENT_ID`) et la **clé secrète** (`FT_CLIENT_SECRET`).
4. ⚠ L'accès à cette API a connu des restrictions. Si l'inscription est refusée ou si les identifiants sont rejetés, **le programme continue avec La Bonne Alternance seule** (un avertissement apparaît dans l'email). Tu peux alors demander l'accès via le formulaire de contact de francetravail.io.

### c) Gmail : mot de passe d'application
1. Active la **validation en deux étapes** sur ton compte Google (obligatoire).
2. Va sur https://myaccount.google.com/apppasswords, crée un mot de passe d'application (nom : « alternance »).
3. Google affiche 16 caractères : c'est `SMTP_PASSWORD` (les espaces sont ignorés).
4. `SMTP_USER` = ton adresse Gmail. Par défaut le programme utilise `smtp.gmail.com`, port 587 : rien d'autre à régler.

---

## 2. Installation sur GitHub (le programme tourne tout seul)

1. Crée un dépôt GitHub **privé** (important : la base contient tes candidatures et tes notes) et envoie-y le contenu de ce dossier.
2. Va dans **Settings → Secrets and variables → Actions → New repository secret** et ajoute :
   `LBA_API_KEY`, `FT_CLIENT_ID`, `FT_CLIENT_SECRET`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO`.
3. Va dans l'onglet **Actions**, ouvre « Recherche quotidienne d'alternances » et clique **Run workflow** pour un premier essai.
4. Ensuite il se lance tout seul chaque jour à 7h (heure de Guadeloupe).

**Où est la base ?** Sur une branche séparée nommée `data` (fichier `offers.db`), mise à jour automatiquement après chaque run. La branche principale ne contient que le code.

Si GitHub désactive le workflow planifié après une longue inactivité, réactive-le dans l'onglet Actions.

### Le premier run
Le premier email peut être long (toutes les offres actuelles sont « nouvelles »). Les jours suivants, tu ne reçois que les nouveautés. Si rien de nouveau : pas d'email.

---

## 3. Suivre tes candidatures

Chaque offre a un **numéro (id)**, visible avec le CLI.

### Depuis GitHub (recommandé : la base reste au même endroit)
Onglet **Actions → « Mettre à jour le statut d'une offre » → Run workflow**, puis renseigne l'id, le statut et une note éventuelle. Ça marche aussi depuis l'appli mobile GitHub.

### En local (pour consulter)
```bash
git fetch origin data
git show origin/data:offers.db > offers.db      # télécharge la base

python cli.py list --status new                  # offres pas encore traitées
python cli.py list --kind spontanee              # entreprises pour candidatures spontanées
python cli.py show 12                            # détail d'une offre
```
⚠ Les commandes `python cli.py status ...` et `note ...` modifient **ta copie locale** seulement : elle sera écrasée par la version GitHub. Pour changer un statut durablement, utilise le workflow ci-dessus.

Statuts : `new`, `applied`, `interview`, `rejected`.

---

## 4. Utiliser le programme en local

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # puis remplis .env (jamais committé)

python main.py --no-email          # affiche le récap au lieu de l'envoyer
python main.py                     # run complet + email
python main.py --verbose           # journal détaillé (pour comprendre une erreur)
```

## 5. Personnaliser (`config.yaml`)

- `keywords` : ajoute ou retire des mots-clés. Accents, majuscules et tirets sont ignorés.
- `search_in` : `title` (strict) ou `title_and_description` (plus large).
- `lba.romes` : codes métiers envoyés à La Bonne Alternance.
- `lba.include_recruteurs` : `false` pour désactiver la section « candidatures spontanées ».
- `france_travail.enabled` : `false` pour désactiver France Travail.

## 6. Comment c'est organisé

| Fichier | Rôle |
|---|---|
| `main.py` | Chef d'orchestre : récupère, filtre, enregistre, envoie l'email |
| `sources/lba.py`, `sources/francetravail.py` | Un fichier par API (tout ce qui dépend d'une API est ici) |
| `filters.py` | Mots-clés, type de contrat, code postal 971 |
| `db.py` | Base SQLite et dédoublonnage |
| `emailer.py` | Mise en forme et envoi de l'email |
| `cli.py` | Suivi des candidatures |
| `tests/` | Tests (`python -m pytest`) |

**Doublons** : une offre est la même si (source, id) est identique, ou si le titre et l'entreprise sont identiques une fois nettoyés (accents, majuscules, ponctuation). La base le garantit elle-même (contraintes `UNIQUE`). Relancer le programme ne modifie jamais ton statut ni tes notes.

**Pannes** : si une source échoue, les autres continuent et l'email le signale. Si **toutes** les sources échouent, le workflow est marqué en échec (GitHub t'envoie alors un email). Si l'email ne part pas, les offres sont renvoyées au run suivant.

## 7. En cas de problème

- **« LBA_API_KEY absente » / « clé refusée »** : vérifie le secret GitHub et la clé sur le portail.
- **Erreur HTTP 400 La Bonne Alternance** : un code ROME ou un paramètre est refusé. Lance `python main.py --verbose` : le message de l'API est affiché. Compare avec la documentation technique : https://api.apprentissage.beta.gouv.fr/fr/documentation-technique
- **France Travail « accès refusé »** : voir le point 1-b. La source est facultative.
- **Aucun email** : regarde les journaux du run dans l'onglet Actions ; vérifie le mot de passe d'application (pas ton mot de passe Gmail normal).
- **Pas assez / trop d'offres** : ajuste `keywords` et `search_in`.
