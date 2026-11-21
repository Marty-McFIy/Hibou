"""Amorces de la chaîne documentaire Hibou : dépôt hibou-docs, modèles et outil Open WebUI."""
import json, pathlib, shutil, textwrap

RACINE = pathlib.Path("/home/claude/pack/hibou-0.3.0")
OUT = RACINE / "amorces"
shutil.rmtree(OUT, ignore_errors=True)
CHARTE = RACINE / "charte/commun"

def ecrire(chemin, texte):
    p = OUT / chemin
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(texte, bytes):
        p.write_bytes(texte)
    else:
        p.write_text(textwrap.dedent(texte).lstrip("\n"))

# ─── Templates ──────────────────────────────────────────────────────────────
# id, titre, public, sections (titre, consigne)
TEMPLATES = [
    ("procedure", "Procédure", "exploitants", [
        ("Objet", "Une ou deux phrases : ce que la procédure permet de faire et quand l’utiliser."),
        ("Prérequis", "Droits, accès, outils et état attendu du système avant de commencer."),
        ("Étapes", "Liste numérotée. Une action par étape, avec la commande exacte et le résultat attendu."),
        ("Vérification", "Comment constater que l’opération a réussi."),
        ("Retour arrière", "Comment annuler, étape par étape, si quelque chose échoue."),
    ]),
    ("fiche-technique", "Fiche technique", "équipe technique", [
        ("Résumé", "Ce qu’est le composant, en trois phrases au plus."),
        ("Caractéristiques", "Tableau : versions, ressources, ports, dépendances."),
        ("Configuration", "Fichiers et paramètres importants, avec leurs valeurs par défaut."),
        ("Exploitation", "Démarrage, arrêt, journaux, supervision."),
        ("Limites connues", "Ce que le composant ne fait pas ou fait mal, et les contournements."),
    ]),
    ("guide-utilisateur", "Guide utilisateur", "utilisateurs", [
        ("À quoi ça sert", "Le besoin couvert, sans jargon."),
        ("Premiers pas", "Accès, connexion et première action, avec captures si fournies."),
        ("Tâches courantes", "Une sous-section par tâche, en étapes courtes."),
        ("Questions fréquentes", "Questions et réponses brèves."),
        ("Obtenir de l’aide", "Qui contacter et quelles informations donner."),
    ]),
    ("architecture", "Document d’architecture", "équipe technique", [
        ("Contexte", "Le besoin, les contraintes et le périmètre."),
        ("Vue d’ensemble", "Un schéma Mermaid des composants et de leurs liens, puis une phrase de lecture."),
        ("Composants", "Un paragraphe par composant : rôle, technologie, hébergement."),
        ("Flux", "Les échanges principaux, avec un diagramme de séquence Mermaid si utile."),
        ("Sécurité", "Accès, secrets, cloisonnement."),
        ("Décisions et alternatives", "Les choix faits, les options écartées et pourquoi."),
    ]),
    ("decision", "Note de décision", "équipe technique", [
        ("Contexte", "La situation qui impose de décider."),
        ("Options", "Tableau des options avec avantages et inconvénients."),
        ("Décision", "L’option retenue, en une phrase."),
        ("Conséquences", "Ce qui change, ce qu’il faut faire ensuite."),
    ]),
]

for tid, titre, public, sections in TEMPLATES:
    corps = "\n\n".join(f"## {s}\n\n<!-- {c} -->" for s, c in sections)
    noms = ", ".join(json.dumps(s, ensure_ascii=False) for s, _ in sections)
    ecrire(f"hibou-docs/templates/{tid}.md", f"""---
modele: {tid}
titre: {titre}
public: {public}
sections: [{noms}]
---

# Titre du document

{corps}
""")

