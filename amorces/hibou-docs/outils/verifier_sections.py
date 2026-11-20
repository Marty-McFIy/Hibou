"""Vérifie que chaque document contient les sections de son template, dans l'ordre."""
import pathlib, re, sys, yaml

def entete(texte):
    m = re.match(r"^---\n(.*?)\n---\n", texte, re.S)
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
