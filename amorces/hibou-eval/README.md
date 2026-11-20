# hibou-eval

Vingt tâches réelles pour comparer les modèles du catalogue llama-swap et vérifier qu’une mise à jour ne dégrade rien.

| Famille | Tâches | Notation |
| --- | --- | --- |
| Code | 8 | Automatique : le test passe ou non, exécuté dans un conteneur sans réseau |
| Documentation | 8 | Automatique sur la forme (sections, consignes, schéma) ; note humaine de 1 à 5 à reporter dans le CSV |
| Vision | 4 | Part des éléments attendus présents dans la réponse |

## Lancer une évaluation

Forge l’exécute seule après chaque installation de doc ou dev, puis chaque dimanche à 4 h ; les scores vont dans le tableau Grafana « Hibou · Évaluation des modèles ». À la main, sur forge :

```bash
sudo /usr/local/lib/hibou/hibou evaluer doc /usr/local/lib/hibou
```

Ou directement :

Depuis la VM forge (Docker requis pour isoler le code produit) :

```bash
python3 evaluer.py --api https://llm-dev.hibou.lan/v1 --cle "$(cat cle-dev)" --modeles qwen3.8-27b,qwen3-coder-next --familles code
python3 evaluer.py --api https://llm-doc.hibou.lan/v1 --cle "$(cat cle-doc)" --modeles gemma-4-26b,qwen3.8-27b --familles doc,vision
```

Les résultats vont dans `resultats/AAAA-MM-JJ/` : un CSV par lancement, et les réponses brutes pour relecture. Pour les documents, ouvre chaque fichier `.md` produit et note-le de 1 à 5 dans la colonne `note_humaine` (conformité, exactitude, français, schémas).

## Règle d’adoption

Un modèle candidat remplace le modèle en place s’il fait au moins aussi bien sur le code et la documentation, sans perte de vitesse de plus de 20 %. `--reference <modèle>` affiche ce verdict pour chaque candidat.

Commite le CSV de chaque évaluation : l’historique sert de référence aux mises à jour suivantes.