# ─── Dépôt hibou-docs ───────────────────────────────────────────────────────
ecrire("hibou-docs/README.md", """
# hibou-docs

Documentation produite avec Hibou. Chaque document part d’un template de `templates/` et porte dans son en-tête le champ `modele`.

À chaque pull request, le runner vérifie le style Markdown, la présence des sections du template et la validité des schémas Mermaid. À la fusion dans `main`, le site est publié sur `docs.hibou.lan`.

Pour ajouter un type de document, crée un fichier dans `templates/` avec la liste `sections`. Le modèle correspondant dans Open WebUI se régénère avec `outils/modeles_open_webui.py`.
""")
ecrire("hibou-docs/docs/index.md", """
# Documentation

Bienvenue. Les documents sont classés par type dans le menu.
""")
ecrire("hibou-docs/mkdocs.yml", """
site_name: Hibou · Documentation
site_url: https://docs.hibou.lan/
docs_dir: docs
theme:
  name: material
  language: fr
  font: false
  logo: assets/logos/symbole-sur-nuit.svg
  favicon: assets/logos/favicon.svg
  palette:
    - scheme: slate
      toggle: { icon: material/weather-sunny, name: Thème Brume }
    - scheme: default
      toggle: { icon: material/weather-night, name: Thème Nuit }
  features: [navigation.sections, navigation.top, search.highlight, content.code.copy]
extra_css:
  - assets/hibou-jetons.css
  - assets/hibou-mkdocs.css
markdown_extensions:
  - admonition
  - tables
  - toc: { permalink: true }
  - pymdownx.superfences
  - pymdownx.details
plugins:
  - search: { lang: fr }
""")
ecrire("hibou-docs/docs/assets/hibou-jetons.css", (CHARTE / "hibou-jetons.css").read_text().replace("./fonts", "./fonts"))
for f in (CHARTE / "fonts").iterdir():
    ecrire(f"hibou-docs/docs/assets/fonts/{f.name}", f.read_bytes())
for f in (CHARTE / "logos").iterdir():
    ecrire(f"hibou-docs/docs/assets/logos/{f.name}", f.read_bytes())
ecrire("hibou-docs/docs/assets/hibou-mkdocs.css", """
/* Material for MkDocs aux couleurs de Hibou : slate = Nuit, default = Brume. */
[data-md-color-scheme="slate"] { color-scheme: dark; }
[data-md-color-scheme="slate"], [data-md-color-scheme="default"] {
  --md-default-bg-color: var(--fond);
  --md-default-fg-color: var(--texte);
  --md-default-fg-color--light: var(--texte-doux);
  --md-default-fg-color--lighter: var(--filet-fort);
  --md-default-fg-color--lightest: var(--filet);
  --md-primary-fg-color: var(--fond-creux);
  --md-primary-bg-color: var(--texte);
  --md-accent-fg-color: var(--accent-texte);
  --md-typeset-a-color: var(--accent-texte);
  --md-code-bg-color: var(--fond-creux);
  --md-code-fg-color: var(--texte);
  --md-footer-bg-color: var(--fond-creux);
  --md-text-font-family: Inter, system-ui, sans-serif;
  --md-code-font-family: "JetBrains Mono", ui-monospace, monospace;
}
/* Les jetons suivent le schéma choisi par le lecteur. */
[data-md-color-scheme="default"] {
  --fond: #E9E4D8; --fond-creux: #DCD6C7; --surface: #F2EEE4; --texte: #0F1420; --texte-doux: #4A5468;
  --filet: #C9C3B4; --filet-fort: #787262; --accent-texte: #7A4F00;
}
.md-header, .md-tabs { background: #0A0E17; color: #E9E4D8; }
.md-typeset h1, .md-typeset h2 { font-family: Fraunces, Georgia, serif; font-weight: 600; }
.md-typeset pre > code { background: #0A0E17; color: #E9E4D8; }
.md-typeset img[src$=".svg"] { background: #FBF8F1; border-radius: 8px; padding: 12px; }
""")
ecrire("hibou-docs/.markdownlint-cli2.yaml", """
config:
  default: true
  MD013: false          # pas de limite de longueur de ligne
  MD033: false          # commentaires de consigne et balises simples autorisés
  MD041: false          # l’en-tête YAML précède le titre
globs: ["docs/**/*.md"]
""")
ecrire("hibou-docs/outils/verifier_sections.py", '''
"""Vérifie que chaque document contient les sections de son template, dans l'ordre."""
import pathlib, re, sys, yaml

def entete(texte):
    m = re.match(r"^---\\n(.*?)\\n---\\n", texte, re.S)
    return (yaml.safe_load(m.group(1)) or {}) if m else {}

templates = {p.stem: entete(p.read_text()) for p in pathlib.Path("templates").glob("*.md")}
erreurs = 0
for doc in sorted(pathlib.Path("docs").rglob("*.md")):
    texte = doc.read_text()
    tid = entete(texte).get("modele")
    if not tid:
        continue
    if tid not in templates:
        print(f"{doc} : template inconnu « {tid} ». Choisis parmi {', '.join(sorted(templates))}.")
        erreurs += 1
        continue
    titres = [t.strip() for t in re.findall(r"^## (.+)$", texte, re.M)]
    attendues = templates[tid]["sections"]
    manquantes = [s for s in attendues if s not in titres]
    if manquantes:
        print(f"{doc} : sections manquantes : {', '.join(manquantes)}.")
        erreurs += 1
    elif [t for t in titres if t in attendues] != attendues:
        print(f"{doc} : sections dans le désordre. Ordre attendu : {', '.join(attendues)}.")
        erreurs += 1
    if "<!--" in texte:
        print(f"{doc} : il reste des consignes du template à remplacer.")
        erreurs += 1

print(f"{erreurs} problème(s)." if erreurs else "Sections conformes.")
sys.exit(1 if erreurs else 0)
''')
ecrire("hibou-docs/outils/rendre_schemas.sh", """
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
""")
ecrire("hibou-docs/.forgejo/workflows/documentation.yml", """
name: Documentation
on:
  push:
    branches: [main]
  pull_request:

jobs:
  documentation:
    runs-on: hibou-docs
    steps:
      # Pas d’action externe : on récupère le dépôt directement depuis Forgejo.
      - name: Récupérer le dépôt
        run: |
          branche="${GITHUB_HEAD_REF:-$GITHUB_REF_NAME}"
          git clone --depth 1 --branch "$branche" "http://jeton:${{ github.token }}@forgejo:3000/${{ github.repository }}.git" depot
      - name: Style Markdown
        working-directory: depot
        run: markdownlint-cli2
      - name: Sections des templates
        working-directory: depot
        run: python3 outils/verifier_sections.py
      - name: Schémas Mermaid
        working-directory: depot
        run: bash outils/rendre_schemas.sh
      - name: Construire le site
        working-directory: depot
        run: mkdocs build --strict -d ../site
      - name: Publier
        if: github.event_name == 'push'
        run: rsync -a --delete site/ /publication/
""")

