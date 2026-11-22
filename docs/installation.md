# Installation pas à pas

Trois temps : préparer le bundle sur une machine connectée, l’apporter sur un disque, installer chaque rôle depuis
son hôte Proxmox. Les commandes d’installation se lancent en root sur l’hôte ; le script crée lui-même les VM.

## 0. Avant de commencer

- **Hôtes GPU** (doc, dev) : Proxmox VE 9 (version essayée), cartes NVIDIA, BIOS avec la virtualisation (VT-x/VT-d ou AMD-V/IOMMU)
  et « Above 4G decoding » activés. Le script vérifie l’IOMMU et confie les cartes à `vfio-pci` sans redémarrer l’hôte.
- **forge** : un nœud Proxmox quelconque (ou un cluster). 2 cœurs, 12 Go de RAM et 80 Go de disque au minimum.
- **Stockages Proxmox** : un pour les disques des VM, un pour les sauvegardes de forge (type « VZDump backup file »).
- **Réseau** : un pont Proxmox (par exemple `vmbr1`) relié au réseau isolé, et quatre adresses libres (forge, doc, dev,
  plus celles des hôtes). Aucune passerelle vers Internet n’est nécessaire.
- **Machine connectée** : Ubuntu avec Docker, python3-venv, git, zstd, openssl, rsync, et un **disque séparé** pour le
  bundle (20 à 300 Go selon les profils). Le script refuse d’écrire le bundle sur le disque système.

## 1. Préparer le bundle

```bash
./hibou autotest
./hibou telecharger /mnt/hibou/bundle
```

Le menu demande :

| Question | Exemple |
| --- | --- |
| Serveurs d’IA | doc et dev, doc seulement ou dev seulement : seules les questions et les modèles utiles suivent |
| Domaine | `hibou.lan` |
| Réseau, passerelle | `10.99.0.0/24`, vide |
| Pont, VLAN | `vmbr1`, vide |
| Adresses forge, doc, dev | `10.99.0.10`, `10.99.0.20`, `10.99.0.30` |
| Adresses des hôtes Proxmox doc et dev | celles de leurs hôtes (identiques si un seul hôte) |
| Numéros de VM, disques | `210`, `220`, `230` ; 80, 150, 150 Go |
| forge : mémoire, cœurs | 12 Go, 2 |
| Stockages | disques des VM, sauvegardes |
| Cartes de dev et de doc | modèle et nombre ; le profil conseillé suit la mémoire vidéo |
| Génération d’images | « Non », ou une carte dédiée |
| Carte de recherche (doc) | « Oui » si l’hôte doc a une petite carte en plus (4 à 8 Go) : elle porte les embeddings et le reranker au lieu de ralentir le LLM |
| Miroir | versions de Python, listes pip, npm, git, images Docker |
| Documentation de sécurité | « Oui » : guides de l’ANSSI (environ 170 Mo) et tes textes de référence (`securite.d/autres.txt`, `securite.d/ajouts/`) pour la base « Hibou · Sécurité » |
| Administrateur, utilisateurs | dans l’ordre de priorité ; équipes doc, dev ou les deux. La liste peut rester vide : `hibou comptes` après l’installation |
| Phrase de passe | chiffre les secrets du bundle |

Puis contrôle et taille :

```bash
./hibou verifier /mnt/hibou/bundle
du -sh /mnt/hibou/bundle
```

Un second passage (« La garder », versions gardées) ne retélécharge rien qui n’a pas changé.
Lance toujours `telecharger` avec le même utilisateur.

## 2. Apporter le bundle

Démonte le disque et branche-le sur l’hôte Proxmox de forge (ou copie le dossier). Puis, sur cet hôte :

```bash
cd /mnt/hibou/bundle
./hibou verifier
```

## 3. forge

```bash
./hibou installer forge
```

