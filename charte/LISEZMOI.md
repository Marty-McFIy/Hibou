Hibou est une IA locale et hors ligne pour le traitement de texte et le code (OpenCode). Elle tourne sur la machine de l'utilisateur, n'envoie rien et ne parle que quand on lui demande. La marque dit la même chose : **une nuit calme, deux yeux d'ambre ouverts.**

## Promesse et ton

- Trois piliers, toujours dans cet ordre : **Local** (vos modèles tournent sur votre machine), **Isolé** (aucune connexion sortante requise), **Discret** (il veille, il ne bavarde pas).
- Signature : « L'IA qui veille chez vous. »
- Ton : calme, précis, discret. Tutoiement dans l'interface, phrases courtes, aucun jargon inutile. Hibou dit ce qu'il a fait (« J'ai relu ton chapitre »), jamais ce qu'il ressent.
- Pas de point d'exclamation, pas d'émoji, pas de superlatif. Majuscule initiale seule dans les titres et boutons.
- « hors ligne » est un état normal, jamais une erreur. Un message d'erreur dit quoi faire : « Port réservé. Choisis-en un au-dessus de 1024. »
- Nom : toujours « Hibou », jamais « HIBOU » ni « hibou » dans un texte (la commande `hibou` reste en minuscules).

## Couleurs

Cinq couleurs de marque, réparties **55 / 25 / 12 / 6 / 2** : `nuit`, `brume`, `ardoise`, `ambre`, `pierre`. Deux thèmes : **Nuit** (par défaut) et **Brume** (clair). Une interface utilise les jetons sémantiques, pas les couleurs de marque.

- Fond : `fond`. Relief croissant : `fond-creux` → `surface` → `surface-haute`.
- Texte : `texte`, `texte-doux`. Lien et invite : `accent-texte` (l'`ambre` pur est illisible en texte sur `brume`).
- Action principale : `accent` avec `sur-accent` (jamais de blanc sur l'ambre), tranche `accent-fonce`.
- États : `succes`, `danger`, toujours avec un mot ou une icône. Fonds doux pour les suggestions : `succes-doux`, `danger-doux`, `accent-doux`.
- Bords de contrôles : `filet-fort` (≥ 3:1). `filet` est décoratif.
- Le terminal reste `nuit` dans les deux thèmes.

## Relief

Le relief de Hibou vient d'une seule lumière, **par le haut** : un reflet clair sur l'arête supérieure, une ombre portée dessous.

- `creux` : enfoncé (champs, invite, rails, bouton pressé), sur `fond-creux`.
- `relief-1` : posé (cartes, boutons neutres). `relief-2` : soulevé (survol, terminal). `relief-3` : flottant (menus, fenêtres, icône d'application).
- `relief-accent` : le bouton principal, avec sa tranche de 2 px.
- `lueur` : halo d'ambre quand Hibou écoute ou travaille. Jamais décoratif.
- Une interaction traverse les niveaux : repos `relief-1` → survol `relief-2` (+1 px) → clic `creux` (−2 px).
- Le symbole reste plat ; seul son support (tuile d'application, ombre portée `hb-logo--relief`) prend du relief.

## Typographie

- Titres : **Fraunces 600** (`t-affiche` 132, `t-titre` 52, `t-sous-titre` 28, `t-intertitre` 22).
- Texte : **Inter 400 / 600** (`t-corps` 18, `t-corps-petit` 16, `t-legende` 14, `t-action` 15).
- Code : **JetBrains Mono 500** (`t-code` 16, `t-etiquette` 13 en capitales espacées).
- Les fichiers de police sont dans `fonts/` et fonctionnent hors ligne. Ne jamais charger de police depuis le réseau dans le produit.

## Mouvement

Hibou bouge peu et sans bruit. Chaque mouvement a une raison.

- Courbes : `courbe-sortie` par défaut, `courbe-entree` pour ce qui part, `courbe-ressort` pour ce qu'on touche, `courbe-veille` pour les boucles lentes.
- Durées : `duree-instant` 90, `duree-rapide` 160, `duree-posee` 280, `duree-lente` 480, `duree-veille` 4200 ms.
- Le symbole a six états (`veille`, `ecoute`, `reflexion`, `ecriture`, `erreur`, `endormi`) : voir la carte Etats du hibou. Un seul hibou animé par écran.
- Le texte généré apparaît mot à mot (`hb-reponse__mot`), l'attente se montre par deux yeux qui clignent (`hb-attente`), jamais par une toupie.
- Tout s'arrête sous `prefers-reduced-motion`.

## Logo

- Symbole : tête vue de face, deux oreilles, deux yeux, un bec, dans un carré de 120. Fichiers dans `assets/Logos/`, version vivante avec `Hibou.Logo()`.
- Sur fond sombre : tête `brume`, bec `ardoise`. Sur fond clair : tête `nuit`, bec `ambre`. Les iris sont toujours `ambre`.
- Zone de protection : un diamètre d'œil (un quart de la largeur). Taille minimale : 24 px, en dessous `hibou-favicon.svg` (les yeux seuls).
- À éviter : étirer ou incliner le logo, colorier la tête en ambre, ajouter ombre ou dégradé sur la silhouette, poser l'ambre en texte sur fond clair.

## Iconographie

- Jeu maison de 35 icônes au trait (grille 24, trait 1,75, bouts ronds), dans `assets/Icones/` et en classes `hb-icone hb-icone--<nom>` qui prennent la couleur du texte.
- Tailles 16 / 20 / 24 / 32. Toujours accompagnées d'un libellé, ou d'un `aria-label` sur le bouton.
- Pas d'émoji, pas d'icônes pleines, pas d'autre bibliothèque.

## Utiliser le système dans un projet

1. Charger `tokens.css`, puis `components/bundle.css`, puis (pour le logo vivant et les aides) `components/bundle.js` qui expose `window.Hibou`. Aucune dépendance, aucun appel réseau.
2. Poser `data-theme="nuit"` ou `data-theme="brume"` sur `<html>`.
3. Composer avec les classes `hb-` : `hb-bouton`, `hb-champ`, `hb-invite`, `hb-carte`, `hb-etat`, `hb-terminal`, `hb-suggestion`…
4. Focus clavier : `anneau-focus` sur tout contrôle, plein, 2 px décollés de 2 px.
