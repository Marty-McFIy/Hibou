"""Amorce du dépôt hibou-eval : 8 tâches de code, 8 de documentation, 4 de vision, et le script de mesure."""
import json, pathlib, shutil, textwrap, cairosvg

RACINE = pathlib.Path("/home/claude/pack/hibou-0.5.0")
OUT = RACINE / "amorces/hibou-eval"
shutil.rmtree(OUT, ignore_errors=True)

def ecrire(chemin, texte):
    p = OUT / chemin
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(texte, bytes):
        p.write_bytes(texte)
    else:
        p.write_text(textwrap.dedent(texte).lstrip("\n"))

# ─── Code : énoncé + test exécuté dans un conteneur sans réseau ─────────────
CODE = {
 "01-duree": ("Écris `parse_duree(texte: str) -> int` qui convertit une durée comme `1h30m`, `45s`, `2h`, `1h2m3s` en secondes. Lève `ValueError` pour une entrée vide ou invalide (`10x`, `h`, `1h1h`).", """
from solution import parse_duree
assert parse_duree("1h30m") == 5400
assert parse_duree("45s") == 45
assert parse_duree("2h") == 7200
assert parse_duree("1h2m3s") == 3723
for mauvais in ["", "10x", "h", "1h1h", "m5"]:
    try:
        parse_duree(mauvais); raise SystemExit(f"accepté : {mauvais!r}")
    except ValueError:
        pass
"""),
 "02-intervalles": ("Écris `fusionner(intervalles: list[tuple[int, int]]) -> list[tuple[int, int]]` qui fusionne les intervalles fermés qui se chevauchent ou se touchent, et renvoie le résultat trié.", """
from solution import fusionner
assert fusionner([]) == []
assert fusionner([(1, 3), (2, 6), (8, 10), (15, 18)]) == [(1, 6), (8, 10), (15, 18)]
assert fusionner([(5, 7), (1, 4), (4, 5)]) == [(1, 7)]
assert fusionner([(1, 10), (2, 3)]) == [(1, 10)]
"""),
 "03-slug": ("Écris `slug(texte: str) -> str` qui produit un identifiant d’URL : minuscules ASCII, accents retirés (`é` → `e`, `œ` → `oe`), tout autre caractère remplacé par un tiret, sans tiret en double ni en bord.", """
from solution import slug
assert slug("Procédure de sauvegarde") == "procedure-de-sauvegarde"
assert slug("  Œuvre : l’été 2026 !  ") == "oeuvre-l-ete-2026"
assert slug("déjà--vu") == "deja-vu"
assert slug("___") == ""
"""),
 "04-cache": ("Écris une classe `CacheLRU(capacite: int)` avec `lire(cle)` (renvoie `None` si absente) et `ecrire(cle, valeur)`. Quand la capacité est dépassée, la clé la moins récemment utilisée (lecture ou écriture) est retirée.", """
from solution import CacheLRU
c = CacheLRU(2)
c.ecrire("a", 1); c.ecrire("b", 2)
assert c.lire("a") == 1
c.ecrire("c", 3)
assert c.lire("b") is None and c.lire("a") == 1 and c.lire("c") == 3
c.ecrire("a", 10); c.ecrire("d", 4)
assert c.lire("c") is None and c.lire("a") == 10
"""),
 "05-reseau": ("Écris `dans_reseau(ip: str, reseau: str) -> bool` qui dit si une adresse IPv4 appartient à un réseau CIDR, sans utiliser le module `ipaddress`. Lève `ValueError` pour une adresse ou un réseau mal formé.", """
from solution import dans_reseau
assert dans_reseau("192.168.10.12", "192.168.10.0/24")
assert not dans_reseau("192.168.11.1", "192.168.10.0/24")
assert dans_reseau("10.1.2.3", "0.0.0.0/0")
assert dans_reseau("172.16.5.4", "172.16.0.0/12")
for a, r in [("256.1.1.1", "10.0.0.0/8"), ("1.2.3", "10.0.0.0/8"), ("1.2.3.4", "10.0.0.0/33")]:
    try:
        dans_reseau(a, r); raise SystemExit(f"accepté : {a} {r}")
    except ValueError:
        pass
"""),
 "06-journal": ("Écris `top_ip(lignes: list[str], n: int) -> list[tuple[str, int]]` qui lit des lignes de journal au format Caddy/Nginx combiné (l’IP est le premier champ) et renvoie les `n` IP les plus fréquentes, par nombre décroissant puis IP croissante. Les lignes vides ou sans IP valide sont ignorées.", """
from solution import top_ip
l = ['10.0.0.2 - - [16/Nov/2026] "GET / HTTP/1.1" 200', '10.0.0.1 - - [x] "GET /a" 404', '',
     '10.0.0.2 - - [x] "GET /b" 200', 'pas-une-ip - - [x]', '10.0.0.1 - - [x]', '10.0.0.3 - - [x]']
assert top_ip(l, 2) == [("10.0.0.1", 2), ("10.0.0.2", 2)]
assert top_ip(l, 5) == [("10.0.0.1", 2), ("10.0.0.2", 2), ("10.0.0.3", 1)]
"""),
 "07-correction": ("""Cette fonction doit renvoyer la moyenne glissante sur `k` valeurs, mais elle est fausse. Corrige-la sans changer sa signature.

```python
def moyenne_glissante(valeurs, k):
    resultat = []
    somme = 0
    for i, v in enumerate(valeurs):
        somme += v
        if i > k:
            somme -= valeurs[i - k]
        if i >= k:
            resultat.append(somme / k)
    return resultat
```""", """
from solution import moyenne_glissante
assert moyenne_glissante([1, 2, 3, 4, 5], 2) == [1.5, 2.5, 3.5, 4.5]
assert moyenne_glissante([4, 4, 4], 3) == [4.0]
assert moyenne_glissante([1, 2], 3) == []
"""),
 "08-env": ("Écris `lire_env(texte: str) -> dict[str, str]` qui lit un fichier `.env` : lignes `CLE=valeur`, commentaires `#` en début de ligne ignorés, préfixe `export ` toléré, valeurs entre guillemets simples ou doubles débarrassées de leurs guillemets, espaces autour de la clé et de la valeur retirés. Une ligne sans `=` lève `ValueError`.", """
from solution import lire_env
t = '''
# commentaire
export HIBOU_DOMAINE = hibou.lan
CLE="a=b c"
VIDE=
MOT='simple'
'''
assert lire_env(t) == {"HIBOU_DOMAINE": "hibou.lan", "CLE": "a=b c", "VIDE": "", "MOT": "simple"}
try:
    lire_env("SANS_EGAL"); raise SystemExit("accepté")
except ValueError:
    pass
"""),
}
for nom, (enonce, test) in CODE.items():
    ecrire(f"taches/code/{nom}/enonce.md", enonce + "\n")
    ecrire(f"taches/code/{nom}/test.py", test)