# ─── Open WebUI : un modèle par template ────────────────────────────────────
CONSIGNE = """Tu es Hibou, assistant de rédaction technique. Tu écris en français, avec un ton calme, précis et sobre : phrases courtes, aucun point d’exclamation, aucun émoji, aucun superlatif.

L’utilisateur te donne un sujet, et parfois des notes, des captures ou des documents. Tu produis UN document Markdown complet qui suit exactement le template ci-dessous :
- recopie l’en-tête YAML (dont `modele`) en remplaçant seulement `titre`, et ajoute `date` (AAAA-MM-JJ) ;
- garde toutes les sections `##`, dans le même ordre et avec les mêmes intitulés ;
- remplace chaque consigne en commentaire `<!-- -->` par le contenu ; n’en laisse aucune ;
- pour un schéma, utilise un bloc ```mermaid valide ;
- blocs de code : une ligne vide avant et après, et le langage indiqué (```bash, ```text) ; adresses entre chevrons <https://…> ou dans du code ;
- n’invente ni commande, ni version, ni chiffre : si une information manque, écris « À compléter : » suivi de ce qu’il faut fournir.

Avant de rédiger, si le sujet est trop vague pour remplir les sections, pose au plus trois questions. Quand le document est prêt et que l’utilisateur le valide, propose de le publier dans Forgejo avec l’outil publier_document.

Template « {titre} » :

{template}"""

modeles = []
for tid, titre, public, _ in TEMPLATES:
    tpl = (OUT / f"hibou-docs/templates/{tid}.md").read_text()
    modeles.append({
        "id": f"hibou-{tid}",
        "name": f"Hibou · {titre}",
        "base_model_id": "gemma-4-26b",
        "meta": {"description": f"Rédige un document « {titre} » pour les {public}, à partir d’un sujet.",
                 "profile_image_url": "/static/hibou/symbole-sur-nuit.svg",
                 "toolIds": ["publier_forgejo"],
                 "capabilities": {"vision": True, "citations": True}},
        "params": {"system": CONSIGNE.format(titre=titre, template=tpl), "temperature": 0.4},
        "is_active": True,
    })
ecrire("open-webui/modeles-hibou.json", json.dumps(modeles, ensure_ascii=False, indent=2) + "\n")
ecrire("hibou-docs/outils/modeles_open_webui.py", "# Régénère amorces/open-webui/modeles-hibou.json depuis templates/ : voir gen_amorces.py dans le paquet hibou.\n")

