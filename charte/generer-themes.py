"""Génère les thèmes Hibou (Forgejo, Open WebUI, OpenCode) depuis tokens.json."""
import json, re, shutil, pathlib, cairosvg

SRC = pathlib.Path("/mnt/user-data/outputs/artifacts/840599f0-8ded-4fe2-bcc7-7f1df2997d8e/project")
LOGOS = pathlib.Path("/mnt/user-data/outputs/logos")
OUT = pathlib.Path("/mnt/user-data/outputs/charte")
shutil.rmtree(OUT, ignore_errors=True)

t = json.loads((SRC / "tokens.json").read_text())
brut = {x["name"]: x["value"] for x in t["color"]["tokens"]}

def val(nom, theme):
    v = brut[nom]
    v = v.get(theme, next(iter(v.values()))) if isinstance(v, dict) else v
    m = re.fullmatch(r"\{(.+)\}", v)
    return val(m.group(1), theme) if m else v.upper()

C = {th: {n: val(n, th) for n in brut} for th in ("nuit", "brume")}
O = {th: {x["name"]: (x["value"][th] if isinstance(x["value"], dict) else x["value"]) for x in t["shadow"]["tokens"]} for th in ("nuit", "brume")}

# Contrôle : texte 4,5:1 sur ses fonds, dans les deux thèmes.
def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)
for th, c in C.items():
    for txt, fond in [("texte", "fond"), ("texte", "surface"), ("texte-doux", "fond"), ("accent-texte", "fond"), ("sur-accent", "accent")]:
        assert ratio(c[txt], c[fond]) >= 4.5, (th, txt, fond, ratio(c[txt], c[fond]))

POLICES = """@font-face { font-family: "Fraunces"; src: url("{p}/Fraunces-600.woff2") format("woff2"); font-weight: 600; font-display: swap; }
@font-face { font-family: "Inter"; src: url("{p}/Inter-variable.woff2") format("woff2"); font-weight: 100 900; font-display: swap; }
@font-face { font-family: "JetBrains Mono"; src: url("{p}/JetBrainsMono-500.woff2") format("woff2"); font-weight: 500; font-display: swap; }
"""
TEXTE = 'Inter, system-ui, sans-serif'
CODE = '"JetBrains Mono", ui-monospace, monospace'
TITRE = 'Fraunces, Georgia, serif'

def ecrire(chemin, contenu, mode="w"):
    p = OUT / chemin
    p.parent.mkdir(parents=True, exist_ok=True)
    (p.write_bytes if isinstance(contenu, bytes) else p.write_text)(contenu)

def logos(dossier):
    for nom, fichier in [("favicon.svg", "b7b75ab9e6e23236bc36392f5252fd92.svg"), ("symbole-sur-nuit.svg", "6cae2d01eae95425f22f583769a101c3.svg"),
                         ("symbole-sur-brume.svg", "e501f73a1dec833df7d39b789bdf6e84.svg"), ("icone-app.svg", "a7b54c7bce0e322a01185ce5dc09552c.svg")]:
        ecrire(f"{dossier}/{nom}", (LOGOS / fichier).read_bytes())

def polices(dossier):
    for f in (SRC / "fonts").iterdir():
        ecrire(f"{dossier}/{f.name}", f.read_bytes())

def png(svg, taille):
    return cairosvg.svg2png(bytestring=(LOGOS / svg).read_bytes(), output_width=taille, output_height=taille)