# ─── Documentation : sujet + notes factuelles, vérifiée sur le template ────
DOCS = {
 "01-restaurer-forgejo": ("procedure", "Restaurer Forgejo depuis une sauvegarde",
  "Forgejo tourne en conteneur sur la VM forge, dossier /srv/forgejo, compose « hibou-forge ». Sauvegardes : /srv/forgejo/data/sauvegardes/forgejo-AAAAMMJJ-HHMM.zip, produites par forgejo dump. Base SQLite. Arrêt : docker compose stop forgejo."),
 "02-ajouter-modele": ("procedure", "Ajouter un modèle au catalogue llama-swap du 5820",
  "Modèles dans /srv/models, configuration /srv/hibou/llama-swap.yaml, redémarrage : docker compose -f /srv/hibou/compose.yaml restart llama-swap. Les modèles arrivent par le bundle, vérifié par SHA256SUMS."),
 "03-fiche-llama-swap": ("fiche-technique", "llama-swap sur le Precision 5820",
  "llama-swap sert une API compatible OpenAI sur le port interne 8080, charge les modèles à la demande. Carte RTX 6000 Ada 48 Go. Modèles : Qwen3.8-27B Q8, Qwen3-Coder-Next Q4, Qwen2.5-Coder 7B pour l’autocomplétion. Exposé par Caddy sur llm-dev.hibou.lan avec une clé d’API."),
 "04-guide-redaction": ("guide-utilisateur", "Rédiger un document avec Hibou dans Open WebUI",
  "Adresse chat.hibou.lan, connexion par le compte Forgejo. Choisir un modèle « Hibou · <type> », donner le sujet et les notes. Publication par l’outil « Publier dans Forgejo », qui ouvre une pull request dans hibou-docs. Le site est docs.hibou.lan."),
 "05-architecture": ("architecture", "Infrastructure Hibou",
  "Precision 5820 (Ubuntu 26.04, RTX 6000 Ada) : IA de développement, OpenCode. Precision 7910 (Proxmox 9.2) : conteneur LXC doc avec 4 Quadro RTX 4000 (Open WebUI), VM forge (Forgejo, registre, supervision, DNS). Réseau isolé, mises à jour par bundle sur disque USB. Connexion unique par Forgejo."),
 "06-decision-gpu": ("decision", "GPU du 7910 : passthrough PCI ou conteneur LXC",
  "Passthrough : isolation forte, mais exige des groupes IOMMU propres et réserve les cartes à une VM. LXC : pas de contrainte IOMMU, cartes visibles de l’hôte, mais pilotes hôte et conteneur à garder strictement identiques. Choix retenu : LXC."),
 "07-fiche-runner": ("fiche-technique", "Runner Forgejo Actions",
  "Conteneur forgejo-runner sur la VM forge, étiquette hibou-docs, image hibou/docs-builder (MkDocs Material, mermaid-cli, markdownlint). Une tâche à la fois. Publie le site dans /srv/docs-site. Aucune action externe."),
 "08-guide-alertes": ("guide-utilisateur", "Recevoir les alertes Hibou",
  "Alertes envoyées par Prometheus via Alertmanager au serveur ntfy, sujet « hibou », adresse alertes.hibou.lan. Abonnement depuis le navigateur ou l’application ntfy sur le réseau interne. Cinq alertes : machine injoignable, disque à 85 %, GPU à 85 °C, erreur SMART, sauvegarde de plus de 26 h."),
}
for nom, (modele, sujet, notes) in DOCS.items():
    ecrire(f"taches/doc/{nom}.json", json.dumps({"modele": modele, "sujet": sujet, "notes": notes}, ensure_ascii=False, indent=2) + "\n")

