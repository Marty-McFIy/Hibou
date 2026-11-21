# Fonctionnalités de Hibou 0.9.0

Hibou installe, dans un réseau sans Internet, deux IA locales (rédaction et code) et tout ce qu’il faut autour :
dépôts, connexion unique, documentation, supervision, sauvegardes. Un seul script, `hibou`, fait tout.

État à l’essai : **Validé** (testé de bout en bout sur une machine d’essai), **À valider** (non testable sur la
machine d’essai : une seule carte de 4 Go, pas d’AVX2), **Prévu** (pas encore fait).

## 1. Préparer le bundle (machine connectée)

| Fonctionnalité | Détail | État |
| --- | --- | --- |
| Menu unique | Réseau, VM, cartes de chaque serveur, profil de modèles, miroir, administrateur, utilisateurs par ordre de priorité, phrase de passe | Validé |
| Profils selon la mémoire vidéo | dev : ≥ 4, 12, 24, 48, 90 Go ; doc : ≥ 4, 12, 24, 48 Go. Le profil conseillé suit la mémoire totale (plusieurs cartes s’additionnent) | Validé (4 Go), à valider au-delà |
| Tout ce qui sert à l’installation | Paquets Ubuntu et Proxmox, image cloud Ubuntu, 14 images Docker figées par empreinte, images construites localement, modèles Hugging Face, pilote NVIDIA figé | Validé |
| Miroir de dépendances | Paquets pip (plusieurs versions de Python, dont toujours celle de l’agent), npm, dépôts git, images Docker, publiés dans Forgejo | Validé |
| Versions figées | `versions.lock` : empreinte de chaque image, version d’OpenCode, révision de chaque modèle, modules d’export | Validé |
| Reprise sans tout retélécharger | Second passage : seules les parties changées sont refaites (`HIBOU_PARTIES`, `HIBOU_ACTUALISER`) | Validé (5 min au lieu de plusieurs heures) |
| Contrôle d’intégrité | `SHA256SUMS`, `MANIFEST.md`, `hibou verifier` | Validé |
| Secrets chiffrés | `secrets.chiffre` (AES-256, PBKDF2), phrase de passe demandée une fois par installation | Validé |

## 2. Installer (hôtes Proxmox)

| Fonctionnalité | Détail | État |
| --- | --- | --- |
| Installation sans question | `hibou installer forge|doc|dev|noeud` : VM créée par cloud-init, bundle copié, tout installé et vérifié | Validé |
| Passthrough des cartes | Cartes confiées à `vfio-pci` sans redémarrer l’hôte, ajoutées à la VM, vérifiées par `nvidia-smi` | Validé (1 carte) |
| Hôte partagé | `HIBOU_RAM_GPU`, `HIBOU_CPU_GPU` : mémoire et fils de la VM GPU | Validé |
| Mise à jour | `hibou mettre-a-jour <rôle>` : n’apporte que ce qui a changé, garde comptes, secrets, conversations et dépôts ; ne redémarre que les services dont la configuration change ; s’arrête si un service redémarre en boucle | Validé |
| Changement de profil | « Changer seulement les cartes et les modèles » : ancien modèle retiré du bundle et de la VM, chat et évaluation rebranchés automatiquement | Validé (4B → 9B → 4B) |
| Pare-feu | Les ports des serveurs GPU ne s’ouvrent qu’à forge (nftables) | Validé |
| Réseau isolé | DNS et heure servis par forge, autorité de certification interne, TLS partout | Validé |
| Supervision des autres nœuds | `hibou installer noeud` | À valider |
| Diagnostic | `hibou diagnostic` : stockages, quorum, cartes, sauvegarde, VM, conteneurs, sites, certificats ; rapport sans secret | Validé |
| Essai de bout en bout | `hibou essai` : compte temporaire, connexion par Forgejo au chat, à OpenCode et à Grafana, réponses sourcées, fichier joint, export, PR, runner, relecture, notifications ; 17 contrôles en 1 min | Validé |
| Rotation des secrets | `hibou renouveler-secrets` : nouvelles clés d’API, jetons des comptes de service (anciens révoqués), applications de connexion, secret du webhook | Validé |

