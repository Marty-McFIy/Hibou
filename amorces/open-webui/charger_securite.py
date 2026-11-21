#!/usr/bin/env python3
"""Remplit la base « Hibou · Sécurité » d’Open WebUI avec les PDF de securite/ (guides de l’ANSSI, textes de référence, ajouts).

Lancé en tâche de fond sur forge par « hibou installer forge » ou « mettre-a-jour forge » (systemctl status hibou-securite).
N’envoie que les documents absents de la base : une relance reprend où elle s’était arrêtée. Bibliothèque standard uniquement.

    OWUI_URL=http://open-webui:8080 OWUI_CLE=sk-… BASE_ID=… python3 charger_securite.py /securite
"""
import json, os, pathlib, sys, time, urllib.request, uuid


def appel(methode, chemin, corps=None, type_corps="application/json", delai=900):
    donnees = json.dumps(corps).encode() if isinstance(corps, (dict, list)) else corps
    req = urllib.request.Request(os.environ["OWUI_URL"].rstrip("/") + "/api/v1" + chemin, donnees, method=methode,
                                 headers={"Authorization": f"Bearer {os.environ['OWUI_CLE']}", "Content-Type": type_corps})
    with urllib.request.urlopen(req, timeout=delai) as r:
        texte = r.read()
    return json.loads(texte) if texte.strip() else {}


def presents(base):
    noms, page = set(), 1
    while True:
        r = appel("GET", f"/knowledge/{base}/files?page={page}")
        items = r.get("items", []) if isinstance(r, dict) else r
        noms |= {(f.get("meta") or {}).get("name") or f.get("filename") for f in items}
        if not items or len(noms) >= (r.get("total", 0) if isinstance(r, dict) else 0):
            return noms
        page += 1


def envoyer(nom, contenu):
    borne = uuid.uuid4().hex
    corps = (f"--{borne}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{nom}\"\r\n"
             f"Content-Type: application/pdf\r\n\r\n").encode() + contenu + f"\r\n--{borne}--\r\n".encode()
    # Extraction du texte avant la réponse, sinon l’ajout à la base arrive avant elle (« content is empty »).
    return appel("POST", "/files/?process_in_background=false", corps, f"multipart/form-data; boundary={borne}")["id"]


def main(dossier):
    base = os.environ["BASE_ID"]
    deja = presents(base)
    lignes = [l.split("\t") for l in (dossier / "INDEX.tsv").read_text().splitlines() if l.strip()]
    nom = lambda titre: titre.replace("/", "-").strip() + ".pdf"   # nom affiché comme source dans le chat
    a_faire = [(chemin, titre) for chemin, titre, *_ in lignes if nom(titre) not in deja and (dossier / chemin).exists()]
    print(f"{len(lignes)} documents, {len(lignes) - len(a_faire)} déjà dans la base, {len(a_faire)} à ajouter.", flush=True)
    t0, echecs = time.time(), 0
    for n, (chemin, titre) in enumerate(a_faire, 1):
        try:
            fid = envoyer(nom(titre), (dossier / chemin).read_bytes())
            appel("POST", f"/knowledge/{base}/file/add", {"file_id": fid})
            print(f"[{n}/{len(a_faire)}] {titre} ({time.time() - t0:.0f} s)", flush=True)
        except Exception as e:
            echecs += 1
            print(f"[{n}/{len(a_faire)}] non ajouté : {titre} ({e})", flush=True)
    print(f"Terminé : {len(a_faire) - echecs} ajouté(s), {echecs} échec(s), {time.time() - t0:.0f} s.", flush=True)


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/securite"))
