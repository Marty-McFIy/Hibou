# Journal des corrections — Hibou 0.9.0

Format : symptôme, cause, diff, test de preuve. Secrets masqués (`***`).

## Préparation de l'hôte (hors script)

- **Disques** : `sdb` (BitLocker) et `sdd` (NTFS, SSD 500 Go) effacés avec l'accord de l'utilisateur. `sda` (NTFS) conservé.
  `hibou-vm` (LVM-thin) sur le SSD ; `/mnt/hibou` (ext4) sur `sdb`.
- **IOMMU** : déjà active sans `intel_iommu=on` (noyau 7.0, groupes IOMMU présents, GPU seul dans le groupe 17). Aucune modification de GRUB.

## A1 — Profil « ≥ 4 Go » absent (amélioration)

- Symptôme : la RTX A400 (4 Go) est sous le plus petit profil (12 Go) ; le menu affiche « Attention » et propose un profil qui ne tient pas.
- Ajout : `dev:5` (Qwen3.5 4B UD-Q4_K_XL, contexte 16k, + complétion Qwen2.5-Coder 1.5B Q8, groupe exclusif) et `doc:4`
  (Qwen3.5 4B UD-Q4_K_XL + mmproj F16, contexte 8k, embedding sur le processeur). Seuils `PROFILS_*_GO` étendus à 4.
- Dépôts et fichiers vérifiés sur Hugging Face le 2026-11-20.
- Test : `./hibou autotest` (22 lignes de modèles). Tenue en VRAM : à mesurer (phase 3).

## B1 — Bruit `debconf` dans la sortie de `telecharger` (affichage)

- Symptôme : plusieurs lignes `debconf: unable to initialize frontend …` entre les étapes, hors charte.
- Cause : `apt-get install` dans les conteneurs sans `DEBIAN_FRONTEND=noninteractive`.
- Correction : à venir (voir plus bas).
  Diff : `export DEBIAN_FRONTEND=noninteractive` ajouté en tête des deux `bash -euc` (paquets Ubuntu et Proxmox).
  Test : relancer `telecharger` avec `HIBOU_PARTIES=apt` et vérifier l'absence de lignes `debconf`.

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

## N1 — Avertissement apt « Did not understand pin type version » (sans effet)

- Constat : bundle du 2026-11-20 : 23 paquets NVIDIA, tous en 620.70.06 (`nvidia-driver-open`, `nvidia-dkms-open`, `libnvidia-compute`…), toolkit 1.20.2. `MANIFEST.md` annonce 620.70.06.
- Conclusion : le pilote est bien figé. L'avertissement est du bruit, pas un bogue bloquant. À revoir si le pilote installé dans la VM doc diffère (phase 3).

## Mesures phase 1

- Bundle : 18 Go. `verifier` : OK en 2 min 14 s (dans la VM de téléchargement).
