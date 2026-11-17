# EtatsHibou

Les six états animés du symbole, posés par `data-etat` sur le `<svg class="hb-logo">` (ou `Hibou.etat(svg, 'reflexion')`).

| État | Quand | Mouvement |
|---|---|---|
| `veille` | Interface au repos, modèle chargé | Un clignement toutes les `duree-veille` |
| `ecoute` | L'utilisateur tape une invite | Les pupilles se dilatent et respirent |
| `reflexion` | Avant le premier mot | Le regard cherche à gauche, puis à droite |
| `ecriture` | Pendant la génération | Le regard lit de gauche à droite, les iris palpitent |
| `erreur` | Échec, refus | La tête fait non, une fois ; pupilles serrées |
| `endormi` | Aucun modèle chargé | Yeux fermés |

Un seul hibou animé par écran. Tout s'arrête sous `prefers-reduced-motion`.