# ─── Forgejo ────────────────────────────────────────────────────────────────
FJ = "forgejo/public/assets"
def forgejo(th):
    c, o, base = C[th], O[th], "forgejo-dark" if th == "nuit" else "forgejo-light"
    return f"""/* Hibou {th.capitalize()} — thème Forgejo généré depuis tokens.json. */
@import url("./theme-{base}.css");
{POLICES.replace("{p}", "../fonts")}
gitea-theme-meta-info {{ --theme-display-name: "Hibou {th.capitalize()}"; }}

:root {{
  --is-dark-theme: {"true" if th == "nuit" else "false"};
  --fonts-proportional: {TEXTE};
  --fonts-monospace: {CODE};
  --color-body: {c["fond"]};
  --color-box-body: {c["surface"]};
  --color-box-body-highlight: {c["surface-haute"]};
  --color-box-header: {c["surface-haute"]};
  --color-card: {c["surface"]};
  --color-menu: {c["surface-haute"]};
  --color-nav-bg: {c["fond-creux"]};
  --color-nav-hover-bg: {c["surface"]};
  --color-secondary-nav-bg: {c["fond"]};
  --color-footer: {c["fond-creux"]};
  --color-header-wrapper: {c["fond-creux"]};
  --color-text: {c["texte"]};
  --color-text-dark: {c["texte"]};
  --color-text-light: {c["texte"]};
  --color-text-light-1: {c["texte-doux"]};
  --color-text-light-2: {c["texte-doux"]};
  --color-text-light-3: {c["texte-doux"]};
  --color-primary: {c["accent-texte"]};
  --color-primary-contrast: {c["fond"]};
  --color-primary-dark-1: {c["accent-texte"]};
  --color-primary-light-1: {c["accent-texte"]};
  --color-primary-alpha-10: {c["accent-doux"]};
  --color-primary-alpha-20: {c["accent-doux"]};
  --color-secondary: {c["filet"]};
  --color-secondary-dark-1: {c["filet-fort"]};
  --color-light-border: {c["filet"]};
  --color-input-background: {c["fond-creux"]};
  --color-input-border: {c["filet-fort"]};
  --color-input-border-hover: {c["accent-texte"]};
  --color-input-text: {c["texte"]};
  --color-hover: {c["surface-haute"]};
  --color-active: {c["accent-doux"]};
  --color-markup-code-block: {c["fond-creux"]};
  --color-markup-code-inline: {c["fond-creux"]};
  --color-code-bg: {c["fond-creux"]};
  --color-console-bg: {C["nuit"]["fond-creux"]};
  --color-console-fg: {C["nuit"]["texte"]};
  --color-green: {c["succes"]};
  --color-red: {c["danger"]};
  --color-accent: {c["accent"]};
  --color-small-accent: {c["accent-doux"]};
  --color-diff-added-row-bg: {c["succes-doux"]};
  --color-diff-removed-row-bg: {c["danger-doux"]};
  --border-radius: 8px;
  --border-radius-medium: 14px;
}}

/* Action principale : ambre et sur-accent, jamais de blanc sur l’ambre. */
.ui.primary.button, .ui.primary.buttons .button {{
  background: {c["accent"]}; color: {c["sur-accent"]};
  box-shadow: {o["relief-accent"]};
  transition: transform 160ms cubic-bezier(0.2, 0.8, 0.2, 1);
}}
.ui.primary.button:hover {{ background: {c["accent"]}; color: {c["sur-accent"]}; transform: translateY(-1px); }}
.ui.primary.button:active {{ transform: translateY(2px); box-shadow: {o["creux"]}; }}
.ui.segment, .ui.attached.segment, .ui.card, .ui.cards > .card {{ box-shadow: {o["relief-1"]}; }}
.ui.dropdown .menu, .ui.modal, .tippy-box {{ box-shadow: {o["relief-3"]}; }}
input, textarea, .ui.input input, .ui.form input, .ui.form textarea {{ box-shadow: {o["creux"]}; }}
:focus-visible {{ outline: none; box-shadow: {o["anneau-focus"]} !important; }}
h1, h2, .ui.header, .markup h1, .markup h2 {{ font-family: {TITRE}; font-weight: 600; }}
.terminal, .job-step-container {{ background: {C["nuit"]["fond-creux"]}; color: {C["nuit"]["texte"]}; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
"""

ecrire(f"{FJ}/css/theme-hibou-nuit.css", forgejo("nuit"))
ecrire(f"{FJ}/css/theme-hibou-brume.css", forgejo("brume"))
ecrire(f"{FJ}/css/theme-hibou-auto.css", """/* Hibou Auto — suit le réglage clair ou sombre du poste. */
@import url("./theme-hibou-nuit.css") (prefers-color-scheme: dark);
@import url("./theme-hibou-brume.css") (prefers-color-scheme: light);
gitea-theme-meta-info { --theme-display-name: "Hibou Auto"; }
""")
polices(f"{FJ}/fonts")
ecrire(f"{FJ}/img/logo.svg", (LOGOS / "6cae2d01eae95425f22f583769a101c3.svg").read_bytes())
ecrire(f"{FJ}/img/favicon.svg", (LOGOS / "b7b75ab9e6e23236bc36392f5252fd92.svg").read_bytes())
ecrire(f"{FJ}/img/logo.png", png("6cae2d01eae95425f22f583769a101c3.svg", 512))
ecrire(f"{FJ}/img/favicon.png", png("b7b75ab9e6e23236bc36392f5252fd92.svg", 180))
ecrire(f"{FJ}/img/apple-touch-icon.png", png("a7b54c7bce0e322a01185ce5dc09552c.svg", 180))
ecrire(f"{FJ}/img/avatar_default.png", png("a7b54c7bce0e322a01185ce5dc09552c.svg", 256))

