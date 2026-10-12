#!/usr/bin/env bash
# Sauvegarde offers.db sur la branche "data" (créée au premier passage).
# La branche "main" ne contient jamais la base : elle contient tes candidatures.
set -euo pipefail

[ -f offers.db ] || { echo "Pas de offers.db à sauvegarder."; exit 0; }

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

ROOT="$(pwd)"
TMP="$(mktemp -d)"
# Nettoyage : on retire le dossier de travail temporaire à la fin
trap 'cd "$ROOT"; git worktree remove --force "$TMP/data" 2>/dev/null || true' EXIT
if git ls-remote --exit-code --heads origin data >/dev/null 2>&1; then
  git fetch origin +data:refs/remotes/origin/data
  git worktree add -B data "$TMP/data" origin/data
  cp "$ROOT/offers.db" "$TMP/data/offers.db"
  cd "$TMP/data"
else
  # Première sauvegarde : branche vide (sans l'historique du code)
  git worktree add --detach "$TMP/data"
  cd "$TMP/data"
  git checkout --orphan data
  git rm -rf . >/dev/null 2>&1 || true
  cp "$ROOT/offers.db" offers.db
fi

git add -f offers.db
if git diff --cached --quiet; then
  echo "Base inchangée, rien à sauvegarder."
else
  git commit -m "Mise à jour de offers.db"
  git push origin HEAD:data
fi
