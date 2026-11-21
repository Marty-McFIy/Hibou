"""Essai de bout en bout de Hibou, comme une personne : connexion par Forgejo, chat, réponses sourcées, export,
chaîne de documentation (pull request, runner, relecture). Lancé par « hibou essai » dans le conteneur Open WebUI,
avec un compte d’essai temporaire. Mot de passe sur l’entrée standard, jamais affiché.

Sortie : une ligne par contrôle, « R<TAB>ok|attention|echec<TAB>libellé<TAB>détail », lue par le script hibou.
Usage : hibou_essai.py <domaine> <compte> <ca.crt> <modèles attendus, séparés par des virgules> [--sans-dev]"""
import base64, datetime, http.cookiejar, json, re, ssl, sys, time, urllib.error, urllib.parse, urllib.request, uuid

import socketio

DOMAINE, COMPTE, CA, ATTENDUS = sys.argv[1:5]
SANS_DEV = "--sans-dev" in sys.argv
MDP = sys.stdin.readline().strip()
FORGE, CHAT, U = f"https://forge.{DOMAINE}", f"https://chat.{DOMAINE}", "http://127.0.0.1:8080"
ctx = ssl.create_default_context(cafile=CA)
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx), urllib.request.HTTPCookieProcessor(jar))
TOK = None


def resultat(etat, libelle, detail=""):
    print(f"R\t{etat}\t{libelle}\t{detail}", flush=True)


def page(u, data=None):
    try:
        r = op.open(u, data=urllib.parse.urlencode(data).encode() if data else None, timeout=60)
        return r.geturl(), r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.geturl(), e.read().decode(errors="replace")


def api(m, p, corps=None, base=U, auth=None, delai=900):
    h = {"Content-Type": "application/json", "Authorization": auth or f"Bearer {TOK}"}
    r = urllib.request.Request(base + p, method=m, data=json.dumps(corps).encode() if corps is not None else None, headers=h)
    with (op if base.startswith("https") else urllib.request.build_opener()).open(r, timeout=delai) as f:
        return json.loads(f.read() or b"null")


def forgejo(m, p, corps=None):
    auth = "Basic " + base64.b64encode(f"{COMPTE}:{MDP}".encode()).decode()
    return api(m, p, corps, base=f"{FORGE}/api/v1", auth=auth, delai=60)


# ─── Connexion par Forgejo ────────────────────────────────────────────────
t = time.time()
url, html = page(f"{CHAT}/oauth/oidc/login")
if "/user/login" in url:
    csrf = re.search(r'name="_csrf" value="([^"]+)"', html).group(1)
    url, html = page(url, {"_csrf": csrf, "user_name": COMPTE, "password": MDP})
if "/login/oauth/grant" in html:
    champs = dict(re.findall(r'name="(_csrf|client_id|state|scope|nonce|redirect_uri|granted)" value="([^"]*)"', html))
    champs["granted"] = "true"
    url, html = page(f"{FORGE}/login/oauth/grant", champs)
TOK = next((c.value for c in jar if c.name == "token"), None)
if not TOK:
    resultat("echec", "Connexion au chat par Forgejo", f"arrivé sur {urllib.parse.urlsplit(url).path}")
    sys.exit(1)
resultat("ok", "Connexion au chat par Forgejo", f"{time.time() - t:.1f} s")

visibles = {m["id"] for m in api("GET", "/api/models")["data"]}
manquants = [m for m in ATTENDUS.split(",") if m and m not in visibles]
resultat("echec" if manquants else "ok", "Modèles Hibou visibles", ("manquent : " + ", ".join(manquants)) if manquants else f"{len(visibles)} modèles")


# ─── Chat, comme la page web (WebSocket) ───────────────────────────────────
sio = socketio.Client(ssl_verify=False)
fins, fichiers = set(), {}


@sio.on("events")
def evenement(d):
    t = (d.get("data") or {}).get("type"); donnees = d["data"].get("data") or {}
    if t == "chat:completion" and donnees.get("done"):
        fins.add(d.get("message_id"))
    if t in ("files", "chat:message:files"):
        fichiers.setdefault(d.get("message_id"), []).extend(donnees.get("files", []))