Le script crée la VM, installe Docker, Forgejo, Open WebUI, OpenCode, Caddy, la supervision, le runner, le relecteur,
publie le miroir et configure la connexion unique (y compris celle de Proxmox par Forgejo). Il écrit sur forge
`/root/hibou-acces.txt` : clés d’API des utilisateurs, adresses, commande Proxmox.

## 4. doc et dev

Sur l’hôte des cartes doc, puis sur celui des cartes dev :

```bash
./hibou installer doc
./hibou installer dev
```

Un hôte partagé avec d’autres VM : limite la VM GPU avec `HIBOU_RAM_GPU=<Go> HIBOU_CPU_GPU=<fils>`.
À la fin, le script vérifie `nvidia-smi`, l’API du serveur, et lance une première évaluation des modèles.

Si doc est installé après forge (cas normal), relance une fois `./hibou mettre-a-jour forge` : la base
« Hibou · Templates » du chat a besoin des embeddings de doc pour se remplir.

## 5. Postes clients

- Résolution des noms : utilise forge comme DNS (il sert tout le domaine), ou ajoute dans `/etc/hosts` l’adresse de
  forge pour `forge`, `chat`, `code`, `docs`, `supervision`, `etat`, `alertes`, `registry`, `llm-doc`, `llm-dev`.
- Certificat : installe l’autorité de Hibou, `/srv/hibou/hibou-ca.crt` sur forge.
- Ouvre `https://forge.<domaine>` : chaque compte change son mot de passe à la première connexion, puis se connecte
  partout avec Forgejo.

## 6. Mettre à jour

```bash
./hibou telecharger /mnt/hibou/bundle      # sur la machine connectée, même disque
./hibou mettre-a-jour forge                # puis doc, dev selon ce qui a changé
```

Seul ce qui a changé est copié et rechargé ; comptes, dépôts, conversations et sessions de l’agent sont conservés.
Ensuite : `./hibou diagnostic` sur chaque hôte et `./hibou essai` sur l’hôte de forge.

## Comptes des personnes

```bash
./hibou comptes                                   # menu : ajouter, équipes, priorité, retirer
./hibou comptes lister
./hibou comptes ajouter carole carole@hibou.lan doc,dev 2   # rang 2 dans la file ; mot de passe initial demandé
./hibou comptes equipes carole dev
./hibou comptes priorite carole 1
./hibou comptes retirer carole                    # connexion bloquée ; dépôts et espace de travail gardés
```

Chaque changement met à jour `secrets.chiffre` du bundle puis s’applique à forge (compte Forgejo, équipes, instance
OpenCode), doc et dev (clé personnelle et rang dans la file). Une VM sur un autre hôte est mise à jour par SSH
(configuration seulement) ; si elle est injoignable, la commande dit quoi lancer sur son hôte. Les clés personnelles
sont dans `/root/hibou-acces.txt` sur forge.
Pour changer de cartes ou de profil : « Changer seulement les cartes et les modèles » au menu de `telecharger`.

## 7. Dépannage

| Symptôme | Que faire |
| --- | --- |
| Quelque chose ne va pas, sans savoir quoi | `./hibou diagnostic` sur l’hôte : un rapport sans secret dans `/root`, à joindre à un ticket |
| Un secret a pu être vu | `./hibou renouveler-secrets` sur l’hôte de forge : nouvelles clés, anciens jetons révoqués |
| Une étape échoue | Lis le message, corrige, relance la même commande : les étapes faites sont rapides. `HIBOU_SAUTER=vm,copie` pour en sauter. |
| « Service(s) qui redémarrent en boucle » | `docker compose -f /srv/forgejo/compose.yaml logs --tail 50 <service>` sur forge |
| Le chat ne répond pas | `curl http://<ip-doc>:8080/health` depuis forge ; depuis ailleurs, c’est refusé (pare-feu) |
| L’agent ne trouve pas un paquet | Ajoute-le aux listes du miroir, puis `telecharger` et `mettre-a-jour forge` |
