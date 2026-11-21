<pre>
   /\_/\
  ( o o )   Hibou
   > ^ <    L’IA qui veille chez vous.
</pre>

Hibou installe, dans un réseau sans Internet, deux IA locales : une IA de **documentation** (rédaction, vision,
recherche dans la documentation) et une IA de **développement** (agent de code, autocomplétion, relecture),
avec Forgejo comme dépôt commun. Un seul script Bash, `hibou`, prépare tout sur une machine connectée puis
installe chaque rôle sur des hôtes Proxmox, sans question.

**Local.** Les modèles tournent sur tes cartes NVIDIA, servis par llama.cpp et llama-swap.
**Isolé.** Aucune connexion sortante. Tout entre par un bundle vérifié.
**Discret.** Il veille, il ne bavarde pas.

## Ce que tu obtiens

- **Chat et rédaction** (`chat.<domaine>`) : cinq rédacteurs (procédure, fiche technique, guide, architecture, décision),
  export Word, PDF, PowerPoint et Excel téléchargeable dans la conversation, publication dans Forgejo par pull request,
  questions-réponses sur la documentation validée, compression automatique des longues conversations.
- **Agent de code** (`code.<domaine>`) : une instance OpenCode par développeur, hors ligne (pip et npm par le miroir),
  qui crée le dépôt, travaille sur une branche et ouvre la pull request ; `main` toujours protégée.
- **Relecture et documentation** : avis automatique sur chaque pull request, contrôle des documents par un runner,
  fusion humaine, site `docs.<domaine>` et base de connaissances mis à jour à chaque fusion.
- **Priorité** : une clé par personne ; quand le serveur est occupé, le mieux classé passe en premier.
- **Exploitation** : connexion unique par Forgejo (chat, agent, supervision, Proxmox), Grafana, alertes, évaluation
  hebdomadaire des modèles, sauvegarde nocturne, mises à jour qui n’apportent que ce qui a changé.

Liste complète, avec l’état de chaque fonction à l’essai : [docs/FONCTIONNALITES.md](docs/FONCTIONNALITES.md).

## Matériel

Trois rôles, chacun dans une VM Proxmox créée par le script :

| Rôle | Où | Besoin |
| --- | --- | --- |
| `forge` | Un nœud Proxmox (ou un cluster) | 2 cœurs, 12 Go de RAM, 80 Go de disque au minimum |
| `doc` | Hôte avec une ou plusieurs cartes NVIDIA | Cartes en passthrough (IOMMU), 4 Go de mémoire vidéo au minimum |
| `dev` | Hôte avec une ou plusieurs cartes NVIDIA | Idem ; peut être le même hôte que doc si chacun a ses cartes |

Le profil de modèles suit la mémoire vidéo du serveur (plusieurs cartes s’additionnent) :

| Mémoire vidéo | dev | doc |
| --- | --- | --- |
| ≥ 4 Go | Qwen3.5 4B, contexte 32k | Qwen3.5 4B, vision, contexte 8k |
| ≥ 12 Go | Qwen3.5 9B, 64k + complétion 1.5B | Qwen3.5 9B, 32k |
| ≥ 24 Go | Qwen3.8 27B Q4, 64k + complétion 3B | Gemma 4 26B Q4 (64k) ou Qwen3.8 27B Q4 (32k), vision |
| ≥ 48 Go | Qwen3-Coder-Next Q3 ou Qwen3.8 27B Q8 + complétion 7B | Gemma 4 26B Q8 ou Qwen3.8 27B Q8, 128k |
| ≥ 90 Go | Qwen3-Coder-Next Q6 (256k) ou Qwen3.8 27B Q8, complétion 7B | — |

Cartes proposées au menu : RTX PRO 6000 Blackwell, RTX 6000 Ada, L40S, RTX A6000, RTX 5000 Ada, RTX 4000 Ada,
RTX A4000, RTX A2000 12 Go, Quadro RTX 4000, RTX A400, ou toute autre carte en indiquant sa mémoire.
Une carte supplémentaire peut porter la génération d’images (ComfyUI).

## Démarrage

Sur la machine connectée (Ubuntu, Docker), bundle sur un disque à part :

```bash
./hibou autotest
./hibou telecharger /mnt/hibou/bundle
./hibou verifier /mnt/hibou/bundle
```

Sur chaque hôte Proxmox, en root, disque du bundle branché :

```bash
./hibou installer forge   # en premier
./hibou installer doc     # sur l’hôte des cartes doc
./hibou installer dev     # sur l’hôte des cartes dev
./hibou installer noeud   # facultatif : supervision des autres nœuds
```

Mise à jour : relancer `telecharger` sur le même disque, puis `./hibou mettre-a-jour <rôle>` sur chaque hôte.
Pas à pas : [docs/installation.md](docs/installation.md). Aide-mémoire du bundle : [docs/LISEZMOI-0.9.0.md](docs/LISEZMOI-0.9.0.md).

## Adresses

| Service | Adresse |
| --- | --- |
| Chat, rédaction, export de fichiers | `https://chat.<domaine>` |
| Agent de code | `https://code.<domaine>` |
| Documentation validée | `https://docs.<domaine>` |
| Forgejo | `https://forge.<domaine>` |
| Supervision, état, alertes | `https://supervision.<domaine>`, `https://etat.<domaine>`, `https://alertes.<domaine>` |
| API (clé par utilisateur) | `https://llm-doc.<domaine>/v1`, `https://llm-dev.<domaine>/v1` |

## État

Version 0.9.0, validée de bout en bout sur une machine d’essai (un hôte Proxmox, une carte de 4 Go, processeur
sans AVX2) : préparation du bundle, installation des trois rôles, chat, rédaction et publication, export de fichiers,
agent de code, relecture, priorité, évaluation. Chaque bogue trouvé est décrit, corrigé et prouvé dans
[JOURNAL-CORRECTIONS.md](JOURNAL-CORRECTIONS.md). Restent à valider sur du matériel plus gros : les profils au-delà
de 4 Go, le décodage spéculatif, la génération d’images, la restauration d’une sauvegarde.

## Documentation

- [Fonctionnalités](docs/FONCTIONNALITES.md)
- [Installation pas à pas](docs/installation.md)
- [Architecture](docs/architecture.md)
- [Journal des corrections](JOURNAL-CORRECTIONS.md) · [Changelog](CHANGELOG.md)
- [Charte graphique](charte/LISEZMOI.md) : jetons, composants, logos, icônes, polices
- [Contribuer](CONTRIBUTING.md) · [Sécurité](SECURITY.md)

## Licence

[MIT](LICENSE).
