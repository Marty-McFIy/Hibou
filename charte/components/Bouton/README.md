# Bouton

`<button class="hb-bouton">` : un bouton en relief. Il se soulève au survol (`relief-2`), s'enfonce au clic (`creux`) et montre `anneau-focus` au clavier.

- `--principal` : ambre, tranche `accent-fonce`. Une seule fois par vue, pour l'action pour laquelle l'écran existe.
- défaut : neutre, `surface-haute` bordée de `filet-fort`.
- `--discret` : texte `accent-texte`, sans relief. Annuler, actions secondaires.
- `--rond` (icône seule, `aria-label` obligatoire), `--grand` (48 px).
- Libellé : verbe à l'infinitif, majuscule initiale seule, sans point : « Lancer le modèle ».
