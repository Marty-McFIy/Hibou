# Sécurité

Hibou tourne dans un réseau isolé. Pour signaler une faille, ouvre un avis privé via l'onglet *Security* du dépôt
(« Report a vulnerability ») plutôt qu'une issue publique.

Ce que Hibou fait pour limiter les risques :

- aucune connexion sortante depuis les VM ; tout entre par un bundle vérifié (SHA-256, versions figées) ;
- secrets du bundle chiffrés (AES-256, PBKDF2), jamais écrits dans les journaux ;
- TLS partout par une autorité interne, connexion unique par Forgejo, ports des serveurs GPU ouverts à forge seulement ;
- agents sans droits root, `main` protégée dans tous les dépôts, fusion par une personne, refus d'office des commandes
  dangereuses et de l'affichage des secrets ;
- conversations et fichiers personnels à chaque compte.

Avant une mise en production : régénère les jetons et mots de passe utilisés pendant les essais.