# ─── Vision : images synthétiques + mots attendus ───────────────────────────
F = "font-family='DejaVu Sans Mono, monospace'"
def svg(l, h, corps):
    return f"<svg xmlns='http://www.w3.org/2000/svg' width='{l}' height='{h}'><rect width='100%' height='100%' fill='#0F1420'/>{corps}</svg>"
def lignes(txts, x=20, y=40, pas=26, taille=17, couleur="#E9E4D8"):
    return "".join(f"<text x='{x}' y='{y + i * pas}' {F} font-size='{taille}' fill='{couleur}'>{t}</text>" for i, t in enumerate(txts))

VISION = {
 "01-gpu": (svg(760, 230, lignes([
    "GPU  Nom                 Temp   Mémoire",
    "0    Quadro RTX 4000     61C    6120MiB / 8192MiB",
    "1    Quadro RTX 4000     66C    5980MiB / 8192MiB",
    "2    Quadro RTX 4000     84C    7710MiB / 8192MiB",
    "3    Quadro RTX 4000     63C    6002MiB / 8192MiB"])),
    "Quelle carte est la plus chaude, à quelle température, et quelle mémoire utilise-t-elle ?", ["2", "84", "7710"]),
 "02-tableau": (svg(620, 210, lignes([
    "Machine   Point de montage   Taille   Utilisé",
    "forge     /                  60 Go    41 %",
    "doc       /srv/models        150 Go   88 %",
    "dev       /                  240 Go   63 %"], taille=18, pas=34)),
    "Transcris ce tableau en Markdown, puis dis quelle machine dépasse le seuil d’alerte de 85 %.", ["|", "doc", "88", "srv/models"]),
 "03-schema": ("<svg xmlns='http://www.w3.org/2000/svg' width='700' height='300'><rect width='100%' height='100%' fill='#E9E4D8'/>"
    "<g font-family='DejaVu Sans' font-size='18' fill='#0F1420'>"
    "<rect x='40' y='40' width='160' height='60' rx='8' fill='none' stroke='#0F1420' stroke-width='2'/><text x='86' y='77'>OpenCode</text>"
    "<rect x='40' y='200' width='160' height='60' rx='8' fill='none' stroke='#0F1420' stroke-width='2'/><text x='80' y='237'>llama-swap</text>"
    "<rect x='480' y='120' width='160' height='60' rx='8' fill='none' stroke='#0F1420' stroke-width='2'/><text x='525' y='157'>Forgejo</text>"
    "<line x1='120' y1='100' x2='120' y2='198' stroke='#0F1420' stroke-width='2'/><polygon points='114,190 126,190 120,200' fill='#0F1420'/>"
    "<line x1='200' y1='70' x2='478' y2='145' stroke='#0F1420' stroke-width='2'/><polygon points='470,138 478,146 467,149' fill='#0F1420'/>"
    "<text x='300' y='92' font-size='15'>Git SSH</text><text x='130' y='155' font-size='15'>API</text></g></svg>",
    "Reproduis ce schéma en Mermaid, avec les libellés des liens.", ["mermaid", "OpenCode", "llama-swap", "Forgejo", "Git SSH", "API"]),
 "04-erreur": ("<svg xmlns='http://www.w3.org/2000/svg' width='560' height='200'><rect width='100%' height='100%' fill='#171E2D'/>"
    "<rect x='20' y='20' width='520' height='160' rx='14' fill='#3A1E18' stroke='#F0876B'/>"
    "<text x='44' y='70' font-family='DejaVu Sans' font-size='22' fill='#F0876B'>Erreur</text>"
    "<text x='44' y='110' font-family='DejaVu Sans' font-size='18' fill='#E9E4D8'>Port réservé. Choisis-en un au-dessus de 1024.</text>"
    "<text x='44' y='145' font-family='DejaVu Sans Mono' font-size='15' fill='#8A93A6'>llama-swap --listen :443</text></svg>",
    "Que dit ce message, quelle commande l’a provoqué, et que faut-il faire ?", ["port", "1024", "443"]),
}
for nom, (image, question, attendus) in VISION.items():
    ecrire(f"taches/vision/{nom}.png", cairosvg.svg2png(bytestring=image.encode()))
    ecrire(f"taches/vision/{nom}.json", json.dumps({"question": question, "attendus": attendus}, ensure_ascii=False, indent=2) + "\n")

