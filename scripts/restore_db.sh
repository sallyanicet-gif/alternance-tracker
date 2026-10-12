#!/usr/bin/env bash
# Récupère offers.db depuis la branche "data" (si elle existe déjà).
set -euo pipefail

if git ls-remote --exit-code --heads origin data >/dev/null 2>&1; then
  git fetch origin +data:refs/remotes/origin/data
  git show origin/data:offers.db > offers.db
  echo "Base restaurée depuis la branche data."
else
  echo "Première exécution : la base sera créée."
fi