sio.connect(U, socketio_path="/ws/socket.io", transports=["websocket"], auth={"token": TOK})
sio.emit("user-join", {"auth": {"token": TOK}})
time.sleep(1)


def joindre(nom, contenu):
    """Envoie un fichier comme la page (multipart), attend l’extraction de son texte → élément à joindre au message."""
    limite = uuid.uuid4().hex
    corps = (f"--{limite}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{nom}\"\r\nContent-Type: text/plain\r\n\r\n").encode() \
        + contenu.encode() + f"\r\n--{limite}--\r\n".encode()
    r = urllib.request.Request(U + "/api/v1/files/?process_in_background=false", data=corps, method="POST",
                               headers={"Authorization": f"Bearer {TOK}", "Content-Type": f"multipart/form-data; boundary={limite}"})
    with urllib.request.urlopen(r, timeout=600) as x:
        f = json.loads(x.read())
    for _ in range(30):
        f = api("GET", f"/api/v1/files/{f['id']}")
        if (f.get("data") or {}).get("content"):
            break
        time.sleep(2)
    return {"type": "file", "file": f, "id": f["id"], "name": nom, "status": "uploaded"}


def discuter(modele, demande, outils=(), delai=600, joints=()):
    """→ (réponse, sources, fichiers, durée)"""
    uid, aid = str(uuid.uuid4()), str(uuid.uuid4())
    joints = list(joints)
    messages = {uid: {"id": uid, "parentId": None, "childrenIds": [aid], "role": "user", "content": demande, "timestamp": int(time.time()), "models": [modele],
                      **({"files": joints} if joints else {})},
                aid: {"id": aid, "parentId": uid, "childrenIds": [], "role": "assistant", "content": "", "model": modele, "timestamp": int(time.time())}}
    cid = api("POST", "/api/v1/chats/new", {"chat": {"title": "Essai Hibou", "models": [modele], "messages": list(messages.values()),
                                                     "history": {"currentId": aid, "messages": messages}}})["id"]
    t0 = time.time()
    api("POST", "/api/chat/completions", {"model": modele, "stream": True, "tool_ids": list(outils), "chat_id": cid, "id": aid,
                                          "session_id": sio.get_sid(), "parent_id": uid,
                                          "messages": [{"role": "user", "content": demande, **({"files": joints} if joints else {})}],
                                          "features": {}, "background_tasks": {}, **({"files": joints} if joints else {})})
    while time.time() - t0 < delai and aid not in fins:
        time.sleep(2)
    duree = time.time() - t0
    time.sleep(3)
    rep = api("GET", f"/api/v1/chats/{cid}")["chat"]["history"]["messages"][aid]
    return (rep.get("content") or "").strip(), rep.get("sources") or [], rep.get("files") or fichiers.get(aid, []), duree


def essai_chat(libelle, modele, demande, sources=False, outils=(), delai=600, joints=()):
    if modele not in visibles:
        resultat("attention", libelle, f"modèle {modele} absent")
        return None
    try:
        texte, src, fich, duree = discuter(modele, demande, outils, delai, joints)
    except Exception as e:  # noqa: BLE001 — chaque contrôle est indépendant
        resultat("echec", libelle, f"{e.__class__.__name__}: {str(e)[:120]}")
        return None
    if not texte and not fich:
        resultat("echec", libelle, f"aucune réponse en {duree:.0f} s")
    elif sources and not src:
        resultat("attention", libelle, f"réponse sans source en {duree:.0f} s")
    else:
        resultat("ok", libelle, f"{duree:.0f} s" + (f", {len(src)} source(s)" if sources else ""))
    return texte, src, fich


essai_chat("Chat (modèle de rédaction)", "hibou-documentation", "Réponds seulement par le mot : bonjour.", delai=300)
essai_chat("Réponse sourcée sur la documentation", "hibou-documentation", "Comment une page arrive-t-elle dans la documentation Hibou ?", sources=True)
if "hibou-securite" in visibles:
    essai_chat("Réponse sourcée sur la base sécurité", "hibou-securite", "Que recommande l’ANSSI pour les mots de passe ? Réponds en deux phrases.", sources=True)