# Templates : copie de ceux de hibou-docs, pour un dépôt autonome.
for t in (RACINE / "amorces/hibou-docs/templates").glob("*.md"):
    ecrire(f"templates/{t.name}", t.read_text())

ecrire("README.md", """
# hibou-eval

Vingt tâches réelles pour comparer les modèles du catalogue llama-swap et vérifier qu’une mise à jour ne dégrade rien.

| Famille | Tâches | Notation |
| --- | --- | --- |
| Code | 8 | Automatique : le test passe ou non, exécuté dans un conteneur sans réseau |
| Documentation | 8 | Automatique sur la forme (sections, consignes, schéma) ; note humaine de 1 à 5 à reporter dans le CSV |
| Vision | 4 | Part des éléments attendus présents dans la réponse |

## Lancer une évaluation

Depuis la VM forge (Docker requis pour isoler le code produit) :

```bash
python3 evaluer.py --api https://llm-dev.hibou.lan/v1 --cle "$(cat cle-dev)" --modeles qwen3.8-27b,qwen3-coder-next --familles code
python3 evaluer.py --api https://llm-doc.hibou.lan/v1 --cle "$(cat cle-doc)" --modeles gemma-4-26b,qwen3.8-27b --familles doc,vision
```

Les résultats vont dans `resultats/AAAA-MM-JJ/` : un CSV par lancement, et les réponses brutes pour relecture. Pour les documents, ouvre chaque fichier `.md` produit et note-le de 1 à 5 dans la colonne `note_humaine` (conformité, exactitude, français, schémas).

## Règle d’adoption

Un modèle candidat remplace le modèle en place s’il fait au moins aussi bien sur le code et la documentation, sans perte de vitesse de plus de 20 %. `--reference <modèle>` affiche ce verdict pour chaque candidat.

Commite le CSV de chaque évaluation : l’historique sert de référence aux mises à jour suivantes.
""")

