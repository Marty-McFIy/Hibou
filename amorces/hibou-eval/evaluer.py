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
    try:
        with urllib.request.urlopen(req, timeout=900, context=contexte) as r:
            rep = json.load(r)
    except Exception as e:  # un modèle qui ne charge pas compte zéro, l’évaluation continue
        return f"[erreur API : {e}]", time.monotonic() - debut, 0
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


def ecrire_metriques(chemin, serveur, synthese):
    """Scores et vitesses au format Prometheus ; écriture atomique pour le collecteur textfile."""
    lignes = ["# HELP hibou_eval_score Part des tâches réussies (0 à 1).", "# TYPE hibou_eval_score gauge",
              "# HELP hibou_eval_tokens_par_seconde Vitesse de génération moyenne.", "# TYPE hibou_eval_tokens_par_seconde gauge"]
    for m, fams in synthese.items():
        for fam, (sc, n, du, so) in fams.items():
            etiq = f'serveur="{serveur}",modele="{m}",famille="{fam}"'
            lignes.append(f"hibou_eval_score{{{etiq}}} {sc / n:.4f}")
            lignes.append(f"hibou_eval_tokens_par_seconde{{{etiq}}} {so / du if du else 0:.2f}")
    lignes.append(f'hibou_eval_derniere_timestamp{{serveur="{serveur}"}} {int(time.time())}')
    tmp = chemin.with_suffix(".tmp")
    tmp.write_text("\n".join(lignes) + "\n")
    tmp.replace(chemin)


def main():
    a = argparse.ArgumentParser(description="Évaluation des modèles Hibou.")
    a.add_argument("--api", required=True, help="ex. https://llm-dev.hibou.lan/v1")
    a.add_argument("--cle", required=True, help="clé d’API du nœud")
    a.add_argument("--modeles", required=True, help="liste séparée par des virgules")
    a.add_argument("--familles", default="code,doc,vision")
    a.add_argument("--reference", help="modèle en place, pour appliquer la règle d’adoption")
    a.add_argument("--ca", help="certificat racine Hibou, si le système ne le connaît pas")
    a.add_argument("--sans-isolation", action="store_true", help="exécute le code produit sans conteneur (déconseillé)")
    a.add_argument("--serveur", default="", help="étiquette du serveur évalué (doc, dev) pour les métriques")
    a.add_argument("--metriques", help="fichier .prom écrit pour le collecteur textfile de node-exporter")
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
    if o.metriques:
        ecrire_metriques(pathlib.Path(o.metriques), o.serveur, synthese)

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
