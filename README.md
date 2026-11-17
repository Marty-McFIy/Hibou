<pre>
   /\_/\
  ( o o )   Hibou
   > ^ <    L’IA qui veille chez vous.
</pre>

Hibou installe deux IA locales dans un réseau isolé : une IA de développement et une IA de documentation, avec Forgejo comme dépôt commun.

**Local.** Les modèles tournent sur tes machines, servis par llama.cpp et llama-swap.
**Isolé.** Aucune connexion sortante. Tout entre par un bundle vérifié.
**Discret.** Il veille, il ne bavarde pas.

## Infrastructure

| Machine | Rôle | Services |
| --- | --- | --- |
| Precision 5820 · RTX 6000 Ada | IA de développement | llama-swap, OpenCode, Caddy |
| Precision 7910 · Proxmox · 4 × Quadro RTX 4000 | IA de documentation (LXC `doc`) | llama-swap, Open WebUI, Caddy |
| Precision 7910 · VM `forge` | Services communs | Forgejo, registre Docker, Caddy |
| VM de téléchargement | Seule machine connectée | Préparation du bundle |

## Modèles

| Nœud | Modèle | Usage |
| --- | --- | --- |
| dev | Qwen3.8-27B (Q8) | Agent de code, lecture de captures |
| dev | Qwen3-Coder-Next (Q4) | Alternative MoE |
| dev | Qwen2.5-Coder 7B | Autocomplétion |
| doc | Gemma 4 26B-A4B (Q6) | Rédaction, images, schémas |
| doc | Qwen3.8-27B (Q4) | OCR structuré |
| doc | Qwen3-Embedding 0.6B | RAG |

## Utilisation

```bash
# Sur la VM connectée, disque USB monté sur /mnt/hibou
sudo ./hibou telecharger /mnt/hibou/hibou-bundle-$(date +%Y%m%d)

# Sur chaque machine, depuis le bundle
./hibou verifier
sudo ./hibou installer pve     # hôte Proxmox, puis redémarrage
sudo ./hibou installer forge   # VM forge
./hibou installer doc          # conteneur LXC doc
sudo ./hibou installer dev     # Precision 5820
```

## Documentation

- [Installation pas à pas](docs/installation.md)
- [Architecture](docs/architecture.md)
- [Charte graphique](charte/LISEZMOI.md) : jetons, composants, logos, icônes, polices
- [Contribuer](CONTRIBUTING.md) · [Sécurité](SECURITY.md) · [Changelog](CHANGELOG.md)

## État

| Brique | État |
| --- | --- |
| Bundle : paquets, images, modèles, empreintes | Fait |
| Installation des quatre rôles | Fait, à tester sur le matériel |
| Authentification OIDC via Forgejo | À faire |
| Runner Forgejo Actions et chaîne documentaire | À faire |
| Supervision | À faire |
| Thèmes Hibou de Forgejo, Open WebUI, OpenCode | À faire |
| Jeu d’évaluation `hibou-eval` | À faire |