## 3. Serveurs de modèles (doc et dev)

| Fonctionnalité | Détail | État |
| --- | --- | --- |
| llama.cpp + llama-swap | Modèles chargés à la demande, contexte réel déclaré, cache KV en q8_0, une requête à la fois par modèle | Validé |
| File de priorité | Chaque utilisateur a sa clé ; quand une place se libère, le mieux classé passe. Rien n’est interrompu | Validé (alice avant bob) |
| API compatible OpenAI | `https://llm-doc.<domaine>/v1`, `https://llm-dev.<domaine>/v1`, clé par utilisateur | Validé |
| Vision | Lecture de captures et de schémas (projecteur multimodal) | Validé (4/4 à l’évaluation) |
| Embeddings | Qwen3-Embedding sur le processeur, pour la recherche dans la documentation | Validé |
| Autocomplétion de code | Modèle FIM dédié, pour les éditeurs | Validé (12 à 16 tokens/s sur le processeur) |
| Décodage spéculatif | Petit modèle d’ébauche pour accélérer le 27B de dev (option du menu) | À valider |
| Génération d’images | ComfyUI sur une carte dédiée (option du menu) | À valider |
| Fonctionnement sans AVX2 | Serveur, embeddings et complétion sur processeur ancien | Validé |
| Carte de recherche | Une petite carte à part porte les embeddings et le reranker, hors du partage des couches du LLM ; chaque modèle épinglé à ses cartes | À valider sur matériel (essai à blanc fait) |
| Recherche hybride et reranker | Mots-clés et sens, puis tri des extraits par un reranker (Qwen3-Reranker 0.6B) ; actif avec la carte de recherche | Validé sur processeur (trop lent sans carte) |

## 4. Chat et rédaction (Open WebUI, `chat.<domaine>`)

| Fonctionnalité | Détail | État |
| --- | --- | --- |
| Connexion par Forgejo | Pas de mot de passe propre au chat ; équipes `doc` et `dev` | Validé |
| Cinq rédacteurs Hibou | Procédure, fiche technique, guide utilisateur, architecture, décision : chacun suit son modèle de document | Validé |
| Publication dans Forgejo | L’outil `publier_forgejo` dépose le document validé dans `hibou-docs`, sur une branche au nom de la personne, et ouvre une pull request | Validé |
| Export de fichiers | L’outil `exporter_document` crée un `.docx`, `.pdf`, `.pptx`, `.xlsx` ou `.md` aux couleurs Hibou, attaché à la réponse et téléchargeable | Validé |
| Documentation interne | Modèle qui répond à partir de la documentation fusionnée, avec ses sources | Validé |
| Compression du contexte | Une conversation trop longue est résumée automatiquement au lieu d’échouer ; les derniers messages restent intacts. Bouton « Compression du contexte » dans le menu « + » (actif par défaut) et réglage personnel « Ne jamais compresser » | Validé |
| Base « Hibou · Sécurité » (option) | Guides et recommandations de l’ANSSI récupérés à la préparation du bundle, plus tes textes de référence (IGI 1300, II 901…) ; modèle « Hibou · Sécurité » qui cite le guide utilisé | Validé (indexation en tâche de fond) |
| Import d’un document | Modèle « Hibou · Import d’un document » : un Word ou un PDF repris fidèlement dans le gabarit le plus proche, puis proposé par PR | Validé |
| Documents joints | Le texte d’un fichier joint au message est donné au modèle | Validé |
| Mise à jour d’un document publié | Lire un document de la documentation et en proposer une nouvelle version par pull request | Validé (outil installé) |
| Espace personnel | Conversations et fichiers propres à chaque compte : personne ne voit ceux des autres | Validé |
| Charte Hibou | Thème nuit et brume, polices, logo, écran de démarrage, suggestions, modèle par défaut ; contrastes AA dans les deux thèmes | Validé (textes d’Open WebUI au vouvoiement) |

## 5. Agent de code (OpenCode, `code.<domaine>`)

