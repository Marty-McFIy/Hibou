# Journal des corrections — Hibou 0.9.0

Format : symptôme, cause, diff, test de preuve. Secrets masqués (`***`).

## A1 — Profil « ≥ 4 Go » absent (amélioration)

- Symptôme : une carte de 4 Go est sous le plus petit profil (12 Go) ; le menu affiche « Attention » et propose un profil qui ne tient pas.
- Ajout : `dev:5` (Qwen3.5 4B UD-Q4_K_XL, contexte 16k, + complétion Qwen2.5-Coder 1.5B Q8, groupe exclusif) et `doc:4`
  (Qwen3.5 4B UD-Q4_K_XL + mmproj F16, contexte 8k, embedding sur le processeur). Seuils `PROFILS_*_GO` étendus à 4.
- Dépôts et fichiers vérifiés sur Hugging Face le 2026-11-20.
- Test : `./hibou autotest` (22 lignes de modèles). Tenue en VRAM : à mesurer (phase 3).

## A1-bis — Profil doc ≥ 4 Go : le modèle meurt faute de mémoire vidéo dès un prompt long (évaluation à 0 token/s)

- Symptôme : évaluation doc lancée par `installer doc` : 12 tâches, toutes « 0.0 s », « 0.0 tokens/s », réponses brutes `[erreur API : HTTP Error 502]` (puis 500).
  L'évaluateur note quand même ces réponses vides (doc 32 %, vision 12 %) : scores sans valeur (voir N4).
- Cause (sortie de llama-server capturée par un script temporaire) : `CUDA error: out of memory` dans `ggml_cuda_mul_mat_q` à la lecture du premier prompt de l'évaluation ;
  dès le chargement : `failed to fit params to free device memory` et tampon de vision de 223 Mio refusé. Modèle 2,9 Go + projecteur vision 0,67 Go + cache 8k + tampons > 4 Go.
  Un prompt court passe (23,4 tokens/s), d'où un serveur « en ligne » pour le contrôle de santé.
- Diff : profil `doc:4` : `--no-mmproj-offload` (projecteur vision sur le processeur ; la vision reste disponible).
- Test (manuel, même conteneur) : chargé 3 125 Mio, prompt de 4 437 tokens : 774 tokens/s en lecture, 22 tokens/s en génération, pic 3 147 Mio, serveur vivant.
  `mettre-a-jour doc` puis évaluation : voir mesures.
- Évaluation après correctif (22:57 UTC) : vision **100 %** (4/4, 40 à 57 s par image, 17,3 tokens/s), doc **74 %** (5/8 à 100 %, 21,7 tokens/s).
  Les 3 échecs (02, 05, 07) : ~362 s chacun, réponse vide. Tâche 02 rejouée : `finish_reason: length`, `content` vide, 28 660 caractères de `reasoning_content`
  (7 819 tokens de réflexion en boucle : « Okay, ready. Wait, I need to check… »).
- Diff n° 2 : profil `doc:4` : `--reasoning-budget 0`. Test (tâche 02, serveur manuel) : `finish_reason: stop`, document complet conforme au template, 470 tokens, 22,9 tokens/s.
- Évaluation après `mettre-a-jour doc` n° 5 (23:59 UTC, sans raisonnement) : doc **93 %** (6/8 à 100 %, 04 et 05 : une section manquante), 22,1 tokens/s ;
  vision **100 %** (15 à 21 s par image). Durée totale ~5 min (contre ~40 min). **Prouvé.**
- Profil `dev:5` : charge ensemble Qwen3.5 4B (2,9 Go + contexte 16k) et la complétion 1.5B Q8 (~1,6 Go) : ne peut pas tenir dans 4 Go.
  Diff : complétion `fim` en `-ngl 0` (processeur). Test : `installer dev` (voir mesures).

## B1 — Bruit `debconf` dans la sortie de `telecharger` (affichage)

- Symptôme : plusieurs lignes `debconf: unable to initialize frontend …` entre les étapes, hors charte.
- Cause : `apt-get install` dans les conteneurs sans `DEBIAN_FRONTEND=noninteractive`.
- Diff : `export DEBIAN_FRONTEND=noninteractive` ajouté en tête des deux `bash -euc` (paquets Ubuntu et Proxmox).
- Test : passage complet n° 2 (2026-11-20, 21:52) : 0 ligne `debconf` (301 paquets Ubuntu, 50 Proxmox). **Prouvé.** Restent les 2 lignes N1.

## B2 — `telecharger` s'arrête sans message à la première image (premier passage)

- Symptôme : la sortie s'arrête sur « Images Docker / gpu-exporter », code de sortie non nul, aucun message d'erreur. `images/` ne contient que `digests.txt`.
- Cause : `enregistrer()` fait `avant=$(awk … digests.precedent 2>/dev/null)`. Au premier passage le fichier n'existe pas, `awk` sort en code 2, et `set -e` tue le script (redirection de l'erreur comprise).
- Diff : `avant=""` puis `[[ -f digests.precedent ]] && avant=$(awk …)` (pas de `|| true`).
- Test : relancer `telecharger` sur un bundle neuf, l'étape images doit se terminer.

## B3 — « La garder » : `HIBOU_DOMAINE: unbound variable`

- Symptôme : relancer `telecharger` sur un bundle existant, choisir 1 « La garder » : `./hibou: line 752: HIBOU_DOMAINE: unbound variable`.
- Cause : `configurer_bundle` retourne sans relire `$bundle/config.env`. Le `source` du début du script lit celui du dossier du script, pas celui du bundle.
- Diff : `[[ "$garde" == 1 ]] && { source "$s/config.env"; return 0; }`.
- Test : second passage de `telecharger` (phase 1, étape 5).
  **Prouvé** (passe images n° 3, 20:21) : « La garder » puis étapes suivantes sans erreur.

## B4 — Les images construites localement sont réécrites à chaque passage (mise à jour)

