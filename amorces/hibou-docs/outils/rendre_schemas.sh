#!/usr/bin/env bash
# Valide chaque schéma Mermaid et le remplace par une image SVG avant la construction du site.
set -euo pipefail
shopt -s globstar nullglob
n=0
for f in docs/**/*.md; do
  grep -q '^```mermaid' "$f" || continue
  mmdc -q -p /etc/puppeteer.json -i "$f" -o "$f" -e svg -b transparent
  n=$((n + 1))
done
echo "Schémas rendus dans $n document(s)."