| Fonctionnalité | Détail | État |
| --- | --- | --- |
| Une instance par développeur | Son espace `/workspace`, ses conversations (conservées aux mises à jour), sa clé de priorité ; commits à son nom | Validé |
| Hors ligne | pip et npm passent par le miroir de Forgejo, pytest fourni, consignes adaptées | Validé |
| Nouveau projet en une commande | `forgejo-nouveau-depot` crée le dépôt, protège `main`, le clone, pose un `.gitignore` | Validé |
| Pull request en une commande | `forgejo-pr` pousse la branche `agent/<sujet>` et ouvre la PR, « Demandé par @<personne> » | Validé |
| Tickets | `forgejo-tickets` liste les tickets ouverts du projet ; « Closes #n » dans la PR les ferme à la fusion | Validé |
| Jamais de PR vide | `forgejo-pr` refuse s’il reste des modifications non commitées ou si la branche n’a aucun commit | Validé |
| Garde-fous | `main` protégée partout, pas de création de dépôt par push, refus d’office : `sudo`, `apt`, `rm -rf .git`, affichage des secrets… | Validé |
| Compaction automatique | OpenCode résume la session quand elle approche de la limite du modèle | Validé |

## 6. Forgejo, relecture et documentation

| Fonctionnalité | Détail | État |
| --- | --- | --- |
| Organisation prête | Équipes `dev`, `doc`, `relecture` ; comptes des utilisateurs et des agents ; dépôts `hibou-infra`, `hibou-docs`, `hibou-eval` amorcés et protégés | Validé |
| Relecteur automatique | Chaque pull request reçoit un avis consultatif du LLM de dev ; s’il est indisponible, la PR le dit | Validé |
| Relecture appuyée sur l’ANSSI | Avec la base sécurité, le relecteur joint les recommandations proches du code et cite le guide | Validé |
| Contrôle des documents | Runner Forgejo Actions : style Markdown, sections du modèle, schémas Mermaid | Validé |
| Fusion humaine | Une approbation requise, push direct sur `main` refusé | Validé |
| Site de documentation | `docs.<domaine>` (MkDocs, charte Hibou), reconstruit à chaque fusion ; tout ce qui est fusionné y apparaît | Validé |
| Base de connaissances à jour | Chaque fusion, et chaque mise à jour de forge, remet « Hibou · Documentation » à l’image de `main` ; les nouveaux outils arrivent par pull request | Validé |
| Paquets | Registres pip, npm et conteneurs de Forgejo, remplis par le miroir | Validé |

## 7. Supervision, évaluation, sauvegardes

| Fonctionnalité | Détail | État |
| --- | --- | --- |
| Grafana | « Vue d’ensemble », « LLM en direct » (file, contexte utilisé, tokens/s), « Évaluation » ; connexion par Forgejo | Validé |
| Alertes | Prometheus, Alertmanager, notifications ntfy (`alertes.<domaine>`, sujet `hibou`, administrateurs), page d’état Uptime Kuma (`etat.<domaine>`) | Validé (en place) |
| Notifications d’équipe | Sujet ntfy `hibou-pr` : PR à relire, relecture prête ou impossible ; ouvert aux équipes doc et dev | Validé |
| Usage par personne | Tokens lus et générés par personne sur 7 jours, dans « LLM en direct » : pour dimensionner les cartes | Validé |
| Évaluation des modèles | `hibou-eval` chaque dimanche : code, rédaction, vision ; scores dans Grafana ; une erreur d’API compte 0 | Validé |
| Sauvegardes | vzdump de forge chaque nuit (7 jours, 4 semaines) et export Forgejo ; une sauvegarde manuelle compte aussi | Validé (restauration complète, données intactes) |
| Connexion à Proxmox par Forgejo | Domaine OpenID `forgejo`, administrateur Hibou administrateur de Proxmox | Validé (connexion complète) |

## 8. Ce qui reste à faire

- Valider sur du vrai matériel les profils au-delà de 4 Go, le décodage spéculatif et la génération d’images.
- Mesurer les durées sur disques SSD et le passage à plusieurs cartes.
