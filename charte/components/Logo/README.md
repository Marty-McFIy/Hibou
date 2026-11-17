# Logo

Le symbole Hibou, en SVG vivant : `Hibou.Logo({taille, variante, etat, relief, vivant})` ou `Hibou.logoHTML(...)` pour une chaîne.

- Sans `variante`, il suit le thème (`texte`, `fond`, `accent`, `logo-bec`). `sur-nuit` / `sur-brume` le figent pour un support connu.
- `etat` anime le regard : `veille` (clignement toutes les 4,2 s, l'état par défaut d'une interface au repos), `ecoute`, `reflexion`, `ecriture`, `erreur`, `endormi`. Voir la carte Etats du hibou.
- `relief` ajoute une ombre portée sous la silhouette (la silhouette elle-même reste plate). `vivant` : la tête penche au survol.
- Taille minimale 24 px ; dessous, utiliser `assets/Logos/hibou-favicon.svg`. Zone de protection : un quart de la taille.
- À ne pas faire : étirer, incliner hors animation, colorer la tête en ambre, ajouter un dégradé sur la silhouette.