code = uuid.uuid4().hex[:6].upper()
try:  # document joint au message : son texte doit parvenir au modèle
    texte, _, _, duree = discuter("hibou-documentation", "Quel est le code de vérification indiqué dans le fichier joint ? Réponds seulement par ce code.",
                                  delai=300, joints=[joindre("essai-hibou.txt", f"Note d’essai Hibou.\nCode de vérification : {code}\n")])
    resultat("ok" if code in texte else "echec", "Fichier joint lu par le modèle", f"{duree:.0f} s" if code in texte else "le code du fichier n’est pas dans la réponse")
except Exception as e:  # noqa: BLE001
    resultat("echec", "Fichier joint lu par le modèle", f"{e.__class__.__name__}: {str(e)[:120]}")
r = essai_chat("Export d’un document (PDF)", "hibou-documentation",
               "Exporte en PDF un document intitulé « Essai Hibou » contenant la phrase : Essai automatique réussi.", outils=["exporter_document"])
if r is not None:
    fich = r[2]
    if fich:
        fid = fich[0].get("id") or (fich[0].get("file") or {}).get("id")
        req = urllib.request.Request(f"{U}/api/v1/files/{fid}/content", headers={"Authorization": f"Bearer {TOK}"})
        with urllib.request.urlopen(req, timeout=60) as x:
            debut = x.read()[:5]
        resultat("ok" if debut == b"%PDF-" else "echec", "Téléchargement du document exporté", "PDF valide" if debut == b"%PDF-" else f"début {debut!r}")
    else:
        resultat("attention", "Téléchargement du document exporté", "le modèle n’a pas appelé l’outil d’export")
sio.disconnect()


# ─── OpenCode : connexion unique, instance personnelle ─────────────────────
t = time.time()
url, html = page(f"https://code.{DOMAINE}/oauth2/start?rd=%2F")
if "/login/oauth/grant" in html:
    champs = dict(re.findall(r'name="(_csrf|client_id|state|scope|nonce|redirect_uri|granted)" value="([^"]*)"', html))
    champs["granted"] = "true"
    url, html = page(f"{FORGE}/login/oauth/grant", champs)
if urllib.parse.urlsplit(url).netloc == f"code.{DOMAINE}" and "Pas d’espace OpenCode" in html:
    # Le compte d’essai passe la connexion et le contrôle d’équipe, mais n’a pas d’instance : réponse attendue.
    resultat("ok", "Connexion à OpenCode par Forgejo", f"{time.time() - t:.1f} s, droits vérifiés")
elif urllib.parse.urlsplit(url).netloc == f"code.{DOMAINE}" and "oauth2" not in urllib.parse.urlsplit(url).path and "<html" in html.lower():
    resultat("ok", "Connexion à OpenCode par Forgejo", f"{time.time() - t:.1f} s")
else:
    resultat("echec", "Connexion à OpenCode par Forgejo", f"arrivé sur {urllib.parse.urlsplit(url).netloc}{urllib.parse.urlsplit(url).path}")


# ─── Supervision : connexion unique à Grafana ──────────────────────────────
t = time.time()
url, html = page(f"https://supervision.{DOMAINE}/login/generic_oauth")
if "/login/oauth/grant" in html:
    champs = dict(re.findall(r'name="(_csrf|client_id|state|scope|nonce|redirect_uri|granted)" value="([^"]*)"', html))
    champs["granted"] = "true"
    url, html = page(f"{FORGE}/login/oauth/grant", champs)
moi = None
try:
    with op.open(f"https://supervision.{DOMAINE}/api/user", timeout=30) as r:
        moi = json.loads(r.read())
except urllib.error.HTTPError:
    pass
if moi and moi.get("login"):
    resultat("ok", "Connexion à Grafana par Forgejo", f"{time.time() - t:.1f} s")
else:
    resultat("echec", "Connexion à Grafana par Forgejo", f"arrivé sur {urllib.parse.urlsplit(url).path}")