ecrire("evaluer.py", r'''
#!/usr/bin/env python3
"""Évalue les modèles d'un serveur llama-swap sur les tâches de taches/. Bibliothèque standard uniquement."""
import argparse, base64, csv, datetime, json, pathlib, re, shutil, ssl, subprocess, sys, tempfile, time, urllib.request

ICI = pathlib.Path(__file__).resolve().parent
AMBRE, PIERRE, SUCCES, DANGER, FIN = ("\033[38;2;242;181;68m", "\033[38;2;138;147;166m", "\033[38;2;92;200;184m", "\033[38;2;240;135;107m", "\033[0m") if sys.stdout.isatty() else ("",) * 5

CONSIGNE_CODE = "Tu es un développeur Python rigoureux. Réponds uniquement avec un bloc ```python contenant le module complet solution.py, sans explication."
CONSIGNE_DOC = ("Tu es Hibou, assistant de rédaction technique. Tu écris en français, ton calme et précis, sans point d’exclamation ni émoji. "
                "Produis UN document Markdown complet qui suit exactement le template : en-tête YAML recopié (modele, titre), toutes les sections ## dans l’ordre, "
                "aucune consigne <!-- --> restante, schémas en blocs ```mermaid. N’invente aucune information absente des notes : écris « À compléter : » à la place. "
                "Ne pose pas de question : rédige directement.")


def appeler(api, cle, modele, messages, contexte):
    corps = json.dumps({"model": modele, "messages": messages, "temperature": 0.2, "max_tokens": 8192}).encode()
    req = urllib.request.Request(f"{api}/chat/completions", corps, {"Content-Type": "application/json", "Authorization": f"Bearer {cle}"})
    debut = time.monotonic()
    with urllib.request.urlopen(req, timeout=900, context=contexte) as r:
        rep = json.load(r)
    duree = time.monotonic() - debut
    texte = rep["choices"][0]["message"].get("content") or ""
    texte = re.sub(r"<think>.*?</think>", "", texte, flags=re.S).strip()
    sortie = rep.get("usage", {}).get("completion_tokens", 0)
    return texte, duree, sortie


def bloc(texte, langage):
    blocs = re.findall(rf"```{langage}\s*\n(.*?)```", texte, re.S)
    return blocs[-1] if blocs else None


def noter_code(tache, reponse, isoler):
    code = bloc(reponse, "python")
    if code is None:
        return 0, "aucun bloc python"
    with tempfile.TemporaryDirectory() as d:
        (pathlib.Path(d) / "solution.py").write_text(code)
        shutil.copy(tache / "test.py", d)
        cmd = (["docker", "run", "--rm", "--network", "none", "--memory", "512m", "-v", f"{d}:/t:ro", "-w", "/t",
                "hibou/docs-builder:actuel", "python3", "test.py"] if isoler else [sys.executable, "test.py"])
        try:
            r = subprocess.run(cmd, cwd=d, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            return 0, "délai dépassé"
    return (1, "") if r.returncode == 0 else (0, (r.stderr or r.stdout).strip().splitlines()[-1:][0] if (r.stderr or r.stdout).strip() else "échec")


def entete(texte):
    m = re.match(r"^---\n(.*?)\n---\n", texte, re.S)
    if not m:
        return {}
    return dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M))


def sections(template):
    m = re.search(r"^sections:\s*\[(.*)\]$", template, re.M)
    return json.loads(f"[{m.group(1)}]") if m else []


def noter_doc(spec, reponse):
    texte = reponse.strip()
    texte = re.sub(r"^```(?:markdown|md)?\s*\n(.*)\n```$", r"\1", texte, flags=re.S)
    attendues = sections((ICI / "templates" / f"{spec['modele']}.md").read_text())
    titres = [t.strip() for t in re.findall(r"^## (.+)$", texte, re.M)]
    points, remarques = 0, []
    if entete(texte).get("modele") == spec["modele"]:
        points += 1
    else:
        remarques.append("en-tête")
    if [t for t in titres if t in attendues] == attendues:
        points += 1
    else:
        remarques.append("sections")
    if "<!--" not in texte:
        points += 1
    else:
        remarques.append("consignes")
    if spec["modele"] == "architecture":
        if bloc(texte, "mermaid"):
            points += 1
        else:
            remarques.append("schéma")
        return points / 4, ", ".join(remarques), texte
    return points / 3, ", ".join(remarques), texte


def noter_vision(spec, reponse):
    bas = reponse.lower()
    manquants = [a for a in spec["attendus"] if a.lower() not in bas]
    return 1 - len(manquants) / len(spec["attendus"]), ", ".join(manquants)


def main():
    a = argparse.ArgumentParser(description="Évaluation des modèles Hibou.")
    a.add_argument("--api", required=True, help="ex. https://llm-dev.hibou.lan/v1")
    a.add_argument("--cle", required=True, help="clé d’API du nœud")
    a.add_argument("--modeles", required=True, help="liste séparée par des virgules")
    a.add_argument("--familles", default="code,doc,vision")
    a.add_argument("--reference", help="modèle en place, pour appliquer la règle d’adoption")
    a.add_argument("--ca", help="certificat racine Hibou, si le système ne le connaît pas")
    a.add_argument("--sans-isolation", action="store_true", help="exécute le code produit sans conteneur (déconseillé)")
    o = a.parse_args()

    isoler = not o.sans_isolation
    if isoler and not shutil.which("docker"):
        sys.exit("Docker est absent : je n’exécute pas de code produit sans isolation. Lance l’évaluation sur forge, ou ajoute --sans-isolation en connaissance de cause.")
    contexte = ssl.create_default_context(cafile=o.ca)
    familles = o.familles.split(",")
    jour = datetime.date.today().isoformat()
    dossier = ICI / "resultats" / jour
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / f"evaluation-{datetime.datetime.now():%H%M}.csv"
    lignes = []

    for modele in o.modeles.split(","):
        print(f"\n{AMBRE}▸{FIN} {modele}")
        rep_dir = dossier / modele
        rep_dir.mkdir(exist_ok=True)
        if "code" in familles:
            for t in sorted((ICI / "taches/code").iterdir()):
                msg = [{"role": "system", "content": CONSIGNE_CODE}, {"role": "user", "content": (t / "enonce.md").read_text()}]
                rep, duree, sortie = appeler(o.api, o.cle, modele, msg, contexte)
                score, remarque = noter_code(t, rep, isoler)
                (rep_dir / f"code-{t.name}.md").write_text(rep)
                lignes.append([jour, modele, "code", t.name, score, round(duree, 1), sortie, remarque, ""])
                print(f"  code   {t.name:<24} {SUCCES + 'réussi' if score else DANGER + 'échoué'}{FIN}  {PIERRE}{duree:5.1f} s {remarque}{FIN}")
        if "doc" in familles:
            for t in sorted((ICI / "taches/doc").glob("*.json")):
                spec = json.loads(t.read_text())
                template = (ICI / "templates" / f"{spec['modele']}.md").read_text()
                msg = [{"role": "system", "content": CONSIGNE_DOC + "\n\nTemplate :\n\n" + template},
                       {"role": "user", "content": f"Sujet : {spec['sujet']}\n\nNotes : {spec['notes']}"}]
                rep, duree, sortie = appeler(o.api, o.cle, modele, msg, contexte)
                score, remarque, texte = noter_doc(spec, rep)
                (rep_dir / f"doc-{t.stem}.md").write_text(texte)
                lignes.append([jour, modele, "doc", t.stem, round(score, 2), round(duree, 1), sortie, remarque, ""])
                print(f"  doc    {t.stem:<24} {score:4.0%}  {PIERRE}{duree:5.1f} s {remarque}{FIN}")
        if "vision" in familles:
            for t in sorted((ICI / "taches/vision").glob("*.json")):
                spec = json.loads(t.read_text())
                image = base64.b64encode(t.with_suffix(".png").read_bytes()).decode()
                msg = [{"role": "user", "content": [{"type": "text", "text": spec["question"]},
                                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}}]}]
                rep, duree, sortie = appeler(o.api, o.cle, modele, msg, contexte)
                score, remarque = noter_vision(spec, rep)
                (rep_dir / f"vision-{t.stem}.md").write_text(rep)
                lignes.append([jour, modele, "vision", t.stem, round(score, 2), round(duree, 1), sortie, remarque, ""])
                print(f"  vision {t.stem:<24} {score:4.0%}  {PIERRE}{duree:5.1f} s {('manque : ' + remarque) if remarque else ''}{FIN}")

    with fichier.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "modele", "famille", "tache", "score", "duree_s", "tokens_sortie", "remarque", "note_humaine"])
        w.writerows(lignes)

    synthese = {}
    for _, m, fam, _, score, duree, sortie, _, _ in lignes:
        s = synthese.setdefault(m, {}).setdefault(fam, [0, 0, 0, 0])
        s[0] += score; s[1] += 1; s[2] += duree; s[3] += sortie
    print(f"\n{AMBRE}▸{FIN} Synthèse")
    for m, fams in synthese.items():
        for fam, (sc, n, du, so) in fams.items():
            print(f"  {m:<20} {fam:<7} {sc / n:4.0%}  {so / du if du else 0:6.1f} tokens/s")

    if o.reference and o.reference in synthese:
        ref = synthese[o.reference]
        print(f"\n{AMBRE}▸{FIN} Règle d’adoption face à {o.reference}")
        for m, fams in synthese.items():
            if m == o.reference:
                continue
            qualite = all(fams[f][0] / fams[f][1] >= ref[f][0] / ref[f][1] for f in ("code", "doc") if f in fams and f in ref)
            v_ref = sum(x[3] for x in ref.values()) / max(sum(x[2] for x in ref.values()), 1e-9)
            v_m = sum(x[3] for x in fams.values()) / max(sum(x[2] for x in fams.values()), 1e-9)
            vitesse = v_m >= 0.8 * v_ref
            verdict = f"{SUCCES}adoptable{FIN}" if qualite and vitesse else f"{DANGER}à écarter{FIN}"
            print(f"  {m:<20} {verdict}  {PIERRE}qualité {'tenue' if qualite else 'en recul'}, vitesse {v_m / v_ref:.0%} de la référence{FIN}")
        print(f"  {PIERRE}Le verdict sur la documentation reste à confirmer par tes notes humaines.{FIN}")

    print(f"\nJ’ai écrit {fichier.relative_to(ICI)}.")


if __name__ == "__main__":
    main()
''')
print("ok", sum(1 for _ in OUT.rglob("*") if _.is_file()), "fichiers")
