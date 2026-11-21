# Hibou 0.9.0

IA locale en air gap : deux serveurs à cartes NVIDIA sous Proxmox (doc et dev), une VM par serveur avec les cartes
en passthrough, toutes les applications dans une VM « forge ». Une seule commande prépare le bundle sur une machine
connectée, une autre installe chaque rôle sans question. De 4 Go à plus de 90 Go de mémoire vidéo par serveur.

## 1. Machine connectée (Ubuntu, Docker)

    ./hibou autotest
    ./hibou telecharger /mnt/hibou/bundle

Questions : réseau, VM, cartes et nombre pour doc et dev (le profil de modèles est proposé selon la mémoire),
carte d’images, miroir de dépendances, administrateur, utilisateurs **dans l’ordre de priorité**, phrase de passe.
Les mots de passe et clés sont chiffrés dans `secrets.chiffre` (AES-256, PBKDF2). Le bundle doit être sur un disque
à part (pas le disque système). Puis : `./hibou verifier /mnt/hibou/bundle`.

## 2. Infrastructure isolée (root sur l’hôte Proxmox, disque branché)

    ./hibou installer forge   # en premier, sur un nœud du cluster
    ./hibou installer doc     # sur l’hôte des cartes doc
    ./hibou installer dev     # sur l’hôte des cartes dev
    ./hibou installer noeud   # facultatif : supervision des autres nœuds

Tout est automatique : phrase de passe demandée une fois, puis 30 s pour choisir des étapes à sauter
(ou `HIBOU_SAUTER=vm,copie`). Le script crée la VM (image cloud Ubuntu, cloud-init), confie les cartes
à vfio-pci, copie le bundle, installe, redémarre la VM et vérifie les GPU et l’API.
Un hôte partagé : `HIBOU_RAM_GPU=24 HIBOU_CPU_GPU=4 ./hibou installer doc` (mémoire en Go, fils).

BIOS des hôtes GPU : virtualisation (VT-x/VT-d ou AMD-V/IOMMU) et « Above 4G decoding » activés.

## Mise à jour (nouveau modèle, nouvelle carte, nouvelles images)

Sur la machine connectée, avec le même disque :

    ./hibou telecharger /mnt/hibou/bundle     # « Changer seulement les cartes et les modèles », ou « La garder »

Seul ce qui a changé est téléchargé et réécrit. Puis sur chaque hôte concerné :

    ./hibou mettre-a-jour dev    # ou doc, forge

Images et modèles inchangés ne sont ni recopiés ni rechargés ; la VM ne redémarre que si le pilote ou le noyau changent.
Une carte ajoutée sur l’hôte est passée à la VM automatiquement. Les conversations, comptes et dépôts sont conservés.

## Versions figées

Le premier bundle note dans `versions.lock` l’empreinte de chaque image, la version d’OpenCode, le commit
de ComfyUI, la révision de chaque modèle et les modules Python d’export. Les bundles suivants reprennent ces versions.
Pour actualiser : réponds au menu, ou `HIBOU_ACTUALISER=open-webui,opencode ./hibou telecharger …` (`tout` pour tout).

## Sauvegardes

La VM forge est sauvegardée chaque nuit à 3 h (vzdump, 7 jours et 4 semaines) vers le stockage choisi au menu,
obligatoire. Forgejo fait en plus son propre export à 2 h. Les VM doc et dev ne sont pas sauvegardées : elles se
reconstruisent entièrement depuis le bundle.

## Adresses

| Service | Adresse |
|---|---|
| Chat, rédaction, export Word/PDF, images | https://chat.<domaine> |
| OpenCode (une instance par développeur) | https://code.<domaine> |
| Documentation validée | https://docs.<domaine> |
| API doc / dev (clé par utilisateur) | https://llm-doc.<domaine>/v1, https://llm-dev.<domaine>/v1 |
| Forgejo, supervision, état, alertes | https://forge.<domaine>, https://supervision.<domaine>, https://etat.<domaine>, https://alertes.<domaine> |

Clés d’API et commande Proxmox OIDC : `/root/hibou-acces.txt` sur forge.
Au premier passage, chaque compte change son mot de passe dans Forgejo, puis se connecte partout avec lui.
