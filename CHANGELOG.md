# Changelog

## 0.9.0 — corrections d'essai
Détail, symptômes et preuves : `JOURNAL-CORRECTIONS.md`.
- Profil « ≥ 4 Go » (`doc:4`, `dev:5`) : projecteur vision et complétion sur le processeur, raisonnement coupé (évaluations doc 93 %, vision 100 %, code 75 %).
- `telecharger` : plus de bruit `debconf` (B1), premier passage des images (B2), « La garder » relit `config.env` (B3), images locales non reconstruites sans changement (B4).
- Installation : apt lit le bundle local (B5), clé SSH de l'agent en 600 (B6), métapaquets noyau `virtual` retirés avant le pilote (B11),
  domaine Proxmox `forgejo` modifiable (B12), pare-feu ouvert à `lo` (B13) et réappliqué en mise à jour (B14).
- Miroir : PyPI publié fichier par fichier sans mot de passe dans les journaux (B7), dépôts git complets (B9) et acceptés par git (B10).
- Open WebUI : base Templates remplie dès que doc répond (B8), embeddings sans 429 (B15), synchronisation de la documentation par `reset` (B16).
- Évaluation : une erreur d'API compte 0 et est signalée (N4).
- Agent OpenCode : sortie réservée = contexte / 4 (B17 : il compactait à chaque tour) ; `dev:5` en contexte 32k ; `pytest` dans l'image,
  consignes « Hors ligne », commandes `forgejo-nouveau-depot` et `forgejo-pr`, refus immédiats (`apt`, `su`, `--index-url`…), consignes rejouées en mise à jour (B18).
- Open WebUI : les 8 modèles (dont « Documentation interne ») sont créés ou mis à jour, sans `|| true` (B21).
- Agent dev : `main` protégée dans chaque dépôt qu'il crée, rien à la racine de /workspace, `rm -r … .git` refusé (B22) ; le relecteur signale ses échecs dans la PR (B23).
- Relecteur : au plus 10 remarques, pénalité de répétition, doublons retirés (B24 : le 4B bouclait jusqu'à la limite).
- OpenCode : **une instance par personne** de l'équipe dev (espace, conversations conservées aux mises à jour, clé de priorité, commits à son nom) (B30, B27).
- Agent dev : plus de création de dépôt par push, miroir pip toujours compatible avec le Python de l'agent (B25) ; secrets jamais affichés (B26) ;
  `.gitignore` de départ et consigne sur les liens `/compare/` (B29). Mise à jour : arrêt si un conteneur redémarre en boucle (B28).
- Profils : `dev:2` en Coder-Next Q3 et `doc:2` en Gemma Q4 pour tenir dans 48 et 24 Go, complétion 7B téléchargée une seule fois (A2).
- Rédaction : `publier_forgejo` 0.2.0 met le Markdown aux règles du runner avant publication (B19) ; l'outil est mis à jour à chaque `mettre-a-jour forge` (B20).

## 0.1.0
- Script `hibou` : `telecharger`, `verifier`, `installer` (pve, forge, doc, dev).
- Documentation : installation, architecture (document complet).
- Charte Hibou : `tokens.css`, composants, polices, logos, icônes.
