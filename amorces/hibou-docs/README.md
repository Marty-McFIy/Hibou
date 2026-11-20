# hibou-docs

Documentation produite avec Hibou. Chaque document part d’un template de `templates/` et porte dans son en-tête le champ `modele`.

À chaque pull request, le runner vérifie le style Markdown, la présence des sections du template et la validité des schémas Mermaid. À la fusion dans `main`, le site est publié sur `docs.hibou.lan`.

Pour ajouter un type de document, crée un fichier dans `templates/` avec la liste `sections`. Le modèle correspondant dans Open WebUI se régénère avec `outils/modeles_open_webui.py`.