- Symptôme : au second passage, `opencode`, `docs-builder`, `priorite`, `relecteur`, `miroir` sont réenregistrées (plusieurs centaines de Mo réécrits, puis recopiées par `mettre-a-jour`).
- Cause : `construire()` enregistrait l'Id de l'image construite. Sans cache Docker garanti, une reconstruction identique change d'Id.
- Diff : l'identifiant devient l'empreinte des entrées (fichiers du contexte + Id de l'image de base du `FROM`) ; si `.tar.zst` présent et empreinte identique dans `digests.precedent`, pas de reconstruction.
- Test : `HIBOU_PARTIES=images`, passe n° 3 (20:21) : les 18 images « inchangée », aucun `.tar.zst` réécrit. **Prouvé.**

## B5 — `installer forge` : apt ne lit pas la source locale dans la VM (bloquant)

- Symptôme : étape « Docker, DNS, heure » : `E: Failed to fetch file:/home/hibou/hibou-bundle/apt/ubuntu/./Packages  File not found`, puis « L’installation dans la VM s’est arrêtée ».
- Cause : `/home/hibou` est en 0750 (défaut Ubuntu 26.04). apt décompresse `Packages.gz` sous l'utilisateur `_apt` → `Permission denied` ; le message final ne cite que la dernière variante essayée (`Packages`).
- Diff : `source_locale()` ajoute `-o APT::Sandbox::User=root` à `APT_HIBOU` (dépôt local de confiance ; droits du dossier personnel inchangés).
- Test : dans la VM forge, `apt-get update` avec ces options : rc=0, `docker-ce` candidat 5:29.10.0. `autotest` OK. Script reporté dans les bundles (hôte et VM, `SHA256SUMS` à jour). Relance n° 2 de `installer forge` : « Docker, DNS, heure » passe (Docker installé, DNS et heure actifs sur <adresse>). **Prouvé.**

## B6 — `installer forge` : clé SSH de l'agent refusée (bloquant, première installation)

- Symptôme : étape « Compte de l’agent hibou-dev » : `WARNING: UNPROTECTED PRIVATE KEY FILE! Permissions 0644 for '/srv/hibou/ssh/id_ed25519'`, puis « L’installation dans la VM s’est arrêtée ».
- Cause : la clé est écrite juste après `umask 022` (retour à la normale après `opencode.env`), donc en 0644 ; `ssh-keygen -y` refuse de la lire. Le `chmod 600` n'arrive qu'à la fin de l'étape.
- Diff : `chmod 600 /srv/hibou/ssh/id_ed25519` juste après le `base64 -d` (corrige aussi un fichier déjà présent, que `>` laisse en 0644).
- Test : `autotest` OK ; relance `installer forge` n° 4 : « hibou-dev créé, membre de dev, clé SSH déposée ». **Prouvé.**

## B7 — Miroir : PyPI jamais publié dans Forgejo, et mot de passe dans le journal (bloquant + sécurité)

- Symptôme : « Miroir de dépendances vers Forgejo » : `twine … does not have support for the following features: --skip-existing`, traceback Python, puis quand même « Fait Paquets publiés ».
  La traceback (`CalledProcessError`) recopie la ligne de commande : **mot de passe administrateur en clair** dans la sortie d'installation.
- Cause : Forgejo refuse `--skip-existing` ; le mot de passe passe en `-p` ; `main()` laisse remonter `CalledProcessError` (même risque pour le jeton dans l'URL du `git push`) ; `importer_miroir` affiche « Fait » après l'échec.
- Diff (`hibou-miroir.py`) : un `twine upload` par fichier, 409/« already exists » compté comme déjà présent, comme pour npm ; identifiants par `TWINE_USERNAME`/`TWINE_PASSWORD` ;
  `main()` attrape `CalledProcessError` et n'affiche que la commande passée par `redact()`. (`hibou`) : « Fait » seulement si le push a réussi.
- Test : `telecharger` `HIBOU_PARTIES=miroir` (VM, 2 min 34 s) : seule `miroir.tar.zst` réécrite ; recopie vers l'hôte : 193 Mo en 2 s ;
  `mettre-a-jour forge` n° 5 : 1 image rechargée (miroir), « pypi : 5 publiés », « npm : 1 publiés », échec git affiché avec `***` à la place du jeton. **Prouvé.**

## B8 — Base « Hibou · Templates » vide pour toujours si forge est installée avant doc (ordre documenté)

- Symptôme : `installer forge` : 5 × `curl: (22) … error: 400` à « Open WebUI : outil, modèles et templates ».
- Cause : l'ajout d'un fichier à une base déclenche les embeddings, servis par la VM doc pas encore installée (`Connect call failed` dans les journaux d'Open WebUI).
  La base n'était remplie qu'à sa création : aux passages suivants elle existe, vide, et n'est plus jamais remplie.
- Diff : base remplie tant qu'elle est vide (comptée par `GET /knowledge/{id}/files` → `total` : `GET /knowledge/{id}` ne renvoie plus `files` dans cette version d'Open WebUI) ;
  au premier refus, arrêt et note claire (« après installer doc, relance hibou mettre-a-jour forge »), sans les 5 erreurs `curl`.
- Test : `mettre-a-jour forge` n° 6 (doc absente) : une seule note claire. Après doc et B15 : n° 11 : base remplie (5 fichiers) ;
  n° 12 : note « vide » affichée à tort (comptage par `.files`, toujours vide) → comptage par `/files` ; n° 13 : aucune note, 5 fichiers. **Prouvé.**

## B9 — Miroir : le dépôt git copié dans forge n'est plus un dépôt (« not a git repository »)

- Symptôme : `ÉCHEC (128) : git -C /m/git/Hello-World.git … push` ; `fatal: not a git repository`.
- Cause : `copier_vers_vm` ne donne à rsync que les fichiers (`find mirror -type f`). Les dossiers vides `refs/`, `refs/heads`, `refs/tags` d'un dépôt nu (références dans `packed-refs`) ne sont pas recréés ; sans `refs/`, git ne reconnaît pas le dépôt.
- Diff : `find mirror -type f -o -type d -empty`.
- Test : `mettre-a-jour forge` n° 6 : `refs/heads`, `refs/tags` présents dans la VM, `git rev-parse --is-bare-repository` = true. **Prouvé.** (Échec suivant : B10.)

## B10 — Miroir : git refuse le dépôt (« detected dubious ownership »)

- Symptôme : après B9, `fatal: detected dubious ownership in repository at '/m/git/Hello-World.git'`.
- Cause : le conteneur `miroir` tourne en root, le dépôt monté appartient à `hibou` (uid 1000) ; git ≥ 2.35.2 refuse.
- Diff (`hibou-miroir.py`) : `git -c safe.directory=<ce dépôt> …` (exception limitée au dépôt, rien de global).
- Test : sur l'hôte, dépôt possédé par uid 1000, git root : refusé sans l'option, accepté avec. Chemin complet : `telecharger` miroir (2 min 30 s), recopie 193 Mo en 2 s, `mettre-a-jour forge` n° 7 :
  `[new branch] master`, `octocat-patch-1`, `test` poussées ; « image publiée : forge.hibou.lan/hibou/alpine:3.20 » ; « Fait Paquets publiés ». **Prouvé.**

## B11 — `installer doc` : apt refuse d'installer le pilote (« Packages need to be removed but remove is disabled »)

- Symptôme : étape « Pilote NVIDIA 620.70.06, Docker, NVIDIA Container Toolkit » : `E: Packages need to be removed but remove is disabled`, puis « apt refuse l’installation ».
- Cause : l'image cloud installe le noyau par `linux-virtual` / `linux-headers-virtual` (7.0.0-43). Le bundle apporte `linux-generic` 7.0.0-44 mais pas les « virtual » 44 ;
  `linux-headers-virtual` 43 exige `linux-headers-generic (= 43)` : apt doit le retirer, `--no-remove` refuse. Se reproduira en production dès que le noyau du bundle dépasse celui de l'image.
- Diff (`installer_gpu`) : si `linux-virtual` est installé, `apt-get remove linux-virtual linux-headers-virtual linux-image-virtual` (métapaquets vides) avant `apt_hibou`. `--no-remove` garde son rôle pour le reste.
- Test : simulation dans la VM doc : seuls ces 3 métapaquets retirés, puis plus aucun `Remv` à l'installation. `autotest` OK. `installer doc` n° 2 : « Module NVIDIA 620.70.06 compilé pour le noyau 7.0.0-44-generic ». **Prouvé.**

## B12 — Fin de `installer doc` : `pveum realm modify` refuse `--username-claim` (rc=255, évaluation jamais lancée)

- Symptôme : après « Serveur doc démarré » et « J’ai terminé le rôle doc (phase suite) » : `Unknown option: username-claim`, `400 unable to parse option`, rc=255.
  `set -e` arrête le script avant le contrôle de l'API et le lancement de l'évaluation.
- Cause : forge a déjà créé le domaine `forgejo` sur l'hôte, `realm_proxmox` passe donc par `realm modify`, qui n'accepte pas `--username-claim` (création seulement). Idem sur un cluster (domains.cfg partagé) ou à chaque relance d'un rôle.
- Diff : `--username-claim username` passé seulement à `realm add`.
- Test : `pveum realm modify forgejo --autocreate 1 --comment …` : OK, `username-claim username` conservé. `installer doc` n° 3 : « Proxmox : connexion par Forgejo active » sans erreur. **Prouvé.**

## B13 — VM doc : le pare-feu Hibou bloque `localhost` ; le contrôle de l'API boucle ~2 h 15 min

- Symptôme : après « Proxmox : connexion par Forgejo active », 60 × `curl: (28) Failed to connect to localhost port 8080 after 134 s`. Les conteneurs tournent (`llama-swap` healthy).
- Cause : la chaîne `entree` (hook prerouting) jette tout accès aux ports 8080/8188/9100/9835 dont la source n'est pas forge. Le trafic local repasse par `lo` en prerouting
  (source 127.0.0.1, ou ::1 en IPv6) : jeté sans réponse, d'où 134 s par essai. Le trafic entre conteneurs (`priorite` → `llama-swap:8080`) n'était pas touché (vérifié : 200 avant correctif).
- Diff (`pare_feu`) : `iifname "lo" accept` en tête de chaîne.
- Test : à chaud dans la VM doc : `curl localhost:8080/health` → OK ; depuis l'hôte : toujours bloqué ; depuis forge : OK. Syntaxe `nft -c` OK.
  L'installation n° 3 en cours a fini grâce au correctif à chaud. Preuve par le script : `mettre-a-jour doc` n° 5 (voir B14). **Prouvé.**

## B14 — `mettre-a-jour` ne réapplique pas le pare-feu (B13 n'atteint pas une installation existante)

- Symptôme : `mettre-a-jour doc` n° 4 : de nouveau `curl: (28) … localhost port 8080 after 134 s` ; règle `lo` absente de `/etc/hibou/pare-feu.nft`.
- Cause : en mise à jour, si `Packages.gz` n'a pas changé, l'étape « socle » est sautée, et `pare_feu` avec elle.
- Diff (`installer_gpu`) : socle sauté → `pare_feu` appelé quand même (hors phase `suite`).
- Test : `mettre-a-jour doc` n° 5 : « Paquets inchangés : socle sauté », puis « Ports … ouverts à forge seulement », puis « API du serveur doc en ligne » au premier essai ; rc=0 en 1 min 48 s. **Prouvé** (B13 et B14).

## B15 — Base « Hibou · Templates » toujours vide : llama-swap refuse les embeddings en rafale (429)

- Symptôme : après `installer doc`, `mettre-a-jour forge` affiche encore « Base Templates vide » ; Open WebUI : `ClientResponseError: 429 Too Many Requests` sur `/v1/embeddings`.
- Cause (capture réseau forge → doc) : réponse de llama-swap `{"error":{"message":"Too many requests","type":"rate_limit_error","code":"concurrency_limit"}}`.
  llama-swap limite par défaut chaque modèle à 10 requêtes simultanées ; Open WebUI en envoie davantage en indexant. Preuve : 40 requêtes simultanées → 10 × 200, 30 × 429.
  (Essayé d'abord, sans effet seul : `RAG_EMBEDDING_BATCH_SIZE=16`, `RAG_EMBEDDING_CONCURRENT_REQUESTS=4` dans l'environnement d'Open WebUI ; gardés, ils réduisent le nombre d'appels.)
- Diff : `config_llama_swap` : `concurrencyLimit: 64` pour le modèle d'embeddings (le serveur met lui-même les requêtes en file).
- Test : réglage à la main : 40 simultanées → 40 × 200 ; retiré → 10 × 200, 30 × 429. `mettre-a-jour doc` n° 5 puis `mettre-a-jour forge` n° 11 : base Templates remplie (5 fichiers), plus aucun 429. **Prouvé.**

## B16 — Synchronisation de « Hibou · Documentation » : 400 DUPLICATE_CONTENT dès le deuxième passage

- Symptôme : `mettre-a-jour forge` : traceback de `outils/synchroniser_owui.py` (`HTTP Error 400`), « Clé du runner ou première synchronisation refusée » ; Open WebUI : `DUPLICATE_CONTENT`.
- Cause : le script vide la base en supprimant `base["files"]`, mais `GET /knowledge/{id}` ne renvoie plus ce champ ; rien n'est supprimé, la même page est renvoyée et refusée.
  Même effet à chaque fusion dans hibou-docs (runner) : synchronisation en échec, et une page modifiée s'ajouterait sans retirer l'ancienne.
- Diff (`amorces/hibou-docs/outils/synchroniser_owui.py`) : `POST /knowledge/{id}/reset` (fichiers et vecteurs) avant l'envoi.
- Test : `mettre-a-jour forge` n° 12 et 13 : plus de traceback, « Hibou · Documentation » : 1 fichier. **Prouvé.**
- Reste : le dépôt hibou-docs déjà créé dans Forgejo garde l'ancien `outils/synchroniser_owui.py` (amorcé à l'installation) ; le runner l'utilisera jusqu'à une PR qui le remplace. Les nouvelles installations ont la version corrigée.

## B17 — OpenCode compacte la conversation à chaque tour (agent inutilisable sur le profil dev ≥ 4 Go)
- Symptôme : test par l'API de la page web (« nouveau projet compteur-mots, poussé dans Forgejo ») : 172 messages en 947 s, aucun fichier, aucun dépôt.
  Un tour sur deux est un résumé « ## Objective… » ; l'agent oublie ce qu'il vient de faire, redemande la marche à suivre, finit par réclamer un mot de passe.
- Cause : `config_opencode` déclare `output: 16384` pour tout contexte < 128k. Sur `dev:5` (contexte 16 384), OpenCode réserve toute la fenêtre à la sortie :
  place utile nulle, compaction après chaque appel. Le prompt système et les outils d'OpenCode pèsent déjà ~8 300 tokens (relevé par tour : 8 368 en entrée).
- Diff : sortie réservée = contexte / 4 (32 768 au-delà de 128k, inchangé) ; `dev:5` passe de 16k à 32k de contexte.
- Test VRAM (à la main, VM dev) : contexte 32k, prompt de 27 296 tokens : 42,7 s (680 tokens/s en lecture), pic 3 675 Mio sur 4 096, aucune erreur mémoire.
- Autres constats du même test (modèle 4B, pas le script) : tente `opencode.ai` (hors ligne), invente `git.forge.hibou.lan` au lieu de `$FORGEJO_URL`
  (erreur TLS), renomme le projet en anglais.

## B18 — Agent OpenCode hors ligne : pas de pytest, venv commité, tentatives vers Internet
- Constat (test web n° 2, après B17) : chaîne complète en 10 min 41 s, 2 compactions seulement : dépôt `compteur-mots` créé, cloné dans `/workspace/compteur-mots`,
  branche `agent/compteur-mots`, commit, push, PR n° 1 ouverte. Mais : `pytest` introuvable (ni dans l'image, ni dans le miroir, qui ne contient que l'exemple `requests`) ;
  l'agent essaie `pip --break-system-packages`, `apt-get`, pypi.org, files.pythonhosted.org (une dizaine de tours perdus), crée `venv/` dans le projet,
  `git add -A` puis commit : **le dépôt contient tout `venv/`** (pip compris) ; il supprime `venv/` après le commit, sans le retirer de l'historique.
- Cause : image `opencode` sans outil de test ; `AGENTS.md` muet sur le hors-ligne, le miroir et `.gitignore`.
- Diff : `python3-pytest` dans l'image `opencode` ; `AGENTS.md` : section « Hors ligne » (Internet absent, miroir pip/npm déjà configuré, pytest présent,
  `.venv/` et `__pycache__/` dans `.gitignore` avant le premier `git add`, relire `git status` avant chaque commit).
- `mettre-a-jour` ne rejouait pas `consignes_agent` (seulement dans `configurer`, sauté en mise à jour) : une nouvelle version des consignes n'atteignait
  jamais une installation existante. Diff : `consignes_agent` appelé aussi en mise à jour. Test : `mettre-a-jour forge` n° 16 : section présente dans le conteneur.
- Terminal n° 1 (interface texte `opencode` dans le conteneur, projet `convertisseur-temperatures`) : 4 min 40 s ; dépôt, clone, branche, **21 tests pytest réussis**,
  commit propre (3 fichiers, aucun `venv/`), push. Mais adresse inventée (`api.forge.hibou.lan`) au premier essai et **pas de PR** : JSON du `curl` cassé (« no URL specified »).
- Diff n° 2 : commandes `forgejo-nouveau-depot <projet>` et `forgejo-pr "<titre>" "<description>"` dans l'image (JSON par `jq`, adresse et organisation lues
  dans l'environnement) ; consignes : une seule adresse de Forgejo, ces deux commandes au lieu des `curl`.
- Web n° 3 (`compteur-lignes`) : code et tests faits d'abord dans un dossier créé à la main (`git init`), puis `forgejo-nouveau-depot` : dépôt créé,
  clone refusé (dossier existant), puis 409 à chaque appel ; le 4B répète la même commande ~90 fois (6 min). Ni push ni PR.
- Diff n° 3 : `forgejo-nouveau-depot` : dossier déjà cloné → rien à faire ; dossier local → mis de côté (`<projet>.avant-depot`), clone, fichiers recopiés ;
  consignes : commencer par cette commande ; deux échecs de suite → changer d'approche.
  Test à la main dans le conteneur sur le cas exact : rc=0, fichiers recopiés ; second appel : « Déjà cloné » ; `forgejo-pr` : branche poussée, PR n° 1 ouverte.

## B19 — Documents publiés par l'IA doc refusés par le runner (style Markdown)
- Constat : rédaction par `hibou-procedure` (doc ≥ 4 Go), publication par l'outil `publier_forgejo` : PR ouvertes dans hibou-docs (branche `redaction/…`, compte hibou-redac),
  mais le runner échoue : PR n° 1 : 2 erreurs (URL nue MD034, saut de ligne final MD047) ; PR n° 2 : 11 erreurs (blocs de code sans langage ni lignes vides, MD031/MD040, MD047).
- Cause : le prompt ne dit rien des règles de `markdownlint` ; un petit modèle ne les devine pas.
- Diff : `publier_forgejo` 0.2.0 : `normaliser()` avant publication (langage `text` et lignes vides autour des blocs de code, adresses nues entre chevrons,
  un seul saut de ligne final ; texte inchangé) ; prompt des 5 modèles : règle en une ligne. Fichier, générateur (`generer-amorces.py`) et `modeles-hibou.json` alignés.
- Test : les deux documents refusés, passés par `normaliser()` puis `markdownlint-cli2` du runner : 13 erreurs → 0.
  Page de chat (WebSocket, deux tours « rédige » puis « oui, publie-la ») : PR n° 3, runner **success** (« 0 issues », « Job succeeded »). **Prouvé.**

## B20 — `mettre-a-jour forge` ne remplace jamais le code de l'outil Open WebUI
- Symptôme : après B19 et `mettre-a-jour forge` n° 20, prompt à jour dans Open WebUI mais outil `publier_forgejo` toujours en 0.1.0.
- Cause : `amorcer_open_webui` ne crée l'outil que si un jeton est passé (installation) ; en mise à jour, rien (commentaire inversé : « mise à jour : outil et jeton déjà en place »).
- Diff : outil créé ou mis à jour (`/tools/id/publier_forgejo/update`) à chaque passage ; valves (jeton de hibou-redac) écrites seulement à l'installation.
- Test : `mettre-a-jour forge` n° 21 : `normaliser` présent dans l'outil, jeton conservé, dépôt `hibou/hibou-docs`. **Prouvé** (puis PR n° 3 ci-dessus).

