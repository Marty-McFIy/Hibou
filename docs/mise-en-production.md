# Mise en production

Liste de contrôle à suivre dans l’ordre, puis le cas d’un cluster Proxmox à deux nœuds.
Chaque étape se vérifie par une commande : rien n’est validé « à l’œil ».

## 1. Matériel et BIOS

- [ ] Virtualisation et IOMMU actives (Intel VT-x et VT-d, ou AMD-V et AMD-Vi).
- [ ] « Memory Mapped I/O above 4 GB » (ou « Above 4G decoding ») activé : indispensable aux cartes de plus de 8 Go.
- [ ] Chaque carte NVIDIA a son alimentation propre si elle dépasse 75 W (câbles d’alimentation GPU du constructeur du serveur,
      adaptateur 16 broches pour les cartes récentes) ; alimentations du serveur dimensionnées pour la somme des cartes.
- [ ] Cartes larges dans des emplacements x16 qui les accueillent (risers adaptés), flux d’air vérifié.
- [ ] Après installation de Proxmox : `lspci -nn | grep -i nvidia` montre toutes les cartes.

## 2. Bundle (machine connectée)

- [ ] `./hibou telecharger` : pour chaque serveur, le modèle exact de carte et leur nombre.
- [ ] Sur doc, une petite carte en plus (4 à 8 Go) ? Réponds « Oui » à « carte à part pour la recherche documentaire » :
      elle porte les embeddings et le reranker, et ne ralentit plus le LLM.
- [ ] Documentation de sécurité : « Oui » si l’équipe en a l’usage ; dépose dans `securite.d/ajouts/` les textes que les
      sites officiels ne laissent pas télécharger (IGI 1300, II 901…).
- [ ] Phrase de passe du bundle notée hors ligne, à deux endroits.
- [ ] `./hibou verifier` sur le disque de transport.

## 3. Installation

- [ ] `hibou installer forge` (sur un nœud), puis `doc`, puis `dev` (sur l’hôte de leurs cartes).
- [ ] Autres nœuds du cluster : `hibou installer noeud` (supervision).
- [ ] `hibou diagnostic` sur chaque hôte : aucun échec.
- [ ] `hibou essai` sur l’hôte de forge : aucun échec (connexion par Forgejo au chat, à OpenCode et à Grafana, réponses
      sourcées, export, pull request, runner, relecture, instances OpenCode).
- [ ] `hibou evaluer tout` sur forge, puis le tableau « Évaluation » de Grafana : notes et débit de chaque profil.

## 4. Sécurité

- [ ] Double authentification du compte administrateur de Forgejo.
- [ ] Certificat racine `/srv/hibou/hibou-ca.crt` installé sur les postes (navigateurs).
- [ ] `/root/hibou-acces.txt` sur forge : clés personnelles remises à chacun, fichier conservé hors ligne puis effacé.
- [ ] Si un secret a pu être vu (essais, captures, journaux) : `hibou renouveler-secrets` sur l’hôte de forge.
      Les anciens jetons sont révoqués ; mots de passe et phrase du bundle restent à changer à la main.
- [ ] Mots de passe initiaux changés à la première connexion (Forgejo l’impose).

## 5. Sauvegarde

- [ ] Stockage de sauvegarde hors du disque des VM (autre disque, autre machine).
- [ ] Le lendemain : `hibou diagnostic` montre une sauvegarde de forge de moins de 26 h.
- [ ] Restauration essayée une fois sur une VM jetable (Proxmox : « Restaurer » vers un autre identifiant), puis supprimée.

## 6. Mise en service

- [ ] Comptes des personnes créés (équipes doc et dev), première connexion faite.
- [ ] Une page publiée par l’équipe doc (rédaction, PR, relecture, fusion) et retrouvée dans le chat.
- [ ] Un ticket traité par l’agent de code (`forgejo-tickets`, PR avec « Closes #n »).

## Cluster à deux nœuds

Un cluster Proxmox a besoin de la majorité de ses votes (le quorum) pour rester modifiable. À deux nœuds, la panne de
l’un fait perdre le quorum à l’autre : ses VM continuent de tourner, mais on ne peut plus en démarrer, en arrêter ni en
modifier. La solution standard est un **témoin** (QDevice) : une troisième voix, portée par une petite machine à part.

### Témoin (QDevice)

1. Sur une machine hors des deux nœuds (petit serveur, poste, VM sur un autre hyperviseur), Debian ou Ubuntu :
   `apt install corosync-qnetd`.
2. Sur les deux nœuds : `apt install corosync-qdevice` (paquet du bundle Proxmox ou du dépôt Proxmox).
3. Sur un nœud : `pvecm qdevice setup <adresse du témoin>`.
4. Vérifier : `pvecm status` affiche `Quorate: Yes`, 3 votes attendus, et `Qdevice` dans la liste.
5. `hibou diagnostic` contrôle ensuite le quorum à chaque passage.

Le témoin ne porte aucune donnée et peut être arrêté quelques minutes sans effet tant que les deux nœuds tournent.

### Où placer les VM

| VM | Où | Pourquoi |
| --- | --- | --- |
| doc | sur l’hôte de ses cartes | les cartes passent à la VM (passthrough) : pas de migration possible |
| dev | sur l’hôte de ses cartes | idem |
| forge | sur l’un des deux, sauvegardée chaque nuit | seule VM sans carte : elle peut changer d’hôte |

Pour que forge redémarre seule sur l’autre nœud en cas de panne, il faut un stockage disponible des deux côtés :

- **ZFS local et réplication** (Datacenter → Réplication, toutes les 15 min) puis **HA** sur forge : redémarrage
  automatique sur l’autre nœud, au prix des minutes non encore répliquées ;
- **stockage partagé** (NFS, Ceph) : pas de perte, mais un équipement de plus.

Sans l’un ou l’autre, la reprise de forge se fait par restauration de sa dernière sauvegarde sur l’autre nœud
(quelques minutes pour forge, voir le journal des mesures).

### Panne d’un nœud sans témoin

En dernier recours seulement, sur le nœud restant : `pvecm expected 1` rend le cluster modifiable le temps de
redémarrer ce qu’il faut. À annuler dès le retour du second nœud (redémarrage de corosync). Ne jamais le faire si
l’autre nœud peut encore tourner : les deux moitiés modifieraient la configuration chacune de leur côté.
