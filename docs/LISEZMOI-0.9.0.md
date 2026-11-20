# Hibou 0.9.0

IA locale en air gap : deux R730 sous Proxmox (doc et dev), une VM par R730 avec les cartes en passthrough,
toutes les applications dans une VM « forge » sur le cluster existant.

## 1. Machine connectée (Ubuntu, Docker)

    ./hibou telecharger /mnt/hibou/bundle

Questions : réseau, VM, cartes et nombre pour doc et dev, carte d'images, modèles,
administrateur, utilisateurs **dans l'ordre de priorité**, phrase de passe.
Les mots de passe et clés sont chiffrés dans `secrets.chiffre` (AES-256, PBKDF2).

## 2. Infrastructure isolée (root sur l'hôte Proxmox, disque branché)

    ./hibou installer forge   # sur un nœud du cluster, en premier
    ./hibou installer doc     # sur le R730 doc
    ./hibou installer dev     # sur le R730 dev
    ./hibou installer noeud   # facultatif : supervision des autres nœuds

Tout est automatique : phrase de passe demandée une fois, puis 30 s pour choisir des étapes à sauter
(ou `HIBOU_SAUTER=vm,copie`). Le script crée la VM (image cloud Ubuntu, cloud-init), confie les cartes
à vfio-pci, copie le bundle, installe, redémarre la VM et vérifie les GPU et l'API.

BIOS des R730 : Virtualization Technology et « Memory Mapped I/O above 4GB » activés.

## Mise à jour (nouveau modèle, nouvelle carte, nouvelles images)

Sur la machine connectée, avec le même disque :

    ./hibou telecharger /mnt/hibou/bundle     # « Changer seulement les cartes et les modèles », ou « La garder »

Seul ce qui a changé est téléchargé et réécrit. Puis sur chaque hôte concerné :

    ./hibou mettre-a-jour dev    # ou doc, forge

Images et modèles inchangés ne sont ni recopiés ni rechargés ; la VM ne redémarre que si le pilote ou le noyau changent.
Une carte ajoutée sur l'hôte est passée à la VM automatiquement.

## Versions figées

Le premier bundle note dans `versions.lock` l'empreinte de chaque image, la version d'OpenCode, le commit
de ComfyUI et la révision de chaque modèle. Les bundles suivants reprennent exactement ces versions.
Pour actualiser : réponds au menu, ou `HIBOU_ACTUALISER=open-webui,opencode ./hibou telecharger …` (`tout` pour tout).

## Sauvegardes

La VM forge est sauvegardée chaque nuit à 3 h (vzdump, 7 jours et 4 semaines) vers le stockage choisi au menu,
obligatoire. Forgejo fait en plus son propre export à 2 h. Les VM doc et dev ne sont pas sauvegardées : elles se
reconstruisent entièrement depuis le bundle.

## Adresses

| Service | Adresse |
|---|---|
| Chat, rédaction, images | https://chat.<domaine> |
| OpenCode | https://code.<domaine> |
| API doc / dev (clé par utilisateur) | https://llm-doc.<domaine>/v1, https://llm-dev.<domaine>/v1 |
| Forgejo, supervision | https://forge.<domaine>, https://supervision.<domaine> |

Clés d'API et commande Proxmox OIDC : `/root/hibou-acces.txt` sur forge.