ecrire("open-webui/publier_forgejo.py", '''
"""
title: Publier dans Forgejo
author: Hibou
version: 0.2.0
description: Dépose un document Markdown dans hibou-docs, sur une branche, et ouvre une pull request.
"""
import base64, datetime, re
import requests
from pydantic import BaseModel, Field


URL_NUE = re.compile(r"(?<![<(`\\[])\\bhttps?://[^\\s<>()`]+[^\\s<>()`.,;:!?]")


def normaliser(md: str) -> str:
    """Règles du runner (markdownlint) qu'un petit modèle oublie : langage et lignes vides autour des blocs de code,
    adresses nues entre chevrons, un seul saut de ligne final. Le texte lui-même n'est pas touché."""
    sortie, dans_bloc, fermeture = [], False, ""
    lignes = md.replace("\\r\\n", "\\n").split("\\n")
    for i, l in enumerate(lignes):
        m = re.match(r"^(\\s*)(`{3,}|~{3,})(.*)$", l)
        if m and not dans_bloc:
            dans_bloc, fermeture = True, m.group(2)
            if sortie and sortie[-1].strip():
                sortie.append("")
            sortie.append(l if m.group(3).strip() else f"{m.group(1)}{m.group(2)}text")
            continue
        if m and dans_bloc and m.group(2).startswith(fermeture[0]) and len(m.group(2)) >= len(fermeture) and not m.group(3).strip():
            dans_bloc = False
            sortie.append(l)
            if i + 1 < len(lignes) and lignes[i + 1].strip():
                sortie.append("")
            continue
        if not dans_bloc:
            # Hors code en ligne : les segments entre accents graves restent tels quels.
            l = "`".join(p if k % 2 else URL_NUE.sub(lambda u: f"<{u.group(0)}>", p) for k, p in enumerate(l.split("`")))
        sortie.append(l)
    return "\\n".join(sortie).rstrip("\\n") + "\\n"


class Tools:
    class Valves(BaseModel):
        forgejo_url: str = Field("https://forge.hibou.lan", description="Adresse de Forgejo.")
        depot: str = Field("hibou/hibou-docs", description="Dépôt cible, organisation/nom.")
        jeton: str = Field("", description="Jeton du compte hibou-redac (donné par « hibou configurer »).")

    def __init__(self):
        self.valves = self.Valves()

    def _api(self, methode, chemin, **kw):
        r = requests.request(methode, f"{self.valves.forgejo_url}/api/v1/repos/{self.valves.depot}{chemin}",
                             headers={"Authorization": f"token {self.valves.jeton}"}, timeout=30, **kw)
        r.raise_for_status()
        return r.json() if r.content else {}

    def publier_document(self, titre: str, chemin: str, contenu: str, __user__: dict = {}) -> str:
        """
        Publie un document Markdown dans Forgejo et ouvre une pull request à relire.
        :param titre: Titre du document, utilisé pour la pull request.
        :param chemin: Chemin du fichier dans le dépôt, sous docs/, terminé par .md (ex. docs/procedures/sauvegarde-forgejo.md).
        :param contenu: Le document Markdown complet, en-tête YAML compris.
        :return: L’adresse de la pull request, ou ce qu’il faut corriger.
        """
        if not self.valves.jeton:
            return "Aucun jeton configuré. Renseigne-le dans les réglages de l’outil."
        if not re.fullmatch(r"docs/[a-z0-9][a-z0-9/_-]*\\.md", chemin) or ".." in chemin:
            return "Chemin refusé. Utilise docs/<dossier>/<nom-en-minuscules>.md, sans espace ni accent."
        contenu = normaliser(contenu)
        if not contenu.startswith("---"):
            return "Le document doit commencer par son en-tête YAML (modele, titre)."
        auteur = (__user__ or {}).get("name", "inconnu")
        branche = "redaction/" + re.sub(r"[^a-z0-9-]", "-", chemin[5:-3]) + datetime.datetime.now().strftime("-%Y%m%d%H%M")
        try:
            self._api("POST", "/branches", json={"new_branch_name": branche, "old_branch_name": "main"})
            self._api("POST", f"/contents/{chemin}", json={
                "branch": branche, "message": f"Rédaction : {titre}",
                "content": base64.b64encode(contenu.encode()).decode()})
            pr = self._api("POST", "/pulls", json={
                "head": branche, "base": "main", "title": titre,
                "body": f"Document rédigé avec Hibou pour {auteur}. Le runner vérifie le style, les sections et les schémas."})
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 422:
                return "Ce fichier existe déjà sur main. Choisis un autre chemin, ou modifie-le dans Forgejo."
            return f"Forgejo a refusé la publication ({e}). Vérifie le jeton et le dépôt dans les réglages de l’outil."
        return f"J’ai ouvert la pull request : {pr.get('html_url')}"
''')
print("ok", sum(1 for _ in OUT.rglob("*") if _.is_file()), "fichiers")
