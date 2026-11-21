# Contribuer

1. Le script `hibou` reste un seul fichier Bash. Avant tout envoi : `bash -n hibou` et `./hibou autotest`.
2. Rien ne se télécharge à l’installation : tout passe par `hibou telecharger` et le bundle.
3. Rien de propre à un site dans le script : un réglage d’installation passe par le menu ou une variable `HIBOU_*`.
   Hibou doit fonctionner de 4 Go à plus de 90 Go de mémoire vidéo, sur une ou plusieurs cartes.
4. Une erreur ne se masque pas (`|| true`, vérification désactivée) : on trouve la cause et on corrige par le plus
   petit changement utile.
5. Chaque correction est notée dans [JOURNAL-CORRECTIONS.md](JOURNAL-CORRECTIONS.md) : symptôme, cause, diff,
   test qui la prouve. Le [CHANGELOG](CHANGELOG.md) en garde une ligne.
6. Les textes (messages, consignes, documentation) sont en français, au tutoiement, ton calme, sans point
   d’exclamation ni émoji.
7. Les polices et ressources de la charte restent locales. Pour toucher à la charte :
   [charte/CONTRIBUTING.md](charte/CONTRIBUTING.md).
8. Aucun secret (mot de passe, jeton, clé) dans le dépôt, les journaux ou les rapports : remplace-le par `***`.

Les fonctions encore à valider sont listées dans [docs/FONCTIONNALITES.md](docs/FONCTIONNALITES.md).
