# Architecture

Deux IA locales dans un réseau isolé, avec Forgejo comme dépôt commun. Aucune connexion sortante : tout entre par un bundle vérifié.

## Machines et services

| Machine | Rôle | Services | Adresses (domaine `hibou.lan`) |
| --- | --- | --- | --- |
| Precision 5820 · RTX 6000 Ada | IA de développement | llama-swap, OpenCode, Caddy | `code.` (interface), `llm-dev.` (API) |
| Precision 7910 · Proxmox · 4 × Quadro RTX 4000 | IA de documentation (LXC `doc`) | llama-swap, Open WebUI, Caddy | `chat.` (interface), `llm-doc.` (API) |
| Precision 7910 · VM `forge` | Services communs | Forgejo, registre Docker, Caddy | `forge.`, `registry.` (SSH Forgejo : port 2222) |
| VM de téléchargement | Seule machine connectée | Préparation du bundle | — |

Le domaine se change avec `HIBOU_DOMAINE`.

## Flux

```
VM connectée ──bundle (USB)──▶ pve ─▶ forge ─▶ doc ─▶ dev
                                         ▲        │      │
                                         └── Git ─┴──────┘
```

- Chaque machine fait tourner ses services en conteneurs Docker, derrière Caddy (HTTPS, certificats locaux).
- Les API `llm-dev.` et `llm-doc.` exigent une clé (`Authorization: Bearer`, variable `HIBOU_API_KEY`).
- llama-swap charge un modèle à la demande ; llama.cpp (`llama-server`) le sert.
- Forgejo est le dépôt commun : le code (dev) et la documentation (doc) y convergent.

## Le bundle

`hibou telecharger` produit, sur la VM connectée : paquets Ubuntu 26.04 et Proxmox VE 9, images Docker (empreintes figées dans `MANIFEST.md`), modèles GGUF, configs et charte. `hibou verifier` contrôle les empreintes avant chaque installation.

## Modèles

| Nœud | Modèle | Contexte | Usage |
| --- | --- | --- | --- |
| dev | Qwen3.8-27B (Q8) | 131 072 | Agent de code, lecture de captures |
| dev | Qwen3-Coder-Next (Q4) | 65 536 | Alternative MoE |
| dev | Qwen2.5-Coder 7B | 8 192 | Autocomplétion |
| doc | Gemma 4 26B-A4B (Q6) | 65 536 | Rédaction, images, schémas |
| doc | Qwen3.8-27B (Q4) | 32 768 | OCR structuré |
| doc | Qwen3-Embedding 0.6B | — | RAG |

## Ordre d'installation

`pve` (puis redémarrage) → `forge` → `doc` → `dev`. Détail dans [installation.md](installation.md).
