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
  `linux-headers-virtual` 43 exige `linux-headers-generic (= 43)` : apt doit le retirer, `--no-remove` refuse. Se reproduira sur les R730 dès que le noyau du bundle dépasse celui de l'image.
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
