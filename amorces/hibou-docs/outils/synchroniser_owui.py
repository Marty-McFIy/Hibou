#!/usr/bin/env python3
"""Recopie la documentation validée (docs/**/*.md) dans la base « Hibou · Documentation » d’Open WebUI.

Lancé par le runner après chaque fusion sur main. Bibliothèque standard uniquement.
Remplacement complet : les anciens fichiers de la base sont supprimés, puis tout est renvoyé,
pour qu’une page renommée ou retirée ne reste pas dans les réponses du chat.

    OWUI_URL=http://open-webui:8080 OWUI_CLE=sk-... python3 outils/synchroniser_owui.py docs
"""
import json, os, pathlib, sys, urllib.request, uuid

BASE = "Hibou · Documentation"


def appel(methode, chemin, corps=None, type_corps="application/json"):
    url = os.environ["OWUI_URL"].rstrip("/") + "/api/v1" + chemin
    donnees = json.dumps(corps).encode() if isinstance(corps, (dict, list)) else corps
    req = urllib.request.Request(url, donnees, method=methode,
                                 headers={"Authorization": f"Bearer {os.environ['OWUI_CLE']}", "Content-Type": type_corps})
    with urllib.request.urlopen(req, timeout=300) as r:
        texte = r.read()
    return json.loads(texte) if texte.strip() else {}


def envoyer(nom, contenu):
    """Téléversement multipart, sans bibliothèque externe."""
    borne = uuid.uuid4().hex
    corps = (f"--{borne}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{nom}\"\r\n"
             f"Content-Type: text/markdown\r\n\r\n").encode() + contenu + f"\r\n--{borne}--\r\n".encode()
    return appel("POST", "/files/", corps, f"multipart/form-data; boundary={borne}")["id"]


def main(dossier):
    pages = sorted(p for p in pathlib.Path(dossier).rglob("*.md") if "assets" not in p.parts)
    liste = appel("GET", "/knowledge/")
    liste = liste.get("items", liste) if isinstance(liste, dict) else liste
    base = next((k for k in liste if k.get("name") == BASE), None)
    if base is None:
        base = appel("POST", "/knowledge/create", {"name": BASE, "description": "Documentation validée de hibou-docs"})
    base = appel("GET", f"/knowledge/{base['id']}")
    for f in base.get("files") or []:
        appel("DELETE", f"/files/{f['id']}")
    for p in pages:
        nom = str(p.relative_to(dossier)).replace("/", "--")
        appel("POST", f"/knowledge/{base['id']}/file/add", {"file_id": envoyer(nom, p.read_bytes())})
        print(f"  {nom}")
    print(f"{len(pages)} pages dans « {BASE} ».")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs")
