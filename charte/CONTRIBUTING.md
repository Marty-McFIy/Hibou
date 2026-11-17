# Contribuer à la charte

La charte est la source des interfaces Hibou. Lis d'abord le [livre de marque](LISEZMOI.md).

## Où modifier quoi

| Je change | Je modifie | Et aussi |
| --- | --- | --- |
| Une couleur, une ombre, une durée, un espacement | `tokens.json` | `tokens.css` (même valeur, même nom) |
| Un composant | `components/bundle.css` | son `README.md` et son `preview.html` |
| Un logo ou une icône | `assets/Logos/` ou `assets/Icones/` | le `README.md` du dossier |
| Un texte de marque | `LISEZMOI.md` | |

`tokens.json` fait foi : `tokens.css` en est dérivé. Les deux changent dans le même commit.

## Règles

- **Hors ligne.** Aucune police, image ni script chargé depuis le réseau. Les polices vivent dans `fonts/`.
- **Jetons, pas couleurs brutes.** Une interface utilise les jetons sémantiques (`fond`, `texte`, `accent`…), jamais `ambre` ou `nuit` directement. Pas de valeur hexadécimale en dur dans un composant.
- **Deux thèmes.** Tout changement est vérifié en Nuit et en Brume.
- **Contraste.** Texte 4,5:1 minimum (3:1 à partir de 24 px), bords de contrôles et icônes 3:1. L'ambre pur n'est jamais du texte sur Brume : utiliser `accent-texte`. Une couleur ne porte jamais seule un état : toujours un mot ou une icône.
- **Focus clavier visible** sur tout contrôle (`anneau-focus`).
- **Mouvement.** Les durées et courbes viennent des jetons. Tout s'arrête sous `prefers-reduced-motion`. Un seul hibou animé par écran.
- **Logo.** Ni étiré, ni incliné, ni colorié en ambre, ni ombré. Zone de protection : un diamètre d'œil. Taille minimale 24 px, en dessous `hibou-favicon.svg`.
- **Icônes.** Grille 24, trait 1,75, bouts ronds, sans remplissage. Pas d'émoji, pas d'autre bibliothèque. Une nouvelle icône est ajoutée à la liste de `assets/Icones/README.md` et au composant `Icones`.
- **Composants.** Classes préfixées `hb-`. Un nouveau composant a un `README.md` (premier paragraphe = résumé, ce que le consommateur doit fournir) et un `preview.html`.

## Ton des textes

Calme, précis, discret. Tutoiement dans l'interface, phrases courtes, pas de point d'exclamation, pas d'émoji, pas de superlatif. Majuscule initiale seule dans les titres et les boutons. Le nom s'écrit « Hibou » ; seule la commande reste `hibou`. « Hors ligne » est un état normal, jamais une erreur. Un message d'erreur dit quoi faire.

## Avant de proposer un changement

1. Ouvrir chaque `preview.html` touché dans un navigateur, en Nuit et en Brume.
2. Vérifier les contrastes des couleurs ajoutées ou modifiées.
3. Mettre à jour le `CHANGELOG.md` à la racine.
