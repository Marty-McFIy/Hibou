# Installation pas à pas

Les commandes se tapent en root ou avec `sudo`. Ordre : VM de téléchargement, hôte Proxmox, VM forge, conteneur doc, Precision 5820, postes clients.

## 1. Préparer le disque USB

Sur la VM de téléchargement. Vérifie le nom du disque avec `lsblk` : le formatage efface tout.

```bash
lsblk
sudo mkfs.ext4 -L HIBOU /dev/sdb1
sudo mkdir -p /mnt/hibou
sudo mount /dev/disk/by-label/HIBOU /mnt/hibou
```

## 2. Construire le bundle

```bash
sudo apt install -y docker.io python3-venv zstd
sudo ./hibou telecharger /mnt/hibou/hibou-bundle-$(date +%Y%m%d)
```

Ajoute à la main dans `hibou-bundle-*/extra/` l’ISO Ubuntu 26.04 serveur et le modèle LXC `ubuntu-26.04-standard_*.tar.zst`.

```bash
sync && sudo umount /mnt/hibou
```

## 3. Hôte Proxmox (7910)

```bash
mkdir -p /mnt/hibou && mount /dev/disk/by-label/HIBOU /mnt/hibou
cd /mnt/hibou/hibou-bundle-*
./hibou verifier
./hibou installer pve
reboot
```

Après le redémarrage, `nvidia-smi` doit lister 4 cartes. Copie l’ISO dans `/var/lib/vz/template/iso/` et le modèle LXC dans `/var/lib/vz/template/cache/`, puis crée la VM `forge` et le conteneur `doc`.

```bash
cat /root/hibou-lxc-doc.conf >> /etc/pve/lxc/<id>.conf
pct set <id> -mp0 /mnt/hibou,mp=/mnt/hibou
pct start <id>
```

## 4. VM forge

Démonte le disque sur l’hôte (`umount /mnt/hibou`), puis passe-le à la VM : Matériel > Ajouter > Périphérique USB.

```bash
sudo mkdir -p /mnt/hibou && sudo mount /dev/disk/by-label/HIBOU /mnt/hibou
cd /mnt/hibou/hibou-bundle-*
sudo ./hibou installer forge
```

Le script affiche la commande de création du compte administrateur et celle qui récupère le certificat racine. Retire ensuite le périphérique USB de la VM et remonte le disque sur l’hôte.

## 5. Conteneur LXC doc

```bash
pct enter <id>
cd /mnt/hibou/hibou-bundle-*
./hibou installer doc
```

## 6. Precision 5820

```bash
sudo mkdir -p /mnt/hibou && sudo mount /dev/disk/by-label/HIBOU /mnt/hibou
cd /mnt/hibou/hibou-bundle-*
sudo ./hibou installer dev
sudo reboot
```

Vérifie avec `nvidia-smi` et `docker compose -f /srv/hibou/compose.yaml ps`. Le script peut être relancé sans risque.

## 7. Postes clients

```
192.168.x.10  forge.hibou.lan registry.hibou.lan
192.168.x.11  chat.hibou.lan llm-doc.hibou.lan
192.168.x.12  code.hibou.lan llm-dev.hibou.lan
```

Installe le certificat racine récupéré à l’étape 4, puis ouvre `https://forge.hibou.lan`, `https://chat.hibou.lan` et `https://code.hibou.lan`.

Autre domaine : préfixe chaque installation par `HIBOU_DOMAINE=mondomaine`.