# ─── Open WebUI ─────────────────────────────────────────────────────────────
# Open WebUI teinte son interface par une échelle --color-gray-* : on la remplace par la gamme Hibou.
n, b = C["nuit"], C["brume"]
gamme = {"50": b["surface-haute"], "100": b["surface"], "200": b["fond"], "300": b["fond-creux"], "400": b["filet"],
         "500": n["texte-doux"], "600": b["texte-doux"], "700": n["filet"], "800": n["surface-haute"], "850": n["surface"],
         "900": n["fond"], "950": n["fond-creux"]}
gris = "\n".join(f"  --color-gray-{k}: {v};" for k, v in gamme.items())
ecrire("open-webui/custom.css", f"""/* Hibou — Open WebUI, généré depuis tokens.json. Monté sur /app/build/static/custom.css (Open WebUI 0.13). */
{POLICES.replace("{p}", "/static/hibou")}
:root {{
{gris}
  /* Noir et blanc purs d’Open WebUI (calques, panneaux, écran de connexion) : fond nuit et fond brume. */
  --color-black: {n["fond"]};
  --color-white: {b["fond"]};
  --hb-accent: {n["accent"]};
  --hb-sur-accent: {n["sur-accent"]};
}}
/* Thème clair : texte secondaire en texte-doux Brume (6:1). La gamme commune garde le gris Nuit, illisible sur brume (2,4:1). */
html:not(.dark) {{ --color-gray-400: {b["texte-doux"]}; --color-gray-500: {b["texte-doux"]}; }}
html, body {{ font-family: {TEXTE}; background: {b["fond"]}; color: {b["texte"]}; }}
html.dark, html.dark body {{ background: {n["fond"]}; color: {n["texte"]}; }}
code, pre, kbd, .font-mono {{ font-family: {CODE}; }}
h1, h2, .text-2xl, .text-3xl {{ font-family: {TITRE}; font-weight: 600; }}
/* Fraunces pour les titres seulement : étiquettes, boutons et descriptions qu’ils contiennent restent en Inter. */
:is(h1, h2, .text-2xl, .text-3xl) :is(.text-xs, .text-sm, .text-base, p, button) {{ font-family: {TEXTE}; font-weight: 400; }}

/* Liens et invites : accent-texte, lisible dans les deux thèmes. */
a {{ color: {b["accent-texte"]}; }}
html.dark a {{ color: {n["accent-texte"]}; }}
::selection {{ background: {n["accent"]}; color: {n["sur-accent"]}; }}

/* Bouton d’envoi : action principale. */
#send-message-button:not(:disabled) {{ background: {n["accent"]} !important; color: {n["sur-accent"]} !important; box-shadow: {O["nuit"]["relief-accent"]}; }}

/* Champ de saisie en creux. */
#chat-input-container, #chat-input {{ box-shadow: {O["brume"]["creux"]}; border-radius: 22px; }}
html.dark #chat-input-container, html.dark #chat-input {{ box-shadow: {O["nuit"]["creux"]}; }}

/* Invite : bord accent-fonce et lueur quand elle a le focus (Hibou écoute). */
#chat-input-container:focus-within {{ border-color: #8A5F0A !important; box-shadow: inset 0 2px 4px rgba(15,20,32,0.16), 0 0 0 1px rgba(138,95,10,0.5), 0 0 20px rgba(242,181,68,0.55) !important; }}
html.dark #chat-input-container:focus-within {{ border-color: #B9821F !important; box-shadow: inset 0 2px 4px rgba(0,0,0,0.6), 0 0 0 1px rgba(242,181,68,0.4), 0 0 24px rgba(242,181,68,0.3) !important; }}
/* Focus clavier : anneau plein, 2 px décollés de 2 px. */
:focus-visible {{ outline: none !important; box-shadow: {O["brume"]["anneau-focus"]} !important; }}
html.dark :focus-visible {{ box-shadow: {O["nuit"]["anneau-focus"]} !important; }}

/* Blocs de code : le terminal reste nuit dans les deux thèmes. */
pre, .codeblock {{ background: {n["fond-creux"]} !important; color: {n["texte"]} !important; }}

@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
""")
polices("open-webui/hibou")
logos("open-webui/hibou")
for nom, svg, taille in [("favicon.png", "b7b75ab9e6e23236bc36392f5252fd92.svg", 32), ("favicon-96x96.png", "b7b75ab9e6e23236bc36392f5252fd92.svg", 96),
                         ("favicon-dark.png", "b7b75ab9e6e23236bc36392f5252fd92.svg", 96), ("apple-touch-icon.png", "a7b54c7bce0e322a01185ce5dc09552c.svg", 180),
                         ("logo.png", "a7b54c7bce0e322a01185ce5dc09552c.svg", 512), ("splash.png", "e501f73a1dec833df7d39b789bdf6e84.svg", 512),
                         ("splash-dark.png", "6cae2d01eae95425f22f583769a101c3.svg", 512)]:
    ecrire(f"open-webui/static/{nom}", png(svg, taille))