## B21 — `mettre-a-jour forge` ne met jamais à jour « Documentation interne » ni les modèles techniques (erreur masquée)
- Symptôme : journal d'Open WebUI à chaque mise à jour : 8 × `POST /api/v1/models/create` → 401 ; table `model` : `hibou-documentation`, `qwen3-embedding`, `fim` figés à la date d'installation.
- Cause : Open WebUI répond 401 quand l'identifiant existe déjà ; ces trois créations finissaient par `|| true` (pas de mise à jour). Après un changement de profil doc, « Documentation interne » resterait branchée sur le modèle retiré.
- Diff : fonction `modele_owui` (création, sinon `/models/model/update?id=…`) pour les 8 modèles ; plus de `|| true` : un échec remonte en note (« Open WebUI n'a pas tout accepté »).
- Test : `mettre-a-jour forge` n° 22 : 8 × 401 puis 8 × `update` 200 ; les 8 lignes de `model` datées de la mise à jour. **Prouvé.**

## B22 — Agent dev : `main` non protégée dans les dépôts qu'il crée ; `.venv` à la racine de /workspace ; `rm -rf .git` seulement « à demander »
- Constats : `hibou-infra`, `hibou-docs` et `hibou-eval` sont protégés, mais pas les dépôts créés par `forgejo-nouveau-depot` (l'agent en est administrateur) ; seule la règle OpenCode `git push*main*` bloquait, et un `git push` nu depuis main passait.
  Essai web n° 4 : `.venv` de 25 Mo créé à la racine de /workspace avant le clone. Même essai : `rm -rf .git` proposé (permission « ask »).
- Diff : `forgejo-nouveau-depot` pose la même protection que les dépôts système, plus `apply_to_admins` (l'agent ne peut pas fusionner sa propre PR sans approbation), message clair si elle est refusée ;
  `AGENTS.md` : « Rien à la racine de /workspace… `cd /workspace/<projet>` avant toute autre commande » ; permissions : `rm -r… .git` refusé (4 motifs).
- Test : `mettre-a-jour forge` n° 22 : dépôt d'essai créé par la commande → protection `enable_push:false, required_approvals:1, apply_to_admins:true` ; `git push` nu depuis main : `pre-receive hook declined` ; second appel : « Déjà cloné ».
  Motifs simulés (dernière règle qui correspond) : `rm -rf .git`, `cd … && rm -rf .git`, `rm -rf /workspace/p/.git`, `rm -r .git/` refusés ; `rm -rf .venv`, `rm .gitignore`, `git rm -r --cached` restent « ask ».
  Non rejoué par le modèle lui-même (serveur dev arrêté pendant l'essai). **Prouvé** pour la protection.
- Constat utile : le jeton de l'agent reçoit 403 en suppression de dépôt.

## B23 — Relecteur muet quand il échoue
- Symptôme : aucune PR de hibou-docs n'a d'avis ; journal du relecteur : `échec de la relecture : <urlopen error [Errno 113] No route to host>` (il appelle le LLM de dev, arrêté pendant l'essai faute de seconde carte).
- Cause : l'échec n'est écrit que dans le journal du conteneur ; dans Forgejo, la PR semble « pas encore relue ».
- Diff : en cas d'échec, avis `COMMENT` « Relecture automatique impossible : … La relecture humaine reste nécessaire. » par `/reviews`
  (premier essai par `/issues/{n}/comments` : 403, l'équipe relecture n'a que `repo.code` et `repo.pulls` en lecture ; `/reviews` : 200).
- Test : `mettre-a-jour forge` n° 23, PR jetable n° 7 : avis de hibou-relecteur avec le message. **Prouvé.** L'avis réel (dev en marche) reste à voir.

## A2 — Profils au-delà de 4 Go : deux ne tiennent pas dans leur palier (tailles réelles sur Hugging Face, 2026-11-21)
- Simulation du menu (Entrée = profil conseillé) de 4 à 96 Go, une ou plusieurs cartes : chaque taille tombe sur le bon palier.
- Poids sur la carte (fichiers réels) : `dev:2` (≥ 48 Go) Qwen3-Coder-Next UD-Q4_K_XL = **49,6 Go** ; `doc:2` (≥ 24 Go) Gemma 4 26B UD-Q6_K_XL + mmproj = **24,5 Go**, avant le cache.
  `dev:3` (≥ 24 Go) : 27B Q4 + mmproj + complétion 3B = 21,9 Go + cache 64k : limite, à mesurer. `dev:4`/`doc:3` (≥ 12 Go) : 6 à 7,6 Go, confortables.
- Diff : `dev:2` Coder-Next en UD-Q3_K_XL (36,3 Go) ; `doc:2` Gemma en UD-Q4_K_XL (17 + 1,2 Go) ; libellés du menu alignés (dont `dev:5` : 32k, complétion sur le processeur).
  Complétion 7B (`dev:1`, `dev:2`) : motif `*q8_0*` → `*q8_0.gguf` : le dépôt contient le même modèle en un fichier et en trois morceaux, les deux étaient téléchargés (8 Go en double).
- Test : `autotest` (22 lignes). Non mesurable sur la machine d'essai (une carte de 4 Go) : à valider sur le premier serveur de 24 ou 48 Go.
- Non corrigé : `*mmproj*F16*` prend aussi `mmproj-BF16` (deux projecteurs téléchargés, ~0,7 à 1,2 Go) ; c'est le BF16 qui est chargé et validé à l'essai (processeur sans F16C) : changement non testé.

## B24 — Relecteur : le 4B répète la même remarque jusqu'à la limite (avis illisible, 3 min 22 s)
- Symptôme : PR piégée (`eval(input())`, dépôt `essai-relecture`) : la première remarque est juste (`eval()`, bloquant), puis « absence de gestion des retours d'erreur… » répétée ~130 fois jusqu'à `max_tokens` 4096.
- Cause : aucune pénalité de répétition, limite haute, consigne sans nombre maximal de remarques ; un petit modèle quantifié entre en boucle.
- Diff (`source_relecteur`) : consigne « Au plus 10 remarques, chacune une seule fois, les plus graves d'abord » ; `max_tokens` 2048, `presence_penalty` 1.0 ;
  paragraphes en double retirés ; mention « Avis coupé » si `finish_reason` = `length`.
- Test : mêmes réglages sur le même diff, 2 essais : 32 s / 667 tokens et 4 s / 77 tokens, `finish_reason: stop`. `mettre-a-jour forge` n° 24 puis nouveau commit sur la PR :
  avis en **13 s**, 3 remarques, `eval()` en premier (bloquant). **Prouvé.** Numéros de ligne approximatifs (limite du 4B).

## Contexte : ce qui se passe quand une conversation devient longue
- doc (Open WebUI → llama-server, contexte 8 192 sur `doc:4`) : **aucune compression**. Open WebUI renvoie tout l'historique à chaque message.
  Mesure directe : 7 781 tokens → réponse juste ; 10 371 tokens → `HTTP 400 exceed_context_size_error` (« request (10371 tokens) exceeds the available context size (8192 tokens) »).
  Pas de troncature silencieuse : la conversation devient inutilisable, il faut en ouvrir une nouvelle.
- dev (OpenCode, contexte 32 768 sur `dev:5`) : **compaction automatique** quand l'historique approche de la limite (contexte − sortie réservée = 24 576) ;
  OpenCode fait résumer la session par le modèle et repart du résumé (B17 : 2 compactions sur un essai de 10 min).

## B25 — Agent dev : push vers un dépôt inexistant accepté (dépôt sans main ni protection) ; pip ne trouve pas les dépendances compilées
- Constat (essai web n° 5, projet `verif-nombre`) : l'agent ignore `forgejo-nouveau-depot`, fait `git init`, `git remote add`, `git push -u origin agent/verif-nombre` :
  **le dépôt naît par le push** (`ENABLE_PUSH_CREATE_ORG=true`), sans `main` ni protection ; `forgejo-pr` répond 404 (base `main` absente) ; ~60 tours de contournements (curl inventés, `push --force`…).
  `pip install requests` : `requests` trouvé dans le miroir, `charset-normalizer` « from versions: none » alors qu'il est publié.
- Causes : création par push activée (mécanisme d'origine, remplacé par `forgejo-nouveau-depot`) ; le miroir ne couvrait que Python 3.12 (choix du menu d'essai),
  l'agent tourne en **Python 3.11** (`node:22-bookworm-slim`, Debian 12) : la roue cp312 ne s'installe pas.
- Diff : `ENABLE_PUSH_CREATE_ORG=false` ; `hibou-miroir.py` crée ses dépôts git par l'API (409 = déjà là) avant le push ; `telecharger` ajoute toujours 3.11 aux versions du miroir (note affichée).
- Test : `telecharger` miroir (2 min 37 s, roue `cp311` ajoutée) ; `mettre-a-jour forge` n° 25 : pypi « 2 publiés, 5 déjà présents », Hello-World poussé, aucune erreur.
  Dans le conteneur de l'agent : `pip install requests` dans un `.venv` → OK (`charset_normalizer` importé) ; `npm install is-number` → OK ; push vers `hibou/depot-fantome` → refusé (« the repository exists ? »). **Prouvé.**

## B26 — L'agent affiche son jeton Forgejo dans la conversation
- Constat (même essai) : `echo $FORGEJO_TOKEN` demandé par l'agent, accepté par le pilote de test : jeton dans l'historique de la session (visible par tous les utilisateurs d'OpenCode, cf. constat « un seul OpenCode partagé »)
  et dans le journal de test (masqué depuis, journal en 600, session supprimée).
- Diff : refus d'office `*echo*TOKEN*`, `*printenv*`, `env`, `*/proc/*/environ*` ; consigne « N'affiche jamais $FORGEJO_TOKEN ni l'environnement ».
- Test : `mettre-a-jour forge` n° 26 : règles présentes dans `opencode.json`, consigne dans `AGENTS.md`. 

## B27 — Les conversations OpenCode disparaissent à chaque mise à jour
- Constat : après `mettre-a-jour forge`, `GET /session` → 0 session. Les données d'OpenCode (`/home/node/.local/share/opencode`, `opencode.db`) vivent dans le conteneur, recréé à chaque mise à jour.
- Diff : volume `/srv/opencode` (uid 1000) monté sur ce chemin, créé avec `/srv/workspace`.
- Test : `mettre-a-jour forge` n° 27 : `/srv/opencode` monté (log, repos). Survie d'une session à une mise à jour : voir essai web n° 6.

## Constat — un seul OpenCode pour toute l'équipe dev
- Un conteneur, un `/workspace`, une liste de sessions commune, un compte Forgejo (`hibou-dev`), une clé d'API (même priorité pour tous). Accès : équipes `dev` et `owners` par oauth2-proxy.
- Remplacé par B30 (une instance par personne).

## B28 — `mettre-a-jour` réussit alors qu'un conteneur redémarre en boucle
- Constat : après la première version de B27 (volume monté sur `.local/share/opencode`), OpenCode plante (`EACCES: mkdir '/home/node/.local/state'` : Docker a créé `.local` au nom de root),
  mais `mettre-a-jour forge` n° 27 finit en rc=0 : `docker compose up -d` réussit dès que les conteneurs sont lancés.
- Diff : B27 monte tout `/home/node/.local` ; `demarrer` regarde 10, 20 et 30 s après si un service est `restarting` et s'arrête avec son nom et la commande de journaux. `--remove-orphans` retire les services disparus du compose.
- Test : `mettre-a-jour forge` n° 28 : OpenCode `Up`, `opencode.db` dans `/srv/opencode/share/opencode` ; n° 29 : contrôle passé, ancien service `opencode` retiré. **Prouvé** (le cas d'échec n'a pas été rejoué volontairement).

## B29 — Agent dev : PR annoncée mais pas ouverte, `.venv` commité (essai web n° 6)
- Constat : après B22 et B25, l'agent commence bien par `forgejo-nouveau-depot` (main protégée) et pousse `agent/verif-nombre` en 3 min 14 s,
  mais annonce « Pull request créée » avec le lien `/compare/` que Forgejo affiche au push (aucune PR), et commite `.venv` (pas de `.gitignore`). `npm install` non lancé.
- Diff : `forgejo-nouveau-depot` dépose un `.gitignore` de départ (`.venv/`, `venv/`, `__pycache__/`, `*.pyc`, `node_modules/`, `.pytest_cache/`) ; consigne : « Un lien en /compare/ n'est pas une pull request ».
- Test (instance d'alice, commandes à la main) : `.gitignore` présent, `.venv` créé puis `git add .` : `.venv` non commité. Comportement du modèle à revoir à l'essai suivant.

## B30 — Une instance OpenCode par personne (demande de l'utilisateur)
- Avant : un conteneur, un `/workspace`, des sessions communes, une clé d'API, commits au nom de `hibou-dev`.
- Diff : `services_opencode` génère `opencode-<utilisateur>` pour chaque personne de l'équipe dev (`/srv/workspace/<u>` → `/workspace`, `/srv/opencode/<u>` → `.local`,
  `/srv/hibou/opencode/<u>.json` avec la clé de la personne, `GIT_AUTHOR_*` = la personne, committer `hibou-dev`, `HIBOU_UTILISATEUR`) ;
  `routes_opencode` : Caddy route par `X-Auth-Request-Email` (en-tête client retiré avant `forward_auth`), sinon 403 « Pas d'espace OpenCode pour ce compte » ;
  `forgejo-pr` ajoute « Demandé par @<utilisateur> » ; note en mise à jour si `/srv/workspace` contient des dossiers hors espaces personnels.
- Test : `mettre-a-jour forge` n° 29 (3 min 51 s) : `opencode-alice` seul (bob est doc seulement), ancien `opencode` retiré, note sur `verif-nombre`.
  Vraie connexion (Forgejo → OAuth → Caddy) : alice → OpenCode (HTTP 200) ; bob → 403 (oauth2-proxy, pas dans dev) ; hibou-admin → 403 « Pas d'espace OpenCode ».
  Dans l'instance d'alice : commit `alice <alice@hibou.lan>`, committer `hibou-dev`, PR « Demandé par @alice ». **Prouvé.**
- Mémoire : ~350 Mo par instance sur forge.

## Étape 1 (dev) — essais réels, 2026-11-21 après-midi
- **Refus de `rm -rf .git`** par le vrai agent (instance d'alice) : 3 tentatives, 3 refus d'OpenCode (« The user has specified a rule which prevents you… »). **Prouvé.**
- **pip et npm par le miroir** dans l'agent : `npm install` réussit après que l'agent a corrigé une version inventée (`^4.0.0` alors que le miroir a 7.0.0) ;
  `pip install pytest` échoue (pytest absent du miroir, invisible dans un `.venv` isolé) : 25 min de boucle.
  Diff (consignes) : `python3 -m venv --system-site-packages .venv` ; installer sans numéro de version.
- **Relecteur sur une PR de documentation** (PR de documentation, dev en marche) : avis posté, 10 remarques au plus (B24), surtout génériques : limite du 4B.
- **Runner** : refuse la PR n° 8 (sections « Objet » et « Retour arrière » manquantes dans le document d'essai écrit à la main) ; corrigé sur la branche → succès.
- **Fusion** : non faite par Claude (le contrôle humain est voulu : le classifieur de sécurité a refusé l'approbation et la fusion automatiques). À faire par une personne.

## Étape 2 (doc) — priorité
- Test sur le serveur doc : bob n° 1 (0 s), bob n° 2 (0,5 s), alice n° 3 (1,5 s), 400 tokens chacune.
  Fins : bob n° 1 à 34 s (jamais interrompue), **alice à 51,5 s**, bob n° 2 à 69 s. Journal de `priorite` : « alice (rang 0) attend… », métriques
  `hibou_llm_requetes_total` (alice 1, bob 2), `hibou_llm_attente_secondes_total` (alice 32 s, bob 51 s), `hibou_llm_contexte_max` 8192. **Prouvé.**

## B31 — Open WebUI : aucun compte non administrateur ne peut utiliser les modèles Hibou (bloquant)
- Symptôme : alice (rôle user, connectée par Forgejo) : `POST /api/chat/completions` → 400 `Model not found` ; d'abord aucun modèle visible.
- Cause : Open WebUI 0.13 réserve à l'administrateur toute ressource sans autorisation (`access_grant`) ; il refuse aussi un modèle dont le modèle de base n'est pas enregistré
  (journal : `reason=base_model_unregistered`). L'essai précédent passait par le compte administrateur, d'où un défaut resté invisible.
- Diff (`amorcer_open_webui`) : lecture publique (`principal_id: "*"`) sur les modèles Hibou (`/models/model/access/update`, la mise à jour ignore `access_grants`),
  les outils (`/tools/id/<id>/access/update`) et les deux bases (`/knowledge/<id>/access/update`) ; modèles de base de chat servis par doc et dev enregistrés et ouverts.
- Test : `mettre-a-jour forge` n° 35 : `access_grant` public sur 7 modèles, 2 outils, 2 bases ; alice voit `qwen3.5-4b` et les 6 modèles Hibou et obtient une réponse. **Prouvé.**

## B32 — Export de documents téléchargeables dans le chat (demande de l'utilisateur)
- Outil `exporter_document` (amorce `open-webui/exporter_document.py`) : Markdown → `.docx` (python-docx), `.pdf` (fpdf2, polices DejaVu, bandeau ambre, titres ardoise),
  `.pptx` (python-pptx), `.xlsx` (openpyxl, tableaux Markdown), `.md`. Le fichier est enregistré au nom de la personne (`Files.insert_new_file`) et attaché au message (événement `files`).
- python-docx, python-pptx et openpyxl sont dans l'image d'Open WebUI ; **pandoc y est aussi mais plante (segfault) sur le processeur d'essai** sans AVX2 : non utilisé.
  fpdf2 2.9.0, fonttools, defusedxml : téléchargés par le pip de l'image Open WebUI (`telecharger`, dossier `owui-py/` du bundle, `versions.lock` : `owui-py`),
  décompressés dans `/srv/hibou/owui-py`, montés en lecture seule sur `/app/hibou-py`.
- Modèles Hibou et « Documentation interne » : outil ajouté, consigne « si la personne demande un fichier… appelle exporter_document ».
- Test : conversions dans le conteneur (docx 37 Ko, pdf 26 Ko, pptx 30 Ko, xlsx 5 Ko ; PDF relu : accents, gras, listes numérotées, tableau, code).
  Page de chat en alice (`hibou-procedure`, « rédige… puis exporte-la en PDF ») : fichier attaché en 53 s, téléchargé par alice (29 Ko, `%PDF-1.3`), propriétaire alice ;
  **bob : 404** sur le même fichier. Nom sans accents translittérés corrigé (`redemarrage-…`). **Prouvé.**
- Pistes : thème de document PowerPoint aux couleurs Hibou ; export `.odt` quand pandoc fonctionnera (processeur avec AVX2, à vérifier).

## B33 — Compression du contexte dans le chat (doc)
- Constat (mesure directe) : au-delà du contexte, llama-server refuse (`exceed_context_size_error`) ; Open WebUI ne compresse rien.
- Diff : filtre global `compression_contexte` (amorce `open-webui/compression_contexte.py`) : au-delà de la moitié du contexte du modèle (le reste pour les extraits de la base),
  résume les anciens échanges par le modèle lui-même, par morceaux, garde les derniers messages tels quels (au moins 4), place le résumé dans le message système
  (Qwen refuse un second message système), annonce « je résume N anciens messages » ; si le résumé échoue, retire les plus anciens. Résumé gardé en mémoire par conversation.
  Contextes réglés par le script d'après les profils (le plus petit si doc et dev servent le même nom : `qwen3.5-4b` 8192 et non 32768).
- Test : page de chat en alice, 40 messages (34 356 caractères, ~10 400 tokens, qui donnaient 400 sans filtre) + « quel est le code donné au début ? » :
  « je résume 31 anciens messages », résumé en 51 s, réponse **« 4721 »** juste en 66 s. **Prouvé.**
- Pour 4 × Quadro RTX 4000 (32 Go, profil doc ≥ 24 Go : Gemma 4 26B 64k ou Qwen3.8 27B 32k), le seuil tombe à 32k ou 16k tokens d'historique.

## B34 — doc : un espace par personne
- Conversations et fichiers : déjà propres à chaque compte dans Open WebUI (fichier d'alice : 404 pour bob, B32).
- Publication (`publier_forgejo` 0.3.0) : branche `redaction/<personne>/<chemin>-<date>`, commit au nom de la personne, PR « Demandé par <nom> (<courriel>) ».
  `docs.hibou.lan` publie tout ce qui est fusionné dans `main` (inchangé).
- Test : PR hibou-docs n° 8 : branche `redaction/alice/procedures-verifier-sauvegarde-forge-…`, commit `alice <alice@hibou.lan>`, corps « Demandé par alice (alice@hibou.lan) ». **Prouvé.**

## Chaîne documentaire complète (PR hibou-docs n° 8, fusion autorisée par l'utilisateur)
- Fusion sans approbation : 405 (protection) ; approbation par hibou-admin puis fusion : 200. Runner sur main : site construit et publié
  (`/srv/docs-site/procedures/verifier-sauvegarde-forge/`, titre « Vérifier la sauvegarde nocturne de forge - Hibou · Documentation »), synchronisation du chat en échec (B35).
- Après B35 : « Documentation interne », interrogé par alice (« Comment vérifier que la sauvegarde nocturne de forge a réussi ? ») répond en 24 s à partir de la page, source [1]. **Prouvé.**

## B35 — Base « Hibou · Documentation » : synchronisation en échec et documents validés écrasés à chaque mise à jour
- Symptômes : runner après fusion : `HTTP Error 400` sur `/knowledge/<id>/file/add` (`DUPLICATE_CONTENT`) ; après correction, `The content provided is empty` sur la 2e page.
  Et à chaque `mettre-a-jour forge`, la base était remplie avec les documents **de départ** du bundle, pas avec ceux fusionnés.
- Causes : (1) `hibou-docs` garde les outils amorcés à l'installation (version d'avant B16), rien ne les met à jour ;
  (2) Open WebUI extrait le texte d'un fichier en arrière-plan : ajouté à la base 50 ms après l'envoi, il est encore vide ;
  (3) `amorcer_open_webui` synchronisait `amorces/hibou-docs`.
- Diff : synchronisation depuis un clone de `main` de hibou-docs avec l'outil du bundle ; envoi `?process_in_background=false` (synchronisation et templates) ;
  `outils_par_pr` : outils, workflow et gabarits du bundle proposés par **pull request** (`hibou/outils-<version>`, branche mise à jour si la PR est ouverte), jamais poussés sur main.
- Test : `mettre-a-jour forge` n° 38 : « Documentation fusionnée envoyée au chat (2 pages) », « pull request des outils 0.9.0 mise à jour » (PR n° 9, à fusionner par une personne). **Prouvé.**

## Phase 6.1 — Mise à jour d'une seule image (`HIBOU_ACTUALISER=caddy`)
- `telecharger` (5 min 29 s) : Caddy revérifié, empreinte publiée inchangée (`caddy:2`), donc 18 images « inchangée », `versions.lock` identique pour Caddy.
- `mettre-a-jour forge` n° 39 : « 0 image(s) chargée(s) » ; `secrets.env`, `opencode.env`, `priorite.json` identiques (empreintes), mêmes 6 comptes, même client OIDC Proxmox.
- Constat : tous les conteneurs de forge sont recréés à chaque mise à jour (`--force-recreate`, nécessaire pour les fichiers montés remplacés) : coupure de quelques secondes de tous les services, pas seulement du service changé.

## B36 — Connexion à Proxmox par Forgejo impossible (hôte sans DNS vers forge, émetteur OIDC différent)
- Symptômes : `POST /access/openid/auth-url` → 500 `failed to lookup address information` ; puis `unexpected issuer URI https://forge.hibou.lan (expected https://forge.hibou.lan/)`.
- Causes : l'hôte Proxmox ne résout pas `forge.<domaine>` (son DNS n'est pas forge) ; le domaine est créé avec `--issuer-url https://forge.<domaine>/`, Forgejo annonce l'émetteur sans barre finale.
  `realm_proxmox` n'était pas rejoué en mise à jour.
- Diff : `realm_proxmox` ajoute `forge.<domaine>` à `/etc/hosts` si l'hôte ne le résout pas ; émetteur sans barre finale (et dans `hibou-acces.txt`) ; `realm_proxmox` rejoué en mise à jour (idempotent).
- Test : `mettre-a-jour forge` n° 40 et 41 (entrée ajoutée une fois, non dupliquée) ; connexion complète simulée comme un navigateur (auth-url, formulaire Forgejo, consentement, retour
  `https://pve-doc.hibou.lan:8006` avec le code, `/access/openid/login`) : **ticket obtenu pour `hibou-admin@forgejo`**, droits d'administration. **Prouvé.**

## B37 — Changement de profil : Open WebUI ne suit pas (Phase 6.2)
- Essai : « Changer seulement les cartes et les modèles », doc de `doc:4` (4B) à `doc:3` (9B) : `telecharger` 6 min 39 s, « retiré : doc · qwen3.5-4b », 9B téléchargé (5,6 Go), comptes et clés inchangés ;
  `mettre-a-jour doc` : ancien modèle retiré de la copie du bundle et de `/srv/models`, llama-swap sur le 9B. Mais Open WebUI : modèles Hibou toujours sur `qwen3.5-4b`, filtre sur l'ancien contexte, évaluation sur l'ancienne configuration.
- Cause : `mettre-a-jour doc` ne touche pas forge.
- Diff : phase `owui` du rôle forge (rebranche Open WebUI, copie `config.env` pour l'évaluation) ; doc et dev la lancent en fin d'installation ou de mise à jour, après avoir recopié script, configuration et amorces sur forge.
  Effet de bord utile : la base de templates se remplit dès l'installation de doc (plus besoin de relancer `mettre-a-jour forge`, cf. B8).
- Test : `mettre-a-jour doc` : « J'ai terminé le rôle forge (phase owui) », modèles Hibou sur `qwen3.5-9b`, contextes du filtre à jour, `PROFIL_DOC=3` dans la configuration de l'évaluation. **Prouvé.**
  Retour à `doc:4` : « retiré : doc · qwen3.5-9b » (6 min 12 s), `mettre-a-jour doc` : 4B servi, Open WebUI rebranché sur `qwen3.5-4b` automatiquement. **Prouvé dans les deux sens.**

## Phase 6.3 — Sauvegarde ; B38 — une sauvegarde manuelle ne met pas la métrique à jour
- `vzdump 210 --storage hibou-sauvegardes --mode snapshot` : `fs-freeze` puis `fs-thaw` par l'agent invité, 80 Gio lus en 135 s, archive 24 Go (sans compression : défaut de vzdump), 2 min 17 s.
  Avec `--compress zstd` : 14,5 Go, 2 min 40 s. La tâche planifiée de 3 h a bien tourné la nuit précédente (métrique à 03:02).
- B38 : la métrique `hibou_sauvegarde_derniere_reussite_timestamp` ne bouge pas après une sauvegarde manuelle : le crochet n'est attaché qu'à la tâche planifiée ;
  et la configuration de sauvegarde n'était pas rejouée en mise à jour.
  Diff : fonction `sauvegarde_forge` (tâche, crochet) rejouée en mise à jour de forge ; crochet limité à la VM forge (sinon une autre VM sauvegardée une fois déclencherait l'alerte « plus de 26 h ») ;
  `script:` global dans `/etc/vzdump.conf` de l'hôte s'il n'y en a pas déjà un (sinon note, rien n'est écrasé).
  Test : `mettre-a-jour forge` n° 42, puis `vzdump 210 … --compress zstd` : fichier de métrique à l'heure exacte de la fin, relevé par Prometheus (`job noeuds`). **Prouvé.**

## Phase 6.4 — Restauration
- `qmrestore` de l'archive zstd vers la VM 299 (`--unique 1`, stockage des VM) : 7 min 41 s ; renommée `hibou-restauration`, `onboot 0`, carte réseau coupée (`link_down=1`, même adresse que forge).
- Démarrée : agent invité prêt en 20 s, 14 conteneurs relancés ; Forgejo `/api/healthz` 200, Open WebUI `{"status":true}` ;
  6 comptes, 4 dépôts, `main` de hibou-docs avec la fusion de la PR n° 8 ; Open WebUI : 3 utilisateurs, 10 modèles, 11 conversations, 40 fichiers, 2 bases, 2 outils, 1 filtre ;
  espace OpenCode d'alice présent. Puis arrêtée et supprimée (`qm destroy 299 --purge`). **Prouvé.**

## Phase 6.3 — Sauvegarde ; B38 — une sauvegarde manuelle ne met pas la métrique à jour
- `vzdump 210 --storage hibou-sauvegardes --mode snapshot` : `fs-freeze` puis `fs-thaw` par l'agent invité, 80 Gio lus en 135 s, archive 24 Go (sans compression : défaut de vzdump), 2 min 17 s.
  Avec `--compress zstd` : 14,5 Go, 2 min 40 s. La tâche planifiée de 3 h a bien tourné la nuit précédente (métrique à 03:02).
- B38 : la métrique `hibou_sauvegarde_derniere_reussite_timestamp` ne bouge pas après une sauvegarde manuelle : le crochet n'est attaché qu'à la tâche planifiée ;
  et la configuration de sauvegarde n'était pas rejouée en mise à jour.
  Diff : fonction `sauvegarde_forge` (tâche, crochet) rejouée en mise à jour de forge ; crochet limité à la VM forge (sinon une autre VM sauvegardée une fois déclencherait l'alerte « plus de 26 h ») ;
  `script:` global dans `/etc/vzdump.conf` de l'hôte s'il n'y en a pas déjà un (sinon note, rien n'est écrasé).
  Test : `mettre-a-jour forge` n° 42, puis `vzdump 210 … --compress zstd` : fichier de métrique à l'heure exacte de la fin, relevé par Prometheus (`job noeuds`). **Prouvé.**

## Phase 6.4 — Restauration
- `qmrestore` de l'archive zstd vers la VM 299 (`--unique 1`, stockage des VM) : 7 min 41 s ; renommée `hibou-restauration`, `onboot 0`, carte réseau coupée (`link_down=1`, même adresse que forge).
- Démarrée : agent invité prêt en 20 s, 14 conteneurs relancés ; Forgejo `/api/healthz` 200, Open WebUI `{"status":true}` ;
  6 comptes, 4 dépôts, `main` de hibou-docs avec la fusion de la PR n° 8 ; Open WebUI : 3 utilisateurs, 10 modèles, 11 conversations, 40 fichiers, 2 bases, 2 outils, 1 filtre ;
  espace OpenCode d'alice présent. Puis arrêtée et supprimée (`qm destroy 299 --purge`). **Prouvé.**

## Phase 5 — Charte graphique (captures Playwright, PC 1440 px et téléphone 390 px, thèmes sombre et clair)
- Outil : Playwright + Chromium sur l'hôte d'essai (seul à joindre le réseau isolé), connexion réelle d'un utilisateur par Forgejo.
  Captures avant : `captures/avant/{pc-sombre,pc-clair,tel-sombre}` ; après : `captures/apres/{pc-sombre,pc-clair,tel-sombre,tel-clair}` (14 écrans chacun, plus la page d'erreur de Caddy).
- Conformes dès l'origine : Forgejo (thème nuit, logo, favicon, Fraunces, Inter), site docs (nuit et brume, bascule), terminal (5 couleurs identiques aux jetons, symbole,
  207 messages sans vouvoiement ni point d'exclamation), contrastes des jetons (toutes les paires ≥ 4,5:1, filets ≥ 3:1, dans les deux thèmes).
- Pas de page oauth2-proxy à habiller : `code.` et `docs.` vont directement au formulaire Forgejo.

## B39 — Connexion à Grafana par Forgejo impossible depuis la première mise à jour (« certificate signed by unknown authority »)
- Symptôme : alice, « Sign in with Hibou · Forge » → « Login failed : Failed to get token from provider » ; Grafana : `x509: certificate signed by unknown authority` vers forge.
- Cause : `supervision()`, rejouée à chaque mise à jour, faisait `cp ca-certificates.crt /srv/supervision/ca.crt` et effaçait l'autorité Hibou que seul `configurer` (installation) ajoutait :
  120 certificats au lieu de 121. Grafana et Uptime Kuma ne font plus confiance à forge après la première mise à jour.
- Diff : `ca.crt` = paquet système + autorité Hibou dans `supervision()` ; Grafana : `SSL_CERT_FILE`, connexion automatique par Forgejo (`GF_AUTH_OAUTH_AUTO_LOGIN`, la page
  « Welcome to Grafana » n'est pas personnalisable en version libre), accueil sur « Hibou · Vue d'ensemble », pas de fil d'actualités de grafana.com ;
  réglages ajoutés à `grafana.env` en mise à jour sans le réécrire (il porte les secrets OAuth).
- Test : `mettre-a-jour forge` n° 45 : 121 certificats, `curl` depuis Grafana vers forge : 200 ; captures : alice connectée, accueil sur le tableau Hibou. **Prouvé.**

## B40 — Chat : la charte Open WebUI n'est pas chargée (fond gris, blanc en thème clair)
- Symptôme : chat en gris neutre (`#171717`), blanc en clair, écran de connexion noir pur ; `/static/custom.css` : 200 mais **0 octet**.
- Cause : Open WebUI 0.13 sert `/static/custom.css` depuis `/app/build/static/` ; le script montait la charte dans `/app/backend/open_webui/static/`.
  Puis : calques `bg-black`/`bg-white` purs (écran de connexion), et gris secondaire Nuit (`#8A93A6`) réutilisé en clair : 2,4 à 2,9:1 sur brume (1,7:1 pour certaines étiquettes).
- Diff : montage sur `/app/build/static/custom.css` ; `--color-black` = fond Nuit, `--color-white` = fond Brume ; en clair, gris 400 et 500 = texte-doux Brume (6:1).
  Générateur `charte/generer-themes.py` et CSS généré alignés (le générateur n'est pas relancé ici : chemins de l'environnement de création, il vide sa sortie).
- Test : `mettre-a-jour forge` n° 46 et 47 ; captures : chat nuit (PC, téléphone), brume en clair, connexion nuit ; mesure des contrastes sur les textes affichés : 0 texte sous le seuil
  dans le chat (hors couleurs `oklab`/`oklch`, que le script de mesure ne lit pas). **Prouvé.**

## B41 — Refus d'accès bruts et petits écarts de lisibilité
- `etat.` et `alertes.` (groupe owners) : alice recevait « Forbidden » en texte brut d'oauth2-proxy. Diff : `@interdit status 403` → `error 403` dans le bloc `sso` ;
  page d'erreur Caddy à la charte avec un texte « Accès réservé » pour 403 (« Ce service ne répond pas » sinon). Test : captures « Accès réservé » ; arrêt d'Open WebUI : « Ce service ne répond pas » (502). **Prouvé.**
- Site docs : texte indicatif de la recherche à 3,6:1 → texte plein à 85 %. Le CSS du site vit dans hibou-docs : `docs/assets` ajouté à la pull request d'outils (PR n° 9 mise à jour), effectif après sa fusion.

## B42 — Application complète de la charte (audit du système de design Hibou)
- Référence : système de design Hibou (livre de marque, jetons, composants Bouton, Champ, Invite, Terminal, Attente, Logo, Icônes).
- Conformes : jetons et thèmes Nuit/Brume (Forgejo, chat, docs, pages d'erreur), contrastes, relief et anneau de focus du chat et de Forgejo,
  terminal (couleurs, symbole), ton (tutoiement, pas de « ! », « hors ligne » état normal) du script, de l'agent, du relecteur et de « Documentation interne ».
- Écarts corrigés :
  - **Documents exportés** (`exporter_document` 0.2.0) : polices de la charte (Fraunces, Inter 400/600, JetBrains Mono) converties depuis ses woff2 par fontTools + brotli
    (brotli ajouté aux modules livrés), mises en cache ; titres en `texte` et Fraunces, code en terminal `nuit`/`brume`, en-têtes de tableau `accent`/`sur-accent`, bords `filet-fort` ;
    Word : styles Inter/Fraunces, code sur trame nuit ; PowerPoint : thème Nuit (fond nuit, titres Fraunces brume, filet ambre) ; Excel : Inter, en-tête ambre.
    Test : export réel par le chat en alice, PDF avec `FrauncesSemiBold`, `Inter`, `JetBrainsMonoMedium` embarquées, relu (pptx généré, non relu faute de logiciel de présentation).
  - **Invite du chat** : au focus, bord `accent-fonce` et `lueur` (composant Invite). Capture : halo d'ambre en sombre et en clair.
  - **Typographie du chat** : Fraunces débordait sur les étiquettes et descriptions contenues dans les titres ; limitée aux titres. Capture : nom du modèle en Fraunces, description en Inter.
  - **Site docs** : anneau de focus Hibou, `prefers-reduced-motion` (par la PR d'outils).
- Pas de défaut, mais à noter : les icônes d'Open WebUI, de Forgejo et de Grafana restent les leurs (la charte veut son jeu de 35 icônes) ; l'attente d'Open WebUI est une animation à points, pas les deux yeux qui clignent.

## B43 — Rédacteurs : vouvoiement dans les documents
- Constat : procédure exportée « Connectez-vous… Exécutez… Vérifiez… » ; la consigne des 5 rédacteurs ne parlait ni de tutoiement ni de l'infinitif (la charte : tutoiement dans l'interface, libellés à l'infinitif).
- Diff : consigne « Tu tutoies la personne. Dans les documents, les étapes et consignes sont à l'infinitif, jamais au vouvoiement » ; gabarit Procédure : « verbe à l'infinitif (« Vérifier… », « Lancer… ») ».
- Test : 3 rédactions après la consigne seule : 1 infinitif, 1 vouvoiement, 1 gabarit vide ; après le gabarit : 2 sur 2 à l'infinitif quand un document est produit, 1 gabarit renvoyé vide (limite du 4B, déjà présente).

## B44 — PR d'outils ouverte par l'administrateur, qui ne peut pas l'approuver ; gabarit vide publiable
- Constat : la PR n° 9 (outils de hibou-docs) était ouverte par hibou-admin ; Forgejo interdit d'approuver sa propre PR, d'où une fusion forcée.
  Et le 4B renvoie parfois le gabarit tel quel : `publier_forgejo` ouvrait une PR vouée à l'échec du runner.
- Diff : `outils_par_pr` ouvre la PR au nom de hibou-redac (en-tête `Sudo` de l'API Forgejo, l'administrateur garde la main) ;
  `publier_forgejo` 0.3.1 refuse un document qui contient encore `<!--` et dit quoi faire.
- Test : PR jetable sur hibou-docs créée avec `Sudo: hibou-redac` : « ouverte par hibou-redac », approbation de hibou-admin acceptée (`official=true`), fermée ensuite ;
  outil installé : gabarit vide → « Le document contient encore des consignes du template… ». **Prouvé.**

## B45 — Une mise à jour redémarrait tous les conteneurs
- Constat (phase 6.1) : `mettre-a-jour` faisait `docker compose up --force-recreate` : tous les services coupés quelques secondes, même sans changement.
- Cause : le forçage servait à faire relire les fichiers de configuration montés (remplacés sur le disque, invisibles pour Docker).
- Diff : `empreintes_montages` (empreinte des montages de configuration de chaque conteneur, données exclues) relevée au début de la mise à jour ;
  `up` sans forçage (recrée ce dont la définition change), puis `redemarrer_montages_changes` ne redémarre que les conteneurs dont un fichier monté a changé. forge et serveurs GPU.
- Test : `mettre-a-jour forge` n° 53 sans changement : « Aucun fichier de configuration modifié », aucun conteneur redémarré ;
  n° 54 après une ligne ajoutée à la main dans `AGENTS.md` : seul `opencode-alice` redémarré, consignes rétablies dans le conteneur, les autres intacts. **Prouvé.**

## B46 — Compression du contexte : bouton pour chaque personne (demande de l'utilisateur)
- Diff : filtre `compression_contexte` 0.2.0 à bascule (`toggle`), icône « Résumer » de la charte, réglage personnel « Ne jamais compresser mes conversations » (`UserValves`) ;
  le script le rattache à tous les modèles de chat et le coche par défaut (`filterIds`, `defaultFilterIds`) ; statut final « Bouton « Compression du contexte » pour la couper ».
- Test (alice, 40 messages, ~10 400 tokens) : bouton actif → « je résume 31 anciens messages » ; bouton coupé → refus du serveur (15 122 tokens pour 8 192) ;
  bouton actif + « jamais » → aucune compression. Capture : menu « + » du chat, interrupteur actif par défaut. **Prouvé.**

## B47 — Chat : défauts d'affichage pendant un échange
- Constats (captures d'un échange complet, sombre et clair) : double cadre dans l'invite et texte collé au bord (mon CSS appliquait creux et arrondi au conteneur ET au champ),
  fond de l'invite gris neutre au lieu de `fond-creux`, numéros de ligne des blocs de code sur une pastille grise.
- Diff : creux, arrondi et `fond-creux` sur le conteneur seul ; champ transparent, sans anneau (la lueur du conteneur marque le focus), marge 8 × 14 px ; gouttière des blocs de code transparente.
- Test : captures après (sombre, clair) : un seul cadre creusé, texte décollé, lueur ambre au focus. **Prouvé.**

## B48 — Prompts des rédacteurs
- Constats : date inventée (2025-07-22), dossier de publication à deviner, nom de l'outil cité à la personne (« avec l'outil `publier_document` »), « Souhaitez-vous… », rien sur les bases de connaissances.
- Diff : `date: {{CURRENT_DATE}}` (Open WebUI la remplace), dossier par type (`docs/procedures`, `docs/fiches-techniques`, `docs/guides`, `docs/architecture`, `docs/decisions`),
  publication seulement après accord explicite, « Ne nomme jamais tes outils », appui sur les bases de connaissances, « la personne » au lieu de « l'utilisateur » ;
  « Documentation interne » : outil d'export et même règle. Les questions de suivi d'Open WebUI sont déjà à l'infinitif : gabarits des tâches laissés.
- Test : rédaction après mise à jour : étapes à l'infinitif, plus de nom d'outil dans la réponse.

## B49 — Documentation de sécurité dans le chat (demande de l'utilisateur)
- Menu de `telecharger` : « Documentation de sécurité : l'ajouter au bundle ? » (`HIBOU_SECURITE`, partie `securite`). Récupère tous les guides de l'ANSSI en français depuis
  `messervices.cyber.gouv.fr/guides` (le site cyber.gouv.fr est protégé contre les robots : non contourné), plus une liste `securite.d/autres.txt` (adresses de PDF) et un dossier
  `securite.d/ajouts/` pour les textes sans lien direct : IGI 1300 (site du SGDSN protégé), II 901, PSSIE, RGS, guide de la CNIL. Index `securite/INDEX.tsv`.
- forge : base « Hibou · Sécurité » (lecture pour tous), chargée en tâche de fond par `charger_securite.py` (`systemctl status hibou-securite`, reprise où elle s'est arrêtée) ;
  modèle « Hibou · Sécurité » (cite le guide et la recommandation, signale quand il sort des documents).
- Mesures : 179 documents (135 guides), 164 Mo, téléchargés en 47 s à 3 min 37 s ; 1 PDF absent côté ANSSI. Adresses accentuées encodées (7 échecs au premier essai).
  Indexation sur ce processeur : ~20 s par document.

## B50 — Outils manquants pour doc et dev
- doc : `publier_forgejo` 0.4.0 : `lire_document` (version publiée) et `mettre_a_jour_document` (nouvelle version par PR) ; consigne des rédacteurs : lire puis proposer.
- dev : commande `forgejo-tickets` (tickets ouverts du projet) ; consigne : « Closes #<numéro> » dans la PR pour fermer le ticket à la fusion.
- Test : outil installé avec ses trois fonctions ; `forgejo-tickets` dans l'instance d'alice, consigne présente.

## B51 — Indexation de la base sécurité refusée par le serveur d'embeddings
- Constat : 131 documents refusés (HTTP 400 d'Open WebUI) ; dans les journaux, llama-swap répond 429 aux embeddings. Open WebUI envoie les lots sans limite de concurrence :
  `RAG_EMBEDDING_CONCURRENT_REQUESTS` est une PersistentConfig, lue au premier démarrage seulement, donc ignorée sur une installation existante.
- Diff : `amorcer_open_webui` impose par l'API (`/retrieval/embedding/update`) lots de 16 et 4 requêtes simultanées, à chaque installation et mise à jour.
- Test : `mettre-a-jour forge` n° 58 ; base : `embedding_batch_size 16`, `embedding_concurrent_requests 4` ; reprise « 179 documents, 9 déjà dans la base, 170 à ajouter » ;
  sur 10 min : 0 refus, 0 réponse 429, un document toutes les ~20 s. **Prouvé.**

## B52 — Mise à jour d'une page refusée par le runner (liste coupée par un bloc de code)
- Constat (test réel de B50) : alice demande d'ajouter une étape à une procédure publiée ; `lire_document` puis `mettre_a_jour_document` ouvrent la PR n° 11
  au nom d'alice (compte hibou-redac), mais le runner échoue : `MD029/ol-prefix [Expected: 1; Actual: 4]`. Le bloc de code sous l'étape 3, non indenté, ferme la liste ;
  l'étape « 4. » ouvre une nouvelle liste (le site l'aurait aussi numérotée 1).
- Diff : `normaliser()` (publier_forgejo 0.4.1) indente sous l'étape numérotée qui le précède tout bloc de code placé juste après elle.
- Test : exemple passé au markdownlint du runner (0 problème) ; même demande par alice : PR n° 12, blocs indentés, runner **success**. **Prouvé.**
- Relecteur, VM dev arrêtée : avis « Relecture automatique impossible … La relecture humaine reste nécessaire » posté dans la PR (B23 tient).

## B53 — Mise à jour de forge pendant le chargement de la base sécurité : 59 documents refusés (401)
- Constat : `amorcer_open_webui` renouvelle la clé d'API d'Open WebUI à chaque passage, ce qui révoque l'ancienne ; le chargeur en cours l'utilise encore :
  « 111 ajouté(s), 59 échec(s) », tous `HTTP Error 401`. La relance n'a eu lieu que parce que le chargeur avait fini d'échouer avant le test `is-active` (course).
- Diff : arrêt du chargeur avant le renouvellement de la clé, relance systématique (il reprend où il s'est arrêté) ; `docker run --init` : sans lui, le chargeur
  (PID 1 du conteneur) ignorait SIGTERM et systemd attendait 90 s avant SIGKILL.
- Test : deux `mettre-a-jour forge` en plein chargement : arrêt dans la seconde (status 143), reprise « 146 déjà dans la base, 33 à ajouter », 0 erreur 401, un seul chargeur. **Prouvé.**

## B54 — Rotation des secrets impossible : anciens jetons jamais révoqués, clé des modèles figée dans Open WebUI (tâche 3)
- Constats : `configurer` crée un jeton à chaque passage sans révoquer les précédents (hibou-dev : 2 jetons `opencode-…` actifs, dont celui affiché pendant l'essai) ;
  Open WebUI garde `openai.api_keys` et `rag.openai.api_key` en base (lus de l'environnement au premier démarrage seulement) : une nouvelle clé l'aurait coupé des modèles.
- Diff : `jeton_neuf` (nouveau jeton, puis révocation des jetons du même usage) pour hibou-dev, hibou-redac, hibou-relecteur ; `amorcer_open_webui` impose la clé
  par l'API (`/openai/config/update`, `openai_config.key`) ; commande **`hibou renouveler-secrets`** (hôte Proxmox) : nouvelles clés (Open WebUI, OpenCode, relecteur,
  clés personnelles), `secrets.chiffre` rechiffré avec la même phrase et son empreinte mise à jour, puis forge (`configurer` rejoué : jetons, 4 applications OAuth,
  secret du webhook, cookie OpenCode) et doc/dev en marche ; une VM arrêtée est signalée. Mots de passe des personnes, phrase et clés SSH inchangés (dit à la fin).
- Test : avant : jetons `opencode×2`, `open-webui×2` ; après (413 s, rc=0) : un jeton neuf par compte, 4 applications OAuth recréées (identifiants changés),
  Open WebUI, relecteur et Grafana redémarrés ; `hibou essai` : 14 OK (connexion au chat, à OpenCode et à Grafana avec les nouveaux secrets, chat, RAG, export, runner) ;
  alice se connecte et obtient une réponse. dev arrêtée : signalée, à mettre à jour à son démarrage. **Prouvé.**

## B55 — Export PDF cassé après une mise à jour (régression de B45)
- Constat (trouvé par `hibou essai`) : « la bibliothèque fpdf n'est pas disponible ». `/app/hibou-py` vide dans le conteneur alors que `/srv/hibou/owui-py` est plein :
  chaque passage faisait `rm -rf` puis recréait le dossier monté ; depuis B45, Open WebUI n'est plus redémarré si le contenu est identique et garde l'ancien dossier, supprimé.
- Diff : extraction dans un dossier temporaire puis `rsync --delete` vers le dossier monté (même inode) ; en mise à jour, Open WebUI est redémarré s'il ne voit pas `fpdf`
  (répare les installations touchées).
- Test : `mettre-a-jour forge` n° 64 : « Open WebUI redémarré : il ne voyait plus les modules d'export », `fpdf 2.9.0` importable ; inode 1773810 identique après
  la rotation (mise à jour complète) ; essai : export PDF téléchargé, PDF valide. **Prouvé.**

## B56 — Un guide de l'ANSSI jamais indexé (titre en double)
- Constat : 179 documents, 178 dans la base ; « Sauvegarde des systèmes d'information » désigne deux guides (Fondamentaux, Essentiels). Le chargeur nomme le fichier
  d'après le titre et prenait le second pour un doublon.
- Diff : l'index numérote les titres en double (« … (2) ») ; `systemd-run --quiet` (plus de « Running as unit » dans la sortie).
- Test : `telecharger` (partie securite) puis `mettre-a-jour forge` : « 178 déjà dans la base, 1 à ajouter », ajouté en 2 s. Base : 179 documents. **Prouvé.**

## F4 — `hibou diagnostic` (tâche 4)
- Sur l'hôte Proxmox, sans rien modifier : stockages, quorum du cluster, cartes en vfio-pci, dernière sauvegarde de forge (< 26 h) ; par VM : marche, SSH, disque,
  conteneurs `hibou-*` arrêtés ou en boucle ; forge : Forgejo, Open WebUI, 6 sites HTTPS, expiration de l'autorité Hibou, base sécurité, forge → doc/dev ; doc/dev : cartes vues, API.
  Rapport sans secret `/root/hibou-diagnostic-<date>.txt`, code 1 en cas d'échec.
- Test : 23 OK, 2 attentions (dev arrêtée) ; ntfy arrêté exprès : « ÉCHEC VM forge : conteneurs arrêtés ou en boucle (hibou-forge-ntfy-1:exited) », code 1. **Prouvé.**

## F12 — `hibou essai` : essai de bout en bout automatisé (tâche 12)
- Compte Forgejo temporaire (équipes doc et dev), puis, comme une personne : connexion au chat par Forgejo, modèles visibles, chat, réponse sourcée (documentation,
  sécurité), export PDF téléchargé et vérifié, connexion à OpenCode et à Grafana, PR de documentation, runner, relecture (attendue « impossible » si dev est arrêtée),
  instance OpenCode de chaque développeur ; ménage (comptes Forgejo, chat, Grafana ; PR fermée, branche supprimée). Rapport sans secret, code 1 en cas d'échec.
- Premier passage : a trouvé B55 (export) ; deux défauts de l'essai lui-même corrigés (page « Pas d'espace OpenCode » attendue pour un compte sans instance ;
  question générale sans recherche → question qui déclenche la recherche).
- Test : 14 OK en 1 min avant et après la rotation des secrets. **Prouvé.**

## F1 — Cartes de doc en production : carte de recherche à part (tâche 1)
- Constat : sur un hôte doc à quatre cartes de 8 Go et une petite carte de 4 Go, toutes les cartes NVIDIA passent à la VM et `indices_gpu` les donne toutes au LLM :
  `--tensor-split 1,1,1,1,1`, l'A400 (4 Go, plus lente) reçoit un cinquième des couches : ralentissement et risque de manque de mémoire.
- Diff : question du menu « Une petite carte à part pour la recherche documentaire ? » (`HIBOU_RAG_GPU/GO/NB`) ; la carte est retirée du partage des couches et porte
  les embeddings (`-ngl 99` au lieu du processeur) ; chaque modèle est épinglé à ses cartes par UUID (`env: CUDA_VISIBLE_DEVICES`), CUDA renumérotant les cartes dans le conteneur.
- Test à blanc (faux nvidia-smi, 4 RTX 4000 + A400 en position 2) : LLM `["0","1","3","4"]`, `tensor-split 1,1,1,1` ; embeddings sur l'A400 seule ; sans l'option,
  `1,1,1,1,1` (défaut reproduit). llama-swap de l'image livrée : « Executing start command … env: CUDA_VISIBLE_DEVICES=… » (clé `env` prise en compte).
  À valider sur le matériel de production (`hibou essai`, `hibou-eval`).

## B57 — Mise à jour avec doc arrêtée : trace Python et message trompeur
- Constat : `mettre-a-jour dev` (doc arrêtée, une seule carte sur l'hôte d'essai) : `urllib.error.HTTPError: HTTP Error 400` puis « Clé du runner ou synchronisation refusée ».
  Cause réelle : doc calcule les embeddings ; sans elle, Open WebUI refuse l'envoi de la documentation. Même cas à toute installation neuve (forge avant doc),
  et le chargeur de la base sécurité aurait échoué sur ses 179 documents.
- Diff : clé du runner toujours mise à jour (elle vient d'être renouvelée) ; envoi de la documentation et chargement de la base sécurité seulement si doc répond,
  sinon un message dit pourquoi et quand cela se fera (mise à jour de doc, prochaine fusion).
- Test : `mettre-a-jour forge` n° 66, doc arrêtée : les deux messages, aucune trace, rc=0. **Prouvé.**

## B58 — L'agent ouvre une pull request vide
- Constat (test réel de `forgejo-tickets`, dépôt d'essai avec le ticket n° 1 « Ajouter une fonction soustraire ») : l'agent d'alice lit le ticket
  (`forgejo-tickets`), écrit la fonction et passe pytest, puis appelle `forgejo-pr` avec « Closes #1 » **sans avoir commité** : PR n° 2 vide (0 fichier), non fusionnable.
- Diff : `forgejo-pr` refuse s'il reste des fichiers suivis modifiés (« git add … && git commit », puis relancer) ou si la branche n'a aucun commit de plus que main ;
  il signale les fichiers non suivis absents de la PR.
- Test : dépôt jetable : modifié non commité → refus rc=1 ; aucun commit → refus rc=1 ; commit + fichier non suivi → avertissement puis push. Image OpenCode reconstruite,
  `mettre-a-jour forge` n° 67 ; second passage de l'agent : commit puis PR n° 3 (`calcul.py` +3). Le 4B a oublié cette fois « Closes #1 » et le test (variabilité du modèle,
  consignes en place) ; « Closes #1 » ajouté à la main, fusion : ticket n° 1 fermé. Dépôt d'essai supprimé. **Prouvé** (outil) ; agent 4B : limites connues.

## B59 — Les documents joints au chat n'arrivaient jamais au modèle
- Constat (test de l'import, tâche 8) : un `.docx` joint est bien extrait (433 caractères) mais le modèle répond « je ne vois aucun fichier ». Open WebUI 0.13 ne donne
  le texte d'un fichier joint qu'aux modèles qui ont la capacité `file_context` (`is_file_context_enabled`) ; sinon le modèle doit le lire par ses outils, ce que le 4B ne fait pas.
  Touchait tous les modèles Hibou, rédacteurs compris (« des notes, des captures ou des documents »).
- Diff : `modele_owui` ajoute `capabilities.file_context: true` à chaque modèle de chat ; `hibou essai` contrôle désormais un fichier joint (code aléatoire à retrouver).
- Test : import du `.docx` : source `impression.docx`, contenu repris ; essai : « Fichier joint lu par le modèle » OK. **Prouvé.**

## F6 — Recherche hybride et reranker (tâche 6)
- Diff : reranker `ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF` (640 Mo) servi par llama-swap sur doc (`--reranking`, groupe `rag`, masqué du sélecteur), branché à Open WebUI
  en reranker externe (`/v1/rerank` via le service de priorité, qui ne met en file que la génération) ; recherche hybride (BM25 + sens), 20 candidats, 5 retenus.
  **Seulement avec la carte de recherche (F1)** : mesuré sur le processeur de l'hôte d'essai, reranker 87 tokens/s (44 s pour 5 extraits, 166 à 562 s par question),
  et la recherche hybride sans reranker recalcule les embeddings des candidats (~8 s chacun, essai en 11 min). Sans carte : recherche par le sens seule, comme avant.
- Test (forcé sur le processeur, `HIBOU_RERANKER=1`) : `/v1/rerank` classe le bon passage à 0,998 et les autres à 0 ; Open WebUI : « Starting hybrid search »,
  « ExternalReranker:predict:model qwen3-reranker » ; essai 16 OK. Puis option retirée du menu sans carte, essai revenu à 1 min (17 OK). Sur carte : à mesurer sur le matériel de production.

## F7 — Relecteur appuyé sur les guides de l'ANSSI (tâche 7)
- Diff : le relecteur interroge la base « Hibou · Sécurité » (`/api/v1/retrieval/query/collection`, 4 extraits) avec les fichiers et les lignes ajoutées du diff, joint
  les extraits au prompt et cite le guide entre crochets ; clé et base relues à chaque relecture dans `securite.env` monté en lecture seule (créé vide sans la base) ;
  mention « avec les guides de l'ANSSI » dans l'avis. Sans base ou si elle ne répond pas, relecture comme avant.
- Test (dev arrêtée : relecteur pointé un temps sur doc, même modèle 4B, puis rétabli) : PR avec `PermitRootLogin yes`, `PasswordAuthentication yes`, MD5 et `verify=False` :
  9 remarques, dont 6 citent un guide (« [ANSSI · Usage sécurisé d'(Open)SSH] » pour les directives SSH) ; deux attributions approximatives du 4B (MD5 rattaché au guide
  GNU/Linux, `verify=False` au guide SSH). **Prouvé** ; précision à revoir avec le modèle de production.

## F8 — Import d'un document existant (tâche 8)
- Diff : modèle « Hibou · Import d'un document » : reçoit la liste des gabarits et de leurs sections (lue dans le bundle), choisit le plus proche, reprend le contenu fidèlement,
  en-tête YAML exact, sections remplies, « À compléter » seulement si le document ne dit rien, liste de ce qui a été déplacé, publication sur accord. Sans la base des gabarits
  (le 4B recopiait leurs commentaires `<!-- -->`).
- Test (alice, `.docx` libre « Redémarrage du serveur d'impression ») : premier jet sans en-tête et avec les commentaires du gabarit ; après la consigne : en-tête correct,
  Objet, Prérequis, 5 étapes à l'infinitif, Vérification, Retour arrière, toutes tirées du document. Chemin proposé sans le dossier `procedures/` (le 4B), publication non faite.

## F10 — Notifications d'équipe par ntfy (tâche 10)
- Diff : le relecteur publie dans le sujet `hibou-pr` : « PR à relire » (ouverture), « Relecture prête » ou « Relecture impossible », avec le lien ; Caddy ouvre
  l'interface ntfy (`alertes.<domaine>`) aux équipes doc et dev, le sujet `hibou` (alertes des serveurs, dont « Sauvegarde en retard », déjà existante) restant aux administrateurs.
- Test : sujet `hibou-pr` : « PR à relire », « Relecture impossible », « Relecture prête » ; essai (compte doc/dev) : notification de sa PR trouvée, sujet `hibou` → HTTP 403. **Prouvé.**

## F11 — Usage par personne dans Grafana (tâche 11)
- Diff : tokens lus et générés comptés par personne (le service de priorité ne comptait que les requêtes et l'attente) ; tableau « LLM en direct » : rangée « Usage par personne »
  (tokens générés et lus sur 7 jours, tokens générés par heure) ; débits recalculés par modèle.
- Test : image du service de priorité reconstruite, `mettre-a-jour doc` : `hibou_llm_tokens_generes_total{modele="qwen3.5-4b",utilisateur="alice"} 48`. **Prouvé** (panneaux affichés au prochain passage de Prometheus).

## F13 — Contrôles automatiques sur GitHub (tâche 13)
- Workflow `.github/workflows/controles.yml` : `bash -n` et `shellcheck -S error` du script, compilation des Python des amorces et du miroir, JSON des amorces et de la charte,
  autotests du relecteur et du service de priorité, `hibou autotest`. Rejoué en local : tout passe. Fichiers `__pycache__` publiés par erreur retirés, `.gitignore` complété.

## F2, F5 — Mise en production et cluster à deux nœuds (tâches 2 et 5)
- `docs/mise-en-production.md` (GitHub) : liste de contrôle ordonnée (matériel et BIOS, bundle, installation, sécurité, sauvegarde, mise en service), chaque point vérifiable
  par une commande ; cluster à deux nœuds : témoin QDevice (`corosync-qnetd`, `pvecm qdevice setup`), placement des VM, réplication ZFS + HA ou stockage partagé pour forge,
  `pvecm expected 1` en dernier recours.

## B60 — L'import proposait un chemin sans dossier
- Constat (F8) : le 4B proposait `docs/redemarrer-serveur-dimpression.md` ; publié tel quel, le document sortait du dossier de son gabarit.
- Diff : `publier_forgejo` 0.4.2 range le document d'après le champ `modele` de son en-tête (`DOSSIERS`, comme les rédacteurs) et indique le chemin retenu.
- Test : `docs/x.md` + `modele: procedure` → `docs/procedures/x.md` ; chemin déjà correct ou sans en-tête : inchangé. **Prouvé** (essai unitaire de `ranger`).

## B61 — Nouvelles options jamais proposées à un bundle existant ; piège `set -e`
- Constat : « La garder » reprenait `config.env` sans poser les questions apparues depuis (documentation de sécurité, carte de recherche) ; « Changer seulement les cartes »
  ne posait pas celle de la sécurité. Et `(( HIBOU_RERANKER )) && note …` en fin de fonction rendait 1 sans carte de recherche : arrêt du script sous `set -e`.
- Diff : `questions_nouvelles` pose les questions absentes de `config.env` puis l'enregistre ; questions sécurité et carte de recherche en fonctions ; test réécrit en `== 0 ||`.

## B62 — `renouveler-secrets` supposait les trois VM sur le même hôte
- Constat : en production forge est sur le cluster, doc et dev sur leurs hôtes ; la commande aurait déclaré « VM doc arrêtée » et ne l'aurait pas mise à jour.
- Diff : `appliquer_role` : VM sur cet hôte → mise à jour complète ; VM d'un autre hôte joignable → copie du bundle et configuration par SSH (ni cartes, ni pilote, ni redémarrage) ;
  injoignable → la commande à lancer sur son hôte. Utilisé par `renouveler-secrets` et `comptes`.
- Test : `comptes priorite` avec doc traitée comme distante (`HIBOU_COMME_DISTANT=doc`) : « VM d'un autre hôte : configuration seulement », rangs de doc mis à jour. **Prouvé.**

## B63 — Un PowerPoint joint au chat n'était jamais lu
- Constat (test de 11 types de fichiers) : `.pptx` « failed », 0 caractère ; `unstructured` télécharge le modèle spaCy `en_core_web_sm` au premier PowerPoint (GitHub), impossible hors ligne.
- Diff : le bundle livre ce modèle (adresse et empreinte SHA-256 lues dans l'image Open WebUI livrée), installé dans `/app/hibou-spacy` et rendu importable par un `.pth`
  placé après `site-packages` (aucun module d'Open WebUI masqué) ; `hibou essai` contrôle Word, Excel, PowerPoint et PDF joints.
- Test : `spacy.load("en_core_web_sm")` hors ligne ; 11 types : txt, md, csv, json, py, html, docx, xlsx, **pptx**, pdf lus (code retrouvé), png par la vision ; essai : « Documents joints Word,
  Excel, PowerPoint, PDF : texte extrait des 4 formats ». **Prouvé.**

## B64 — Images jointes retirées pour la plupart des modèles du chat
- Constat : capture jointe à « Documentation interne » : « je n'ai pas accès à l'image » (378 s) ; seuls les rédacteurs déclaraient la vision, en dur (même sur un profil sans projecteur).
- Diff : la capacité `vision` suit le modèle principal de doc (vraie s'il est servi avec son projecteur), pour tous les modèles bâtis sur lui.
- Test : même capture : réponse en 10 à 13 s, lue à une lettre près (code de 5 lettres aléatoires ; limite de lecture du 4B). **Prouvé.**

## B65 — Miroir : échecs silencieux et outil jamais mis à jour
- Constats (miroir élargi) : 4 paquets refusés (pyserial : « Metadata-Version 2.0 » rejeté par twine ; nodemon, tailwindcss, napi-postinstall : « provenance » npm impossible hors ligne)
  mais « Fait  Paquets publiés » et empreinte enregistrée, donc jamais réessayés ; et forge ne chargeait l'image `miroir` du bundle que si elle n'en avait aucune.
- Diff : l'outil compte ses échecs et sort en erreur (le miroir n'est alors pas marqué importé) ; envoi direct par l'API PyPI de Forgejo quand twine refuse les métadonnées ;
  `npm publish --provenance=false` ; image `miroir` du bundle chargée à chaque import.
- Test : `hibou miroir` : « pypi : 1 publiés, 184 déjà présents ; npm : 3 publiés, 667 déjà présents ; import terminé », aucun échec. **Prouvé.**

## F14 — `hibou comptes` (demande de l'utilisateur)
- Personnes gérées sans tout réinstaller : `lister`, `ajouter <id> <courriel> <doc|dev|doc,dev> [rang]` (mot de passe initial demandé, ou sur l'entrée standard), `equipes`, `priorite`, `retirer`,
  ou menu. La liste vit dans `secrets.chiffre` (comptes retirés gardés, bloqués à chaque passage) ; appliquée à forge (compte Forgejo, équipes alignées, instance OpenCode, fichier
  d'accès), doc et dev (clé personnelle, rang dans la file), y compris sur d'autres hôtes (B62). Le premier menu peut se terminer sans personne. Chaque mise à jour de forge aligne les comptes.

## F15 — Tickets liés d'office, consignes de l'agent
- `forgejo-pr` ajoute « Closes #n » pour un ticket ouvert cité par la branche (`agent/<n>-<sujet>`) ou un commit (« #n ») ; consigne de l'agent : nommer ainsi la branche.
- Test (dépôt jetable, faux Forgejo) : branche `agent/12-…`, commit « voir #13 » (fermé) : « Ticket #12 lié » seulement. **Prouvé.**

## F16 — Miroir : sélection de départ, republication seulement s'il change
- Listes par défaut d'un nouveau bundle : 55 paquets Python, 31 npm, 11 images Docker, 2 dépôts git ; `--legacy-peer-deps` (une liste sans lien ne doit pas échouer sur un conflit « peer »).
  Empreinte du miroir notée après un import sans échec : mise à jour suivante « Miroir inchangé » (forge n° 74 : 4 min au lieu de 19).
- Test : 1,4 Go (184 fichiers Python pour 3.11 et 3.12, 670 paquets npm, 11 images) ; depuis l'agent : `pip install fastapi pandas pytest`, `npm install zod express` servis par Forgejo. **Prouvé.**

## F17 — OpenCode : seul le fournisseur Hibou, images jointes selon le modèle
- Constat : le sélecteur d'OpenCode proposait aussi « OpenCode Zen » (modèles hébergés sur opencode.ai : Flint 40B Free, Big Pickle…), injoignable ici et qui enverrait le code à un tiers.
- Diff : `enabled_providers: ["hibou"]` ; chaque modèle déclare `attachment` et `modalities` (images si servi avec son projecteur de vision).
- Test : fournisseurs exposés par l'instance d'alice : `hibou` seul ; configuration générée : 27B de dev (≥ 48 Go) avec images, Coder-Next et 4B sans. **Prouvé.**

## F18 — `hibou essai` : agent de code et documents bureautiques
- Avec dev en ligne : dépôt jetable avec un ticket, instance OpenCode temporaire au nom du compte d'essai (configuration générique, clé de service), l'agent doit traiter le ticket
  et ouvrir une PR non vide liée au ticket ; échec d'infrastructure = ÉCHEC, agent qui n'aboutit pas = ATTENTION (capacité du modèle). Formats Word, Excel, PowerPoint, PDF joints contrôlés.
- Test (dev en ligne, doc arrêtée) : **20 contrôles OK sur 20** en 5 min : « Agent de code (ticket → pull request) : 143 s, 2 fichier(s), ticket lié », « Relecture automatique : avis en 16 s ».
  Doc arrêtée, le chat a basculé sur le même modèle servi par dev (résilience d'Open WebUI) ; limite de l'essai : une réponse « sourcée » reste comptée quand les embeddings
  échouent (Open WebUI joint quand même des sources) ; `hibou diagnostic` signale doc injoignable.

## Pièces jointes : ce qui passe (demande de l'utilisateur)
- **Open WebUI** : texte, Markdown, CSV, JSON, code, HTML, Word, Excel, PowerPoint (B63), PDF : texte extrait et donné au modèle (B59) ; images : par la vision (B64), lues par le 4B
  à une lettre près sur un code aléatoire.
- **OpenCode** : l'interface joint images, PDF et texte. Texte : lu (code retrouvé en 13 s). PDF : refusé (« le système ne supporte pas l'entrée de fichiers PDF ») : llama.cpp ne
  lit pas les PDF ; passer par Open WebUI ou déposer le texte dans le dépôt. Images : seulement pour un modèle avec vision (27B de dev en production, pas le 4B d'essai) (F17).

## B66 — Après un redémarrage de doc, le modèle tournait sur le processeur
- Constat (essai final) : chat sans réponse en 300 s, puis 114 à 262 s par réponse ; carte à 1 Mio ; dans le conteneur llama-swap : `nvidia-smi` → « Failed to initialize NVML:
  Unknown Error ». Défaut connu de Docker avec les cartes NVIDIA : un `systemctl daemon-reload` (phase socle de la mise à jour) retire les cartes aux conteneurs déjà démarrés.
  La VM venait de redémarrer : conteneurs lancés au démarrage, puis mise à jour sans changement de leur configuration, donc jamais recréés.
- Diff : `cartes_conteneurs` en fin de configuration de doc et dev : chaque conteneur à carte NVIDIA qui ne la voit plus est relancé (erreur claire s'il ne la voit toujours pas) ;
  `hibou diagnostic` contrôle l'accès aux cartes depuis le serveur de modèles.
- Test : diagnostic : « ÉCHEC Serveur de modèles doc : pas d'accès aux cartes » ; `systemctl daemon-reload` dans doc (NVML : Unknown Error), `mettre-a-jour doc` sans changement
  de configuration : « hibou-doc-llama-swap-1 relancé : il avait perdu l'accès aux cartes », carte revue ; essai : 18 OK en 2 min. **Prouvé.**

## B67 — Deux projecteurs de vision téléchargés ; le BF16 préféré sur des cartes Turing
- Constat (vérification du bundle de production) : le motif `*mmproj*F16*` prenait aussi `mmproj-BF16.gguf` (~900 Mo de trop par modèle) et le script utilisait le BF16
  (premier par ordre alphabétique), format que les Quadro RTX 4000 (Turing) ne gèrent pas nativement.
- Diff : motif `*mmproj-F16*` ; `mmproj()` préfère `mmproj-F16.gguf`. Fichiers BF16 retirés des deux bundles, empreintes mises à jour et vérifiées.
- Régression introduite puis corrigée dans la foulée : `… | head -1` faisait recevoir un SIGPIPE au second `find` ; sous `pipefail`, `mettre-a-jour doc` s'arrêtait
  en pleine configuration (« no router for requested model »). Remplacé par `sed -n 1p` (lit tout), essayé sous `set -euo pipefail`.
- Test : A/B sur doc (llama-server temporaire, même image « KTRWB ») : BF16 et F16 lisent tous deux « KTREB » ; service doc en F16 : « KTREB » ; par Open WebUI : image transmise
  (« SOUKU » pour « SGGKU », précision du 4B). `mettre-a-jour doc` n° 16 rc=0. **Prouvé.**

## F19 — doc et dev au choix (demande de l'utilisateur)
- Menu : « Serveurs d'IA à déployer » : doc et dev, doc seulement, dev seulement (`HIBOU_ROLES`, les bundles plus anciens gardent les deux) ; adresses, VM, disques et cartes
  demandés pour les seuls serveurs retenus ; modèles téléchargés pour eux seuls ; `hibou installer <rôle non prévu>` refusé avec la marche à suivre.
- forge suit : supervision, DNS, routes `llm-*`, adresses d'Open WebUI (imposées en base), OpenCode (instances, page « agent de code non déployé »), relecteur
  (sans dev : notifications « PR à relire » seules), évaluation, comptes, rotation, essai et diagnostic. Sans doc : ni bases de connaissances ni modèles de rédaction
  (désactivés s'ils existaient), chat sur le modèle de dev ; l'outil de synchronisation de hibou-docs n'échoue plus sans clé du chat.
- Tests : menu « doc seulement » (bundle jetable) : aucune question sur dev, `HIBOU_ROLES=doc`, seuls les modèles de doc. Hôte d'essai passé en doc seul :
  OpenCode retiré, Caddy sans `llm-dev`, Prometheus sans dev, Open WebUI sur doc seul, relecteur « notifications seules », `installer dev` refusé ; essai **17 OK**.
  Passé en dev seul : chat sur le modèle de code, modèles de rédaction désactivés, OpenCode rétabli ; essai **14 OK** (agent de code et relecture réels).
  Retour à doc et dev : modèles de rédaction recréés ; essai 18 OK, diagnostic sans échec. **Prouvé.**

## B68 — Relecteur jamais réaligné en mise à jour
- Constat (F19) : `relecteur.env` n'était écrit que par `configurer` ; un changement de serveurs ou de profil de dev ne l'atteignait pas.
- Diff : `relecteur_llm` en mise à jour de forge : serveur et modèle de dev (ou aucun), relecteur recréé s'il change. Test : « Relecteur : notifications seules », puis « qwen3.5-4b ». **Prouvé.**

## B69 — Modèle d'un ancien profil toujours proposé dans le chat
- Constat : `qwen3.5-9b` (essai de profil 9B) restait actif alors qu'aucun serveur ne le sert : erreur si on le choisit.
- Diff : en mise à jour, les modèles de base actifs qui ne sont plus servis sont désactivés. Test : « Modèle qwen3.5-9b retiré du chat : plus servi ». **Prouvé.**

## F20 — Installation en ligne, sans disque de transport (demande de l'utilisateur)
- `hibou en-ligne [dossier]` sur l'hôte Proxmox connecté qui portera forge : VM de préparation créée d'office (image Ubuntu vérifiée, clé SSH dédiée, Docker et outils),
  même menu que `telecharger` (choix et secrets d'une préparation précédente repris), bundle rapatrié et vérifié, VM de préparation arrêtée et gardée pour les mises à jour,
  puis forge installée ou mise à jour ici, doc et dev ici ou sur l'hôte de leurs cartes (bundle copié par SSH root, comme entre nœuds d'un cluster) ; une VM arrêtée est signalée.
  Les VM Hibou restent sans Internet. Appels SSH de service en `ssh -n` (sinon ils avalent les réponses suivantes).
- Test (hôte d'essai) : premier passage : VM 299 créée et outillée, bundle de 19 Go préparé, rapatrié, vérifié ; forge et doc mises à jour, dev arrêtée signalée ; rc=0 ;
  essai **18 OK**. Place mesurée dans la VM de préparation : 45 Go pour un bundle de 19 Go (cache de Docker) : conseil porté à 60 / 300 Go.
- Second passage (mise à jour) : arrêté net (rc=1) : le rapatriement `rsync --delete` avait effacé le fichier de réglages de la VM de préparation, rangé dans le bundle.
  Diff : fichier exclu de la synchronisation, adresse relue dans la configuration Proxmox de la VM s'il manque (et réécrite). Rejoué : images « inchangée »,
  « 0 image(s) chargée(s) » sur forge et doc, « rien à redémarrer », rc=0 en 38 min. **Prouvé.**

## Écarts de charte non corrigés (décision ou limite)
- Open WebUI : « Connectez-vous à Hibou (Open WebUI) » : la mention « (Open WebUI) » est imposée par sa licence ; textes français au vouvoiement (« Comment puis-je vous aider aujourd'hui ? »),
  compilés dans des fichiers JavaScript au nom changeant à chaque version : non modifiés (bricolage fragile).
- Open WebUI, thème clair : blocs de code dessinés par l'éditeur intégré, restés clairs (la charte veut le terminal nuit dans les deux thèmes).
- OpenCode web : thèmes intégrés seulement, choisis et gardés par navigateur (`opencode-theme-id`) ; le thème `hibou` ne vaut que pour le terminal (TUI).
- Grafana (page de connexion contournée, voir B39), Uptime Kuma et ntfy : pas de personnalisation dans leurs versions libres ;
  Uptime Kuma permet un CSS et un logo sur ses pages de statut publiques seulement (à configurer dans son interface si on en publie une).

## Constats sur les agents (doc et dev), profil ≥ 4 Go
- Où vont les fichiers : **dev** (OpenCode, conteneur sur forge) écrit dans `/workspace/<projet>` = `/srv/workspace/<projet>` de la VM forge (uid 1000), un clone par projet.
  **doc** (Open WebUI) n'écrit aucun fichier : l'outil dépose le document par l'API de Forgejo, directement dans hibou-docs (`docs/<dossier>/<nom>.md`).
- Quand ça pousse : jamais à chaque étape. dev : un commit puis `forgejo-pr` (push de la branche `agent/<sujet>` + PR) quand le travail est fini ; jamais sur main (refusé par Forgejo depuis B22).
  doc : une branche `redaction/<chemin>-<date>` + un commit + une PR par document, seulement après validation par l'utilisateur (le prompt le demande).
- La fusion reste humaine dans les deux cas ; le runner vérifie les PR de hibou-docs.
- Limites du 4B (pas du script) : adresses inventées, boucles sur une commande en échec, `rm -rf .git` proposé (refusable dans l'interface), tests parfois vides.
  Résultats : terminal n° 2 complet en 2 min 12 s (PR ouverte) ; web n° 4 : code et 10 tests corrects, mais clone détruit et pas de PR.

## N4 — L'évaluation note les erreurs d'API comme des réponses

- Constat : une réponse `[erreur API : …]` reçoit 33 % (« en-tête, sections »), la synthèse affiche « 0.0 tokens/s » sans alerte. Un serveur en panne passe pour un modèle médiocre.
- Diff (`amorces/hibou-eval/evaluer.py`) : réponse `[erreur API …]` → score 0, remarque = l'erreur ; synthèse : « N tâche(s) sans réponse du serveur (erreur API) : scores non significatifs ».
- Test : compilation OK ; déployé sur forge par `mettre-a-jour forge` (avec B8).

## N1 — Avertissement apt « Did not understand pin type version » (sans effet)

- Constat : bundle du 2026-11-20 : 23 paquets NVIDIA, tous en 620.70.06 (`nvidia-driver-open`, `nvidia-dkms-open`, `libnvidia-compute`…), toolkit 1.20.2. `MANIFEST.md` annonce 620.70.06.
- Conclusion : le pilote est bien figé. L'avertissement est du bruit, pas un bogue bloquant. À revoir si le pilote installé dans la VM doc diffère (phase 3).

## Mesures de référence — profil ≥ 4 Go (une carte de 4 Go, processeur sans AVX2)

- `installer forge` sur une installation neuve : rc=0 ; `mettre-a-jour forge` : 2 à 3 min.
- `installer doc` : rc=0 ; 3,1 Go de mémoire vidéo ; évaluation doc **93 %**, vision **100 %**, 22 tokens/s, ~5 min.
- `installer dev` : rc=0 du premier coup (~15 min) ; 4B en contexte 32k + complétion sur le processeur : 3,7 Go au plus ; évaluation code **75 %**, 22 tokens/s.
- Complétion (1.5B Q8 sur le processeur) : 13 à 16 tokens/s seule. Un processeur avec AVX2 fera mieux.
- Agent OpenCode (4B) : de la demande à la PR en 2 à 5 min quand tout va bien ; voir B17, B18 et les constats ci-dessus pour les limites.
- Une carte par rôle GPU : doc et dev ne tournent pas ensemble sur une seule carte.