# ─── Chaîne de documentation ───────────────────────────────────────────────
horodatage = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
branche, chemin = f"essai/{horodatage}", f"docs/essais/essai-{horodatage}.md"
contenu = f"""---
modele: procedure
titre: Essai automatique {horodatage}
---

# Essai automatique {horodatage}

## Objet

Vérifier la chaîne de documentation de Hibou.

## Prérequis

- Aucun.

## Étapes

1. Ouvrir une pull request.
2. Attendre le runner.

## Vérification

Le runner valide la page.

## Retour arrière

Fermer la pull request.
"""
pr = None
try:
    forgejo("POST", "/repos/hibou/hibou-docs/branches", {"new_branch_name": branche, "old_branch_name": "main"})
    forgejo("POST", f"/repos/hibou/hibou-docs/contents/{chemin}", {"branch": branche, "message": "Essai automatique Hibou",
                                                                    "content": base64.b64encode(contenu.encode()).decode()})
    pr = forgejo("POST", "/repos/hibou/hibou-docs/pulls", {"head": branche, "base": "main", "title": f"Essai automatique {horodatage}",
                                                          "body": "Ouverte et fermée par « hibou essai ». Rien à faire."})
    resultat("ok", "Pull request de documentation", f"n° {pr['number']}")
    t0, etat = time.time(), "pending"
    while time.time() - t0 < 600 and etat in ("pending", ""):
        time.sleep(10)
        etat = forgejo("GET", f"/repos/hibou/hibou-docs/commits/{pr['head']['sha']}/status").get("state") or ""
    resultat({"success": "ok", "pending": "echec", "": "echec"}.get(etat, "echec"), "Runner de documentation",
             f"{etat or 'aucun statut'} en {time.time() - t0:.0f} s")
    t0, avis = time.time(), []
    while time.time() - t0 < (900 if not SANS_DEV else 120) and not avis:
        time.sleep(15)
        avis = [a for a in forgejo("GET", f"/repos/hibou/hibou-docs/pulls/{pr['number']}/reviews") if a["user"]["login"] == "hibou-relecteur"]
    if not avis:
        resultat("echec", "Relecture automatique", "aucun avis de hibou-relecteur")
    elif "impossible" in (avis[0].get("body") or ""):
        resultat("attention" if SANS_DEV else "echec", "Relecture automatique", "relecteur sans serveur dev : avis d’impossibilité posté")
    else:
        resultat("ok", "Relecture automatique", f"avis en {time.time() - t0:.0f} s")
    # Notifications d’équipe : la PR doit apparaître dans le sujet hibou-pr ; le sujet des alertes reste aux administrateurs.
    url, html = page(f"https://alertes.{DOMAINE}/oauth2/start?rd=%2F")
    if "/login/oauth/grant" in html:
        champs = dict(re.findall(r'name="(_csrf|client_id|state|scope|nonce|redirect_uri|granted)" value="([^"]*)"', html))
        champs["granted"] = "true"
        page(f"{FORGE}/login/oauth/grant", champs)
    _, flux = page(f"https://alertes.{DOMAINE}/hibou-pr/json?poll=1&since=30m")
    vus = [json.loads(l).get("title", "") for l in flux.splitlines() if l.startswith("{")]
    trouve = any(f"#{pr['number']}" in t and "hibou-docs" in t for t in vus)
    resultat("ok" if trouve else "echec", "Notification « PR à relire » (ntfy)", f"{len(vus)} message(s) récents" if trouve else "absente du sujet hibou-pr")
    try:
        op.open(f"https://alertes.{DOMAINE}/hibou/json?poll=1", timeout=30).read()
        resultat("echec", "Alertes réservées aux administrateurs", "le sujet hibou est lisible par un compte doc/dev")
    except urllib.error.HTTPError as e:
        resultat("ok" if e.code == 403 else "echec", "Alertes réservées aux administrateurs", f"HTTP {e.code}")
except urllib.error.HTTPError as e:
    resultat("echec", "Chaîne de documentation", f"HTTP {e.code} {e.read()[:150].decode(errors='replace')}")
finally:
    try:
        if pr:
            forgejo("PATCH", f"/repos/hibou/hibou-docs/pulls/{pr['number']}", {"state": "closed"})
        forgejo("DELETE", f"/repos/hibou/hibou-docs/branches/{urllib.parse.quote(branche, safe='')}")
    except urllib.error.HTTPError:
        pass