ecrire("open-webui/static/favicon.svg", (LOGOS / "b7b75ab9e6e23236bc36392f5252fd92.svg").read_bytes())

# ─── OpenCode ───────────────────────────────────────────────────────────────
# Le terminal reste nuit dans les deux thèmes : une seule valeur par clé.
p = C["nuit"]
cle = {
    "primary": p["accent"], "secondary": p["texte-doux"], "accent": p["accent"],
    "error": p["danger"], "warning": p["accent"], "success": p["succes"], "info": p["texte"],
    "text": p["texte"], "textMuted": p["texte-doux"],
    "background": p["fond"], "backgroundPanel": p["surface"], "backgroundElement": p["surface-haute"],
    "border": p["filet"], "borderActive": p["accent"], "borderSubtle": p["filet"],
    "diffAdded": p["succes"], "diffRemoved": p["danger"], "diffContext": p["texte-doux"], "diffHunkHeader": p["texte-doux"],
    "diffHighlightAdded": p["succes"], "diffHighlightRemoved": p["danger"],
    "diffAddedBg": p["succes-doux"], "diffRemovedBg": p["danger-doux"], "diffContextBg": p["fond"],
    "diffLineNumber": p["texte-doux"], "diffAddedLineNumberBg": p["succes-doux"], "diffRemovedLineNumberBg": p["danger-doux"],
    "markdownText": p["texte"], "markdownHeading": p["accent"], "markdownLink": p["accent"], "markdownLinkText": p["texte"],
    "markdownCode": p["accent"], "markdownBlockQuote": p["texte-doux"], "markdownEmph": p["texte"], "markdownStrong": p["texte"],
    "markdownHorizontalRule": p["filet"], "markdownListItem": p["accent"], "markdownListEnumeration": p["accent"],
    "markdownImage": p["accent"], "markdownImageText": p["texte-doux"], "markdownCodeBlock": p["texte"],
    "syntaxComment": p["texte-doux"], "syntaxKeyword": p["accent"], "syntaxFunction": p["succes"], "syntaxVariable": p["texte"],
    "syntaxString": "#C9B98F", "syntaxNumber": p["danger"], "syntaxType": "#9FB3D9", "syntaxOperator": p["texte-doux"],
    "syntaxPunctuation": p["texte-doux"],
}
for nom, v in cle.items():
    assert re.fullmatch(r"#[0-9A-F]{6}", v), nom
ecrire("opencode/themes/hibou.json", json.dumps({"$schema": "https://opencode.ai/theme.json",
    "theme": {k: {"dark": v, "light": v} for k, v in cle.items()}}, indent=2, ensure_ascii=False) + "\n")

# ─── Commun : jetons CSS pour tout outil maison ─────────────────────────────
lignes = lambda th: "\n".join(f"  --{k}: {v};" for k, v in C[th].items()) + "\n" + "\n".join(f"  --{k}: {v};" for k, v in O[th].items())
ecrire("commun/hibou-jetons.css", f"""/* Jetons Hibou, générés depuis tokens.json. data-theme="nuit" (défaut) ou "brume" sur <html>. */
{POLICES.replace("{p}", "./fonts")}
:root, [data-theme="nuit"] {{
{lignes("nuit")}
}}
[data-theme="brume"] {{
{lignes("brume")}
}}
""")
polices("commun/fonts")
logos("commun/logos")
print("ok")
